"""ИИ Диджей — комментарии о треке, переходы, выпуски новостей/погоды."""
import os
from typing import Optional

# Groq — бесплатный тариф
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


def get_dj_comment(artist: str, title: str, city: str = "Dushanbe") -> str:
    """
    Short comment about the track: a fact about the artist or song.
    2-3 phrases, conversational.
    """
    client = _get_client()
    if not client:
        return f"That was {artist} with «{title}». Great track! Up next, another one."

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a radio DJ. Reply in 2-3 short phrases in English only. "
                        "Write an interesting fact about the artist or the song. No greetings, straight to the point."
                    ),
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
        return text if text else f"That was {artist}, «{title}». Next track coming up!"
    except Exception:
        return f"That was {artist} — «{title}». Great tune! Next up."


def get_transition(next_artist: str, next_title: str, segment_type: str = "track") -> str:
    """
    Transition phrase to the next segment.
    segment_type: "track" | "news" | "weather"
    """
    if segment_type == "news":
        return "And now, the news briefing!"
    if segment_type == "weather":
        return "Here's the weather forecast!"
    return f"Up next — {next_artist}, «{next_title}»."


def format_news_dj(intro: str) -> str:
    """Brief intro before news."""
    return intro if intro else "News briefing."


def format_weather_dj(intro: str) -> str:
    """Brief intro before weather."""
    return intro if intro else "Weather forecast for today."
