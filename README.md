# AI Radio

24/7 радио с ИИ-диджеем: музыка, комментарии о треках, новости, погода.

## Требования

- Python 3.10+
- **FFmpeg** (для pydub) — [скачать](https://ffmpeg.org/download.html), добавить в PATH
- Mp3-файлы в папке `music/`

## Установка

```bash
pip install -r requirements.txt
```

## API-ключи

- **Groq** (ИИ-комментарии): [console.groq.com](https://console.groq.com)
- **ElevenLabs** (TTS, опционально): [elevenlabs.io](https://elevenlabs.io) → Profile → API Key

В `.env`:
```
GROQ_API_KEY=...
ELEVENLABS_API_KEY=...   # если tts.provider: elevenlabs
```

## Запуск

```bash
python run.py
```

Открой [http://127.0.0.1:5000](http://127.0.0.1:5000) — страница начнёт воспроизводить поток.

## Структура

```
radio3/
├── music/          ← сюда mp3 (формат: Artist - Title.mp3 или с ID3-тегами)
├── cache/          ← кэш озвучек (создаётся автоматически)
├── config.yaml     ← настройки
└── run.py
```

## Конфигурация (config.yaml)

- `language` — **ru** | **en** | **tj** (диджей, новости, погода)
- `region.city` — город для погоды и новостей
- `intervals.news_minutes` — интервал новостей (180 мин)
- `intervals.weather_minutes` — интервал погоды (240 мин)
- `tts.provider` — `edge` (бесплатно) или `elevenlabs`

## TTS: Edge vs ElevenLabs

| Provider   | Ключ   | Качество      |
|------------|--------|---------------|
| **edge**   | Не нужен | Хорошее       |
| **elevenlabs** | ELEVENLABS_API_KEY | Очень высокое |

ElevenLabs: [elevenlabs.io](https://elevenlabs.io) → Profile → API Key → Create. Бесплатный тариф: 10 000 символов/мес.
