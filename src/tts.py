"""Озвучка текста через Edge TTS (бесплатно)."""
import asyncio
import hashlib
from pathlib import Path

import edge_tts


async def _generate_tts(text: str, voice: str, rate: str, volume: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(str(output_path))


def generate_tts(
    text: str,
    cache_dir: Path,
    voice: str = "ru-RU-SvetlanaNeural",
    rate: str = "+0%",
    volume: str = "+0%",
) -> Path:
    """
    Генерирует mp3 с озвучкой. Использует кэш по хэшу текста.
    Возвращает путь к файлу.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    output_path = cache_dir / f"{key}.mp3"

    if output_path.exists():
        return output_path

    asyncio.run(_generate_tts(text, voice, rate, volume, output_path))
    return output_path
