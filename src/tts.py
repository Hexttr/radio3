"""TTS: Edge (free) or ElevenLabs."""
import asyncio
import hashlib
import os
from pathlib import Path

import edge_tts


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

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(audio, "__iter__") and not isinstance(audio, (bytes, bytearray)):
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
    else:
        output_path.write_bytes(bytes(audio))


def generate_tts(text: str, cache_dir: Path, config: dict, cache_salt: str = "") -> Path:
    """
    Generate TTS mp3. Caches by text hash (+ salt для новостей/погоды — свежесть).
    Config: provider, voice, rate, volume (Edge) | voice_id, model_id, api_key_env (ElevenLabs)
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5((text + cache_salt).encode("utf-8")).hexdigest()
    output_path = cache_dir / f"{key}.mp3"

    if output_path.exists():
        return output_path

    provider = (config.get("provider") or "edge").lower()

    if provider == "elevenlabs":
        api_key = os.environ.get(config.get("api_key_env", "ELEVENLABS_API_KEY"))
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY not set. Add to .env when using elevenlabs provider.")
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

    return output_path
