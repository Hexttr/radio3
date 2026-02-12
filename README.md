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
- `tts.volume_boost_db` — усиление голоса в dB (например 6), чтобы TTS был слышнее музыки

## TTS: Edge vs ElevenLabs

| Provider   | Ключ   | Качество      |
|------------|--------|---------------|
| **edge**   | Не нужен | Хорошее       |
| **elevenlabs** | ELEVENLABS_API_KEY | Очень высокое |

ElevenLabs: [elevenlabs.io](https://elevenlabs.io) → Profile → API Key → Create.

### Сколько нужно ElevenLabs в месяц?

Расчёт для круглосуточного эфира (по умолчанию: новости каждые 3 ч, погода каждые 4 ч):

| Сегмент | Раз в день | Символов за выпуск | Символов/мес |
|---------|------------|--------------------|--------------|
| Новости (8 шт) | 8 | ~6 500 | ~1,56M |
| Погода | 6 | ~80 | ~14 400 |
| Диджей + переходы | по трекам | ~230/трек | кэш (200+ треков ≈ 50k) |

**Итого: ~1,6–1,7M символов/мес.** Кэш снижает расход: повторные треки не озвучиваются.

**Тарифы ElevenLabs** ([pricing](https://elevenlabs.io/pricing)):
- **Creator** (100k/мес, $22) — мало
- **Pro** (500k/мес, $99) — мало
- **Scale** (2M/мес, $330) — подходит
- **Business** (11M/мес) — с запасом

Рекомендация: **Scale** (2M) или **Pro** с запасом по кэшу.

Оплата: достаточно оформить подписку на [elevenlabs.io](https://elevenlabs.io) → Billing. API-ключ не меняется — лимит символов просто увеличивается.
