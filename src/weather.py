"""Fetch weather via Open-Meteo (free, no API key)."""
import requests

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "slight snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "heavy thunderstorm with hail",
}


def fetch_weather(latitude: float = 51.5074, longitude: float = -0.1278, city: str = "London", timezone: str = "Europe/London") -> str:
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
        return f"Weather for {city} is temporarily unavailable."

    temp = data.get("temperature_2m")
    humidity = data.get("relative_humidity_2m")
    code = data.get("weather_code", 0)
    desc = WEATHER_CODES.get(code, "variable clouds")

    temp_str = f"{int(round(temp))} degrees" if temp is not None else ""
    hum_str = f", humidity {int(humidity)} percent" if humidity is not None else ""

    return f"Weather in {city}. {desc}, {temp_str}{hum_str}."
