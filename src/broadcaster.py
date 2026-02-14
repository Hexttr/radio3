"""
Broadcaster — читает сегменты из Scheduler и стримит в Icecast.
Icecast не поддерживает chunked encoding, поэтому используем HTTP/1.0.
Предзагрузка следующего сегмента в память — плавные переходы без подвисаний.
"""
import base64
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from urllib.parse import urlparse

CHUNK_SIZE = 16384  # 16 KB — меньше syscall, стабильнее стрим

LOG_PATH = Path(__file__).resolve().parent.parent / "broadcaster.log"


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(msg, file=sys.stderr)


def _ensure_silence_file(cache_dir: Path) -> Path | None:
    """Создаёт silence_3s.mp3 если нет. Возвращает path или None."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / "silence_3s.mp3"
    try:
        if not path.exists() or path.stat().st_size < 100:
            try:
                from pydub import AudioSegment
                silence = AudioSegment.silent(duration=3000)
                silence.export(str(path), format="mp3", bitrate="128k")
            except Exception:
                import subprocess
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=d=3",
                    "-q:a", "9", "-acodec", "libmp3lame", str(path)
                ], capture_output=True, timeout=10, check=True)
        return path
    except Exception as e:
        _log(f"Silence file creation failed: {e}")
        return None


def _get_silence_fallback(cache_dir: Path, chunk_size: int = 8192, duration_sec: float = 3.0):
    """Тишина MP3. duration_sec=3 по умолчанию. При сбое — создаём 0.1с через ffmpeg."""
    path = _ensure_silence_file(cache_dir)
    if path:
        try:
            data = path.read_bytes()
            n = int(len(data) * duration_sec / 3.0)  # пропорция от 3 сек
            for i in range(0, min(n, len(data)), chunk_size):
                yield data[i : i + chunk_size]
            return
        except Exception as e:
            _log(f"Silence read failed: {e}")
    # Fallback: 0.1 сек через ffmpeg
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fallback = cache_dir / "silence_0.1s.mp3"
    try:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=d=0.1",
            "-q:a", "9", "-acodec", "libmp3lame", str(fallback)
        ], capture_output=True, timeout=5, check=True)
        data = fallback.read_bytes()
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]
    except Exception as e:
        _log(f"Silence fallback failed: {e}")
        if path:
            try:
                data = path.read_bytes()
                for i in range(0, len(data), chunk_size):
                    yield data[i : i + chunk_size]
            except Exception:
                pass


def _safe_silence_chunks(cache_dir: Path, chunk_size: int, duration_sec: float = 0.5):
    """Всегда отдаёт хотя бы один chunk тишины. Никогда не падает."""
    yielded = False
    try:
        for chunk in _get_silence_fallback(cache_dir, chunk_size, duration_sec):
            yielded = True
            yield chunk
    except Exception as e:
        _log(f"Silence error: {e}")
    if not yielded:
        # Крайний fallback: читаем silence ещё раз
        try:
            p = _ensure_silence_file(cache_dir)
            if p and p.exists():
                data = p.read_bytes()
                if data:
                    for i in range(0, min(len(data), int(16000 * duration_sec)), chunk_size):
                        yield data[i : i + chunk_size]
        except Exception:
            pass


def _preload_worker(scheduler, ready_queue: Queue, stop_event: threading.Event) -> None:
    """Фон: забирает сегменты из scheduler, читает в память, кладёт (path, data) в ready_queue."""
    while not stop_event.is_set():
        try:
            seg = scheduler.get_segment(timeout=5.0)
            if seg is None:
                continue
            path = Path(seg)
            if not path.exists() or path.stat().st_size == 0:
                _log(f"Preload skip empty: {path}")
                continue
            data = path.read_bytes()
            ready_queue.put((path, data))
        except Exception as e:
            _log(f"Preload error: {e}")
            if stop_event.is_set():
                break


def stream_generator(scheduler, chunk_size: int = CHUNK_SIZE, cache_dir: Path | None = None):
    """Бесконечный генератор с предзагрузкой. Не падает — при любой ошибке отдаёт тишину."""
    cache_dir = cache_dir or Path("cache")
    _ensure_silence_file(cache_dir)
    ready_queue: Queue[tuple] = Queue(maxsize=2)
    stop_event = threading.Event()
    preload_thread = threading.Thread(
        target=_preload_worker,
        args=(scheduler, ready_queue, stop_event),
        daemon=True,
    )
    preload_thread.start()

    try:
        while True:
            try:
                item = None
                try:
                    item = ready_queue.get(timeout=1.0)
                except Empty:
                    _log("Queue empty, sending silence")
                    for chunk in _safe_silence_chunks(cache_dir, chunk_size, 0.5):
                        yield chunk
                    continue

                path, data = item
                for chunk in _safe_silence_chunks(cache_dir, chunk_size, 0.05):
                    yield chunk
                parent = path.parent.name
                seg_type = "dj" if parent in ("dj", "news", "weather", "system") else "track"
                _log(f"Playing [{seg_type}]: {path.name} ({len(data)} bytes)")
                for i in range(0, len(data), chunk_size):
                    yield data[i : i + chunk_size]
            except Exception as e:
                _log(f"Stream generator error: {e}")
                import traceback
                _log(traceback.format_exc())
                for chunk in _safe_silence_chunks(cache_dir, chunk_size, 1.0):
                    yield chunk
    finally:
        stop_event.set()


def run_broadcaster(scheduler, icecast_url: str, password: str, mount: str = "/live", name: str = "NAVO RADIO"):
    """
    Стримит аудио в Icecast. HTTP/1.0 без chunked (Icecast его не поддерживает).
    """
    parsed = urlparse(icecast_url.rstrip("/"))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    auth = base64.b64encode(f"source:{password}".encode()).decode("ascii")

    cache_dir = getattr(scheduler, "cache_dir", Path("cache"))
    gen = stream_generator(scheduler, cache_dir=cache_dir)
    sock = None
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((host, port))

            path = mount or "/"
            req = (
                f"PUT {path} HTTP/1.0\r\n"
                f"Host: {host}:{port}\r\n"
                f"Authorization: Basic {auth}\r\n"
                f"Content-Type: audio/mpeg\r\n"
                f"Ice-Public: 1\r\n"
                f"Ice-Name: {name}\r\n"
                f"Ice-Description: NAVO RADIO 24/7\r\n"
                "\r\n"
            )
            sock.sendall(req.encode("ascii"))

            # Дождаться 100/200 перед отправкой тела
            sock.settimeout(10)
            resp = b""
            while b"\r\n\r\n" not in resp:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    raise ConnectionError("Icecast closed")
                resp += chunk
            if resp:
                first = resp.split(b"\r\n")[0].decode("ascii", errors="replace")
                if "401" in first or "403" in first or "404" in first:
                    raise ConnectionError(f"Icecast rejected: {first}")
                _log(f"Icecast response: {first}")

            _log("Connected, starting stream...")
            sock.settimeout(120)
            # Дроссель: 128 kbps = 16 KB/s; 24 KB/s (+50%) — запас буфера для стабильности
            BYTES_PER_SEC = 24000
            for chunk in gen:
                sock.sendall(chunk)
                time.sleep(len(chunk) / BYTES_PER_SEC)

        except Exception as e:
            import traceback
            _log(f"Broadcaster error: {e}")
            _log(traceback.format_exc())
        finally:
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
        time.sleep(2)
