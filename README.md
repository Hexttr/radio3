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

### Вариант A: ICEcast (единый эфир для всех)

1. Установи **Icecast2** (Windows: [скачать](https://icecast.org/download/), Linux: `apt install icecast2`)
2. Запусти broadcaster (стримит в Icecast):
   ```bash
   python run_broadcaster.py
   ```
3. Запусти веб-сервер:
   ```bash
   python run.py
   ```
4. Открой [http://127.0.0.1:5000](http://127.0.0.1:5000) — клик Play подключит к потоку `/live`.

Flask проксирует `/live` на Icecast для локальной разработки; на сервере nginx проксирует сам.

### Вариант B: Без Icecast (устаревший)

```bash
python run.py
```

Раньше фронт использовал `/api/next` (отдельные сегменты). Сейчас используется поток ICEcast.

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
- `intervals.news_minutes` — интервал новостей (360 = каждые 6 ч)
- `intervals.weather_minutes` — интервал погоды (480 = каждые 8 ч)
- `tts.provider` — `edge` (бесплатно) или `elevenlabs`
- `tts.volume_boost_db` — усиление голоса в dB (например 6), чтобы TTS был слышнее музыки

## TTS: Edge vs ElevenLabs

| Provider   | Ключ   | Качество      |
|------------|--------|---------------|
| **edge**   | Не нужен | Хорошее       |
| **elevenlabs** | ELEVENLABS_API_KEY | Очень высокое |

ElevenLabs: [elevenlabs.io](https://elevenlabs.io) → Profile → API Key → Create.

### Сколько нужно ElevenLabs в месяц?

Расчёт для круглосуточного эфира (новости каждые 6 ч, погода каждые 8 ч):

| Сегмент | Раз в день | Символов за выпуск | Символов/мес |
|---------|------------|--------------------|--------------|
| Новости (8 шт) | 4 | ~6 500 | ~780k |
| Погода | 3 | ~80 | ~7 200 |
| Диджей + переходы | по трекам | ~230/трек | кэш (200+ треков ≈ 50k) |

**Итого: ~840k символов/мес.** Кэш снижает расход: повторные треки не озвучиваются.

**Тарифы ElevenLabs** ([pricing](https://elevenlabs.io/pricing)):
- **Creator** (100k/мес, $22) — мало
- **Pro** (500k/мес, $99) — мало
- **Scale** (2M/мес, $330) — с запасом
- **Business** (11M/мес) — избыточно

Рекомендация при 6ч/8ч: **Pro** не хватает, **Scale** (~$330/мес) — оптимально. Другие расходы: Groq бесплатен, хостинг — по факту.

Оплата: достаточно оформить подписку на [elevenlabs.io](https://elevenlabs.io) → Billing. API-ключ не меняется — лимит символов просто увеличивается.
