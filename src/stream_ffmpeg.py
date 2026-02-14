"""
Стриминг через ffmpeg — стабильный CBR, буферизация на стороне ffmpeg.
Вместо ручного дросселя: ffmpeg читает из pipe, кодирует в CBR 128k, стримит в Icecast.
Python подаёт MP3-байты в stdin; ffmpeg сам контролирует темп выдачи.
Pipe buffer (~64KB) даёт естественный backpressure — не нужно sleep().
"""
import subprocess
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

    # ffmpeg: stdin (mp3) -> decode -> CBR 128k -> Icecast
    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "warning",
        "-i", "pipe:0",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        "-f", "mp3",
        "-content_type", "audio/mpeg",
        dest,
    ]

    while True:
        try:
            _log("Starting ffmpeg stream...")
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=65536,  # 64 KB буфер
            )

            for chunk in _stream_segments(scheduler, cache_dir):
                if proc.poll() is not None:
                    break
                try:
                    proc.stdin.write(chunk)
                    proc.stdin.flush()
                except BrokenPipeError:
                    break

            proc.stdin.close()
            _, err = proc.communicate(timeout=5)
            if err:
                _log(f"ffmpeg stderr: {err.decode('utf-8', errors='replace')[:500]}")
        except Exception as e:
            _log(f"ffmpeg broadcaster error: {e}")
            import traceback
            _log(traceback.format_exc())
        _log("Reconnecting in 3s...")
        time.sleep(3)


def _stream_segments(scheduler, cache_dir: Path):
    """Генератор: сегменты по одному, читаем файл чанками (без полной загрузки в память)."""
    chunk_size = CHUNK_SIZE
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
