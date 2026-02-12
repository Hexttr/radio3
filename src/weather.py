"""Загрузка погоды через Open-Meteo (бесплатно, без API-ключа)."""
import requests

# Коды погоды Open-Meteo -> описание
WEATHER_CODES = {
    0: "ясно",
    1: "преимущественно ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "изморозь",
    51: "морось",
    53: "морось",
    55: "морось",
    61: "небольшой дождь",
    63: "дождь",
    65: "сильный дождь",
    66: "ледяной дождь",
    67: "сильный ледяной дождь",
    71: "небольшой снег",
    73: "снег",
    75: "сильный снег",
    77: "снежная крупа",
    80: "небольшой ливень",
    81: "ливень",
    82: "сильный ливень",
    85: "небольшой снегопад",
    86: "снегопад",
    95: "гроза",
    96: "гроза с градом",
    99: "гроза с сильным градом",
}


def fetch_weather(latitude: float = 55.7558, longitude: float = 37.6173, city: str = "Москва") -> str:
    """
    Получает текущую погоду через Open-Meteo.
    Возвращает текст для озвучки.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code",
        "timezone": "Europe/Moscow",
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("current", {})
    except Exception:
        return f"Прогноз погоды для {city} временно недоступен."

    temp = data.get("temperature_2m")
    humidity = data.get("relative_humidity_2m")
    code = data.get("weather_code", 0)
    desc = WEATHER_CODES.get(code, "переменная облачность")

    temp_str = f"{int(round(temp))} градусов" if temp is not None else ""
    hum_str = f", влажность {int(humidity)} процентов" if humidity is not None else ""

    return f"Прогноз погоды в {city}. {desc}, {temp_str}{hum_str}."
