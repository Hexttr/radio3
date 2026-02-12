"""TTS: Edge (free) or ElevenLabs."""
import asyncio
import hashlib
import os
from pathlib import Path

import edge_tts
from pydub import AudioSegment


def _generate_edge(text: str, voice: str, rate: str, volume: str, output_path: Path) -> None:
    async def _run():
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        await communicate.save(str(output_path))

    asyncio.run(_run())


def _generate_elevenlabs(text: str, voice_id: str, model_id: str, api_key: str, output_path: Path) -> None:
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        raise ImportError("Install elevenlabs: pip install elevenlabs")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )
    data = b""
    if hasattr(audio, "__iter__") and not isinstance(audio, (bytes, bytearray)):
        for chunk in audio:
            if chunk:
                data += chunk if isinstance(chunk, bytes) else bytes(chunk)
    else:
        data = bytes(audio) if audio else b""
    if not data:
        raise ValueError("ElevenLabs returned empty audio")
    output_path.write_bytes(data)


def generate_tts(text: str, cache_dir: Path, config: dict, cache_salt: str = "") -> Path:
    """
    Generate TTS mp3. Caches by text hash (+ salt для новостей/погоды — свежесть).
    Config: provider, voice, rate, volume (Edge) | voice_id, model_id, api_key_env (ElevenLabs)
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("TTS: empty text")

    cache_dir.mkdir(parents=True, exist_ok=True)
    boost_salt = str(config.get("volume_boost_db", 0))
    key = hashlib.md5((text + cache_salt + boost_salt).encode("utf-8")).hexdigest()
    output_path = cache_dir / f"{key}.mp3"

    # Не возвращать битые/пустые кэш-файлы
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path
    if output_path.exists():
        output_path.unlink()

    provider = (config.get("provider") or "edge").lower()

    if provider == "elevenlabs":
        api_key = os.environ.get(config.get("api_key_env", "ELEVENLABS_API_KEY"))
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY not set. Add to .env when using elevenlabs provider.")
        if len(text) > 9000:
            raise ValueError(f"TTS text too long ({len(text)} chars), max 9000 for ElevenLabs")
        _generate_elevenlabs(
            text,
            voice_id=config.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
            model_id=config.get("model_id", "eleven_multilingual_v2"),
            api_key=api_key,
            output_path=output_path,
        )
    else:
        _generate_edge(
            text,
            voice=config.get("voice", "en-GB-SoniaNeural"),
            rate=config.get("rate", "+0%"),
            volume=config.get("volume", "+0%"),
            output_path=output_path,
        )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValueError("TTS generated empty file")

    # Усиление громкости (диджей/новости/погода заметнее на фоне музыки)
    boost_db = config.get("volume_boost_db", 0)
    if boost_db and boost_db != 0:
        try:
            seg = AudioSegment.from_mp3(str(output_path))
            seg = seg + boost_db
            seg.export(str(output_path), format="mp3", bitrate="128k")
        except Exception:
            pass

    return output_path
