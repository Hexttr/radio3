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

## API-ключи (опционально)

- **Groq** (для ИИ-комментариев): [console.groq.com](https://console.groq.com) → создать ключ
  ```bash
  set GROQ_API_KEY=твой_ключ
  ```
- Без ключа используются шаблонные фразы.

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

- `region.city` — город для погоды и новостей
- `intervals.news_minutes` — интервал новостей (по умолчанию 180 мин)
- `intervals.weather_minutes` — интервал погоды (по умолчанию 240 мин)

## Источники (бесплатно)

- **TTS**: Edge (Microsoft)
- **ИИ**: Groq (если указан API-ключ)
- **Новости**: RSS (РИА, Lenta, Vedomosti, ТАСС)
- **Погода**: Open-Meteo
