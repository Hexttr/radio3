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


def get_dj_comment(artist: str, title: str, city: str = "Москва") -> str:
    """
    Короткий комментарий о треке: факт об артисте или о песне.
    2-3 фразы, живым языком.
    """
    client = _get_client()
    if not client:
        return f"Только что прозвучал трек {artist} — «{title}». Отличная композиция! А теперь следующий трек."

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты диджей на радио. Отвечай ТОЛЬКО 2-3 короткими фразами на русском. "
                        "Напиши интересный факт об исполнителе или о песне. Без приветствий, сразу по делу."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Исполнитель: {artist}. Песня: {title}. Город слушателей: {city}.",
                },
            ],
            max_tokens=150,
            temperature=0.7,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text if text else f"Только что — {artist}, «{title}». Следующий трек!"
    except Exception:
        return f"Только что прозвучал {artist} — «{title}». Отличный трек! Дальше — следующая композиция."


def get_transition(next_artist: str, next_title: str, segment_type: str = "track") -> str:
    """
    Переходная фраза к следующему сегменту.
    segment_type: "track" | "news" | "weather"
    """
    if segment_type == "news":
        return "А теперь выпуск новостей!"
    if segment_type == "weather":
        return "Передаём прогноз погоды!"
    return f"А сейчас — {next_artist}, «{next_title}»."


def format_news_dj(intro: str) -> str:
    """Краткое вступление перед новостями."""
    return intro if intro else "Добрый день! Краткий выпуск новостей."


def format_weather_dj(intro: str) -> str:
    """Краткое вступление перед погодой."""
    return intro if intro else "Прогноз погоды на сегодня."
