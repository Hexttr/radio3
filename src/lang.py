"""Language strings and config. lang: ru | en | tj"""

MONTHS = {
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "tj": ["январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"],
}


def date_str(lang: str, day: int, month: int) -> str:
    m = MONTHS.get(lang, MONTHS["en"])
    return f"{day} {m[month - 1]}"


STRINGS = {
    "ru": {
        "dj_fallback": "Только что прозвучал {artist} — «{title}». Отличный трек! Следующий.",
        "dj_system": "Ты диджей на радио. Отвечай ТОЛЬКО 2-3 короткими фразами на русском. Напиши интересный факт об исполнителе или о песне. Без приветствий, сразу по делу.",
        "transition_news": "А теперь выпуск новостей!",
        "transition_weather": "Передаём прогноз погоды!",
        "transition_podcast": "А сейчас подкаст!",
        "transition_track": "А сейчас — {artist}, «{title}».",
        "news_unavailable": "Новости временно недоступны. Возвращаемся к музыке.",
        "news_intro": "Краткий выпуск новостей. {date}.",
        "weather_unavailable": "Прогноз погоды для {city} временно недоступен.",
        "weather_template": "Погода в {city}. {desc}, {temp}{hum}.",
        "temp_format": "{n} градусов",
        "hum_format": ", влажность {n} процентов",
        "welcome": "Добро пожаловать на AI Радио. Добавьте mp3 в папку music и перезапустите.",
    },
    "en": {
        "dj_fallback": "That was {artist} with «{title}». Great track! Up next.",
        "dj_system": "You are a radio DJ. Reply in 2-3 short phrases in English only. Write an interesting fact about the artist or the song. No greetings, straight to the point.",
        "transition_news": "And now, the news briefing!",
        "transition_weather": "Here's the weather forecast!",
        "transition_podcast": "And now, a podcast!",
        "transition_track": "Up next — {artist}, «{title}».",
        "news_unavailable": "News is temporarily unavailable. Back to the music.",
        "news_intro": "News bulletin. {date}.",
        "weather_unavailable": "Weather for {city} is temporarily unavailable.",
        "weather_template": "Weather in {city}. {desc}, {temp}{hum}.",
        "temp_format": "{n} degrees",
        "hum_format": ", humidity {n} percent",
        "welcome": "Welcome to AI Radio. Add mp3 files to the music folder and restart.",
    },
    "tj": {
        "dj_fallback": "Ин ҳангоми {artist} — «{title}» буд. Трек нек! Дар навбат.",
        "dj_system": "Ту диҷей радио ҳастӣ. 2-3 ҷумлаи кӯтоҳ ба забони тоҷикӣ нависед. Факти ҷолиб дар бораи иҷрокунанда ё суруд. Бе салам.",
        "transition_news": "Ва акнун, хабарҳои ахбор!",
        "transition_weather": "Пешбиниҳои обу ҳаво!",
        "transition_podcast": "Ва акнун, подкаст!",
        "transition_track": "Дар навбат — {artist}, «{title}».",
        "news_unavailable": "Хабарҳо дастрас нестанд. Баргардед ба мусиқӣ.",
        "news_intro": "Хабарҳои мухтасар. {date}.",
        "weather_unavailable": "Обу ҳаво барои {city} дастрас нест.",
        "weather_template": "Обу ҳаво дар {city}. {desc}, {temp}{hum}.",
        "temp_format": "{n} дараҷа",
        "hum_format": ", намнокии {n} фоиз",
        "welcome": "Хуш омадед ба AI Радио. Файлҳои mp3 ба папкаи music илова кунед.",
    },
}

# Weather descriptions per language
WEATHER_DESC = {
    "ru": {
        0: "ясно", 1: "преимущественно ясно", 2: "переменная облачность", 3: "пасмурно",
        45: "туман", 48: "изморозь", 51: "морось", 53: "морось", 55: "морось",
        61: "небольшой дождь", 63: "дождь", 65: "сильный дождь", 66: "ледяной дождь", 67: "сильный ледяной дождь",
        71: "небольшой снег", 73: "снег", 75: "сильный снег", 77: "снежная крупа",
        80: "небольшой ливень", 81: "ливень", 82: "сильный ливень",
        85: "небольшой снегопад", 86: "снегопад", 95: "гроза", 96: "гроза с градом", 99: "гроза с сильным градом",
    },
    "en": {
        0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "foggy", 48: "rime fog", 51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
        61: "slight rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "heavy freezing rain",
        71: "slight snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
        80: "slight rain showers", 81: "rain showers", 82: "heavy rain showers",
        85: "slight snow showers", 86: "heavy snow showers", 95: "thunderstorm", 96: "thunderstorm with hail", 99: "heavy thunderstorm with hail",
    },
    "tj": {
        0: "осиёб", 1: "асосан осиёб", 2: "қисман абрӣ", 3: "абрнок",
        45: "туман", 48: "нарм", 51: "каме борон", 53: "борон", 55: "борони зиёд",
        61: "каме борон", 63: "борон", 65: "борони шиддат", 66: "борони яхдор", 67: "борони шадиди яхдор",
        71: "каме барф", 73: "барф", 75: "барфи зиёд", 77: "донаҳои барф",
        80: "каме борони тунук", 81: "борони тунук", 82: "борони шиддати тунук",
        85: "каме барфи тунук", 86: "барфи тунук", 95: "тӯфон", 96: "тӯфон бо жола", 99: "тӯфони шадид",
    },
}

RSS_BY_LANG = {
    "ru": [
        "https://ria.ru/export/rss2/archive/index.xml",
        "https://lenta.ru/rss/news",
        "https://www.vedomosti.ru/rss/news",
        "https://tass.ru/rss/v2.xml",
    ],
    "en": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.npr.org/1001/rss.xml",
        "https://www.theguardian.com/world/rss",
    ],
    "tj": [
        "https://www.rferl.org/Tajikistan/rss",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
}


def get(lang: str, key: str, **kwargs) -> str:
    s = STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"][key])
    return s.format(**kwargs) if kwargs else s


def weather_desc(lang: str, code: int) -> str:
    d = WEATHER_DESC.get(lang, WEATHER_DESC["en"])
    return d.get(code, d.get(2, "variable"))
