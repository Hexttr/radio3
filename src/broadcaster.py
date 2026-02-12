"""
Broadcaster — читает сегменты из Scheduler и стримит в Icecast.
Icecast не поддерживает chunked encoding, поэтому используем HTTP/1.0.
"""
import base64
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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


def _get_silence_fallback(cache_dir: Path, chunk_size: int = 8192):
    """~3 сек тишины MP3. Pydub или ffmpeg."""
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
        data = path.read_bytes()
    except Exception as e:
        _log(f"Silence fallback failed: {e}")
        return
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def stream_generator(scheduler, chunk_size: int = 8192, cache_dir: Path | None = None):
    """Бесконечный генератор: читает сегменты и отдаёт байты. При паузе — тишина."""
    cache_dir = cache_dir or Path("cache")
    while True:
        seg = scheduler.get_segment(timeout=5)
        if seg is None:
            _log("Queue empty, sending silence")
            for chunk in _get_silence_fallback(cache_dir, chunk_size):
                yield chunk
            continue
        path = Path(seg)
        if not path.exists() or path.stat().st_size == 0:
            _log(f"Segment missing/empty: {path}")
            for chunk in _get_silence_fallback(cache_dir, chunk_size):
                yield chunk
            continue
        _log(f"Playing: {path.name} ({path.stat().st_size} bytes)")
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception:
            for chunk in _get_silence_fallback(cache_dir, chunk_size):
                yield chunk


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
            sent = 0
            for chunk in gen:
                sock.sendall(chunk)
                sent += len(chunk)
                if sent >= 65536:
                    sock.settimeout(60)
                    sent = 0

        except Exception as e:
            _log(f"Broadcaster error: {e}")
        finally:
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
        time.sleep(5)
