"""ИИ Диджей — комментарии о треке, переходы, выпуски новостей/погоды."""
import os
from typing import Optional

from . import lang

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


def _get_client() -> Optional["Groq"]:
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key and GROQ_AVAILABLE:
        return Groq(api_key=api_key)
    return None


def get_dj_comment(artist: str, title: str, city: str = "Dushanbe", language: str = "ru") -> str:
    """
    Short comment about the track: a fact about the artist or song.
    2-3 phrases, conversational.
    """
    client = _get_client()
    if not client:
        return lang.get(language, "dj_fallback", artist=artist, title=title)

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": lang.get(language, "dj_system"),
                },
                {
                    "role": "user",
                    "content": f"Artist: {artist}. Song: {title}. Listeners' city: {city}.",
                },
            ],
            max_tokens=150,
            temperature=0.7,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text if text else lang.get(language, "dj_fallback", artist=artist, title=title)
    except Exception:
        return lang.get(language, "dj_fallback", artist=artist, title=title)


def get_transition(next_artist: str, next_title: str, segment_type: str = "track", language: str = "ru") -> str:
    """
    Transition phrase to the next segment.
    segment_type: "track" | "news" | "weather" | "podcast"
    """
    if segment_type == "news":
        return lang.get(language, "transition_news")
    if segment_type == "weather":
        return lang.get(language, "transition_weather")
    if segment_type == "podcast":
        return lang.get(language, "transition_podcast")
    return lang.get(language, "transition_track", artist=next_artist, title=next_title)


def format_news_dj(intro: str, language: str = "ru") -> str:
    """Brief intro before news."""
    return intro if intro else lang.get(language, "transition_news")


def format_weather_dj(intro: str, language: str = "ru") -> str:
    """Brief intro before weather."""
    return intro if intro else lang.get(language, "transition_weather")
