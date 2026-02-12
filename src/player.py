"""
Стриминговый плеер: читает сегменты из очереди и отдаёт байты.
Беспрерывный поток для веб-клиента.
"""
from pathlib import Path
from typing import Iterator

from .scheduler import Scheduler

CHUNK_SIZE = 8192


def stream_audio(scheduler: Scheduler) -> Iterator[bytes]:
    """
    Генерирует непрерывный поток mp3-байтов.
    Блокируется на get_segment, если очередь пуста.
    """
    while True:
        segment = scheduler.get_segment()
        if segment is None:
            continue
        path = Path(segment)
        if not path.exists():
            continue
        try:
            with open(path, "rb") as f:
                while chunk := f.read(CHUNK_SIZE):
                    yield chunk
        except Exception:
            continue
