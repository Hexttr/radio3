"""
Стриминг через ffmpeg — единый CBR 128k 44.1kHz для всех клиентов.
Перекодирование устраняет: invalid packets на границах сегментов, разный sample rate
(диджей 44.1k vs музыка 48k), VBR — причина "3x скорость" на мобильных.
-fflags +discardcorrupt -err_detect ignore_err — не падать на битых пакетах.
"""
import json
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from .broadcaster import (
    CHUNK_SIZE,
    _ensure_silence_file,
    _get_silence_fallback,
    _log,
    _safe_silence_chunks,
)
from .track_parser import parse_track


def _write_now_playing(path: Path, cache_dir: Path, last_track: dict, history: list) -> None:
    """Добавить сегмент в историю для /api/now. history — список {t, artist, title, type}."""
    try:
        t = time.time()
        parent = path.parent.name
        if parent == "news":
            entry = {"t": t, "artist": "", "title": "", "type": "news"}
        elif parent == "weather":
            entry = {"t": t, "artist": "", "title": "", "type": "weather"}
        elif parent in ("dj", "system"):
            entry = {"t": t, "artist": last_track.get("artist", ""), "title": last_track.get("title", ""), "type": "dj"}
        else:
            artist, title = parse_track(path)
            last_track["artist"], last_track["title"] = artist, title
            entry = {"t": t, "artist": artist, "title": title, "type": "track"}
        history.append(entry)
        while history and t - history[0]["t"] > 300:
            history.pop(0)
        (cache_dir / ".now_playing.json").write_text(
            json.dumps({"history": history}, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        _log(f"now_playing write failed: {e}")


def _icecast_url(icecast_http: str, password: str, mount: str) -> str:
    """http://host:port -> icecast://source:PASS@host:port/mount"""
    p = urlparse(icecast_http.rstrip("/"))
    host = p.hostname or "127.0.0.1"
    port = p.port or 8000
    m = (mount or "/live").lstrip("/")
    return f"icecast://source:{password}@{host}:{port}/{m}"


def run_ffmpeg_broadcaster(scheduler, icecast_url: str, password: str, mount: str = "/live", name: str = "NAVO RADIO"):
    """
    Стримит через ffmpeg: pipe -> decode -> CBR 128k -> Icecast.
    Без ручного дросселя — ffmpeg сам держит стабильный поток.
    """
    cache_dir = getattr(scheduler, "cache_dir", Path("cache"))
    _ensure_silence_file(cache_dir)
    dest = _icecast_url(icecast_url, password, mount or "/live")

    # ffmpeg: stdin (mp3) -> decode -> CBR 128k 44.1kHz stereo -> Icecast
    # Перекодирование: единый формат для всех клиентов (мобильные, десктоп)
    # discardcorrupt + ignore_err — не падать на битых пакетах на границах сегментов
    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "warning",
        "-fflags", "+discardcorrupt",
        "-err_detect", "ignore_err",
        "-f", "mp3",
        "-i", "pipe:0",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-f", "mp3",
        "-content_type", "audio/mpeg",
        "-ice_name", name,
        "-ice_public", "1",
        dest,
    ]

    while True:
        try:
            gen = _stream_segments(scheduler, cache_dir)
            prebuf = b""
            _log("Prebuffering 64KB...")
            for chunk in gen:
                prebuf += chunk
                if len(prebuf) >= 65536:
                    break
            if not prebuf:
                _log("Prebuffer empty, using silence")
                prebuf = b"".join(_get_silence_fallback(cache_dir, CHUNK_SIZE, 1.0))

            _log("Starting ffmpeg stream...")
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=65536,
            )
            proc.stdin.write(prebuf)
            proc.stdin.flush()

            err_lines = []

            def read_stderr():
                for line in proc.stderr:
                    s = line.decode("utf-8", errors="replace").strip()
                    if s:
                        err_lines.append(s)
                        _log(f"ffmpeg: {s}")

            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()

            for chunk in gen:
                if proc.poll() is not None:
                    break
                try:
                    proc.stdin.write(chunk)
                    proc.stdin.flush()
                except BrokenPipeError:
                    break

            proc.stdin.close()
            proc.wait(timeout=10)
            stderr_thread.join(timeout=2)
            if err_lines:
                _log(f"ffmpeg exit (last): {'; '.join(err_lines[-3:])}")
        except Exception as e:
            _log(f"ffmpeg broadcaster error: {e}")
            import traceback
            _log(traceback.format_exc())
        _log("Reconnecting in 3s...")
        time.sleep(3)


def _stream_segments(scheduler, cache_dir: Path):
    """Генератор: сегменты по одному, читаем файл чанками (без полной загрузки в память)."""
    chunk_size = CHUNK_SIZE
    last_track: dict = {"artist": "", "title": ""}
    history: list = []
    while True:
        try:
            seg = scheduler.get_segment(timeout=5.0)
            if seg is None:
                for c in _safe_silence_chunks(cache_dir, chunk_size, 0.5):
                    yield c
                continue

            path = Path(seg)
            if not path.exists() or path.stat().st_size == 0:
                _log(f"Segment empty: {path}")
                for c in _safe_silence_chunks(cache_dir, chunk_size, 0.5):
                    yield c
                continue

            # Добавить в историю для /api/now (с учётом буфера плеера ~15 сек)
            _write_now_playing(path, cache_dir, last_track, history)

            # Пауза между сегментами
            for c in _safe_silence_chunks(cache_dir, chunk_size, 0.05):
                yield c

            parent = path.parent.name
            seg_type = "dj" if parent in ("dj", "news", "weather", "system") else "track"
            _log(f"Playing [{seg_type}]: {path.name}")

            # Читаем файл чанками — не грузим весь трек в память
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            _log(f"Stream error: {e}")
            import traceback
            _log(traceback.format_exc())
            for c in _safe_silence_chunks(cache_dir, chunk_size, 1.0):
                yield c
