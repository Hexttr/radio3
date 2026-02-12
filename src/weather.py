"""Fetch weather via Open-Meteo (free, no API key)."""
import requests

from . import lang


def fetch_weather(latitude: float = 38.56, longitude: float = 68.78, city: str = "Dushanbe", timezone: str = "Asia/Dushanbe", language: str = "ru") -> str:
    """
    Get current weather via Open-Meteo.
    Returns text for TTS.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code",
        "timezone": timezone,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("current", {})
    except Exception:
        return lang.get(language, "weather_unavailable", city=city)

    temp = data.get("temperature_2m")
    humidity = data.get("relative_humidity_2m")
    code = data.get("weather_code", 0)
    desc = lang.weather_desc(language, code)

    temp_str = lang.get(language, "temp_format", n=int(round(temp))) if temp is not None else ""
    hum_str = lang.get(language, "hum_format", n=int(humidity)) if humidity is not None else ""

    return lang.get(language, "weather_template", city=city, desc=desc, temp=temp_str, hum=hum_str)
