"""Fetch weather via Open-Meteo (free, no API key)."""
import requests

from . import lang


def _wind_dir(deg: int, language: str = "ru") -> str:
    """Направление ветра по градусам."""
    dirs = lang.WIND_DIRECTIONS.get(language, lang.WIND_DIRECTIONS["ru"])
    if deg < 23 or deg >= 338:
        return dirs["n"]
    if 23 <= deg < 68:
        return dirs["ne"]
    if 68 <= deg < 113:
        return dirs["e"]
    if 113 <= deg < 158:
        return dirs["se"]
    if 158 <= deg < 203:
        return dirs["s"]
    if 203 <= deg < 248:
        return dirs["sw"]
    if 248 <= deg < 293:
        return dirs["w"]
    return dirs["nw"]


def fetch_weather(latitude: float = 38.56, longitude: float = 68.78, city: str = "Dushanbe", timezone: str = "Asia/Dushanbe", language: str = "ru") -> str:
    """
    Get current weather via Open-Meteo.
    Returns text for TTS (подробный выпуск).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,apparent_temperature,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": timezone,
        "forecast_days": 1,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        j = r.json()
        current = j.get("current", {})
        daily = j.get("daily", {})
    except Exception:
        return lang.get(language, "weather_unavailable", city=city)

    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    code = current.get("weather_code", 0)
    desc = lang.weather_desc(language, code)
    apparent = current.get("apparent_temperature")
    wind_speed = current.get("wind_speed_10m")
    wind_deg = current.get("wind_direction_10m", 0)
    pressure = current.get("surface_pressure")
    precip = current.get("precipitation", 0) or 0

    daily_max = daily.get("temperature_2m_max", [None])[0] if daily.get("temperature_2m_max") else None
    daily_min = daily.get("temperature_2m_min", [None])[0] if daily.get("temperature_2m_min") else None

    parts = [lang.get(language, "weather_intro", city=city, desc=desc)]
    if temp is not None:
        parts.append(lang.get(language, "temp_format", n=int(round(temp))))
    if apparent is not None and abs(apparent - temp) > 1:
        parts.append(lang.get(language, "feels_format", n=int(round(apparent))))
    if daily_max is not None and daily_min is not None:
        parts.append(lang.get(language, "daily_format", max=int(round(daily_max)), min=int(round(daily_min))))
    if humidity is not None:
        parts.append(lang.get(language, "hum_format", n=int(humidity)))
    if wind_speed is not None and wind_speed >= 5:
        wdir = _wind_dir(int(wind_deg), language) if wind_deg is not None else ""
        parts.append(lang.get(language, "wind_format", speed=int(round(wind_speed)), dir=wdir))
    if pressure is not None:
        parts.append(lang.get(language, "pressure_format", n=int(round(pressure))))
    if precip and precip >= 1:
        parts.append(lang.get(language, "precip_format", n=int(round(precip))))

    return ". ".join(p for p in parts if p)
