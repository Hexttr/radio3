# NAVO RADIO — контекст для агента

## Что это

24/7 онлайн-радио с единым эфиром через Icecast. Расписание по МСК:
- **Новости:** 9, 12, 15, 18, 21
- **Погода:** 7, 10, 13, 16, 19
- **Подкасты:** 11, 14, 17, 20 (mp3 из `podcasts/`)
- Между слотами — треки из `music/` и реплики диджея (комментарий о прошлом → переход → трек).

## Ключевые файлы

| Файл | Назначение |
|------|------------|
| `src/broadcaster.py` | Стримит через сокет (режим socket) |
| `src/stream_ffmpeg.py` | Стримит через ffmpeg pipe→CBR→Icecast (режим ffmpeg, рекомендуется) |
| `src/scheduler.py` | Расписание, очереди сегментов, TTS для диджея/новостей/погоды |
| `src/main.py` | Flask: `/api/status`, `/api/ping`, `/api/log` |
| `run.py` | Точка входа Flask + Scheduler |
| `run_broadcaster.py` | Отдельный процесс — broadcaster в Icecast |
| `config.yaml` | Конфигурация (язык, папки, TTS, Groq, Icecast) |
| `deploy/force_update.py` | Деплой: git pull, restart сервисов |
| `deploy/fetch_logs.py` | Логи с сервера (нужен .env.deploy с DEPLOY_*) |

## Ключи и переменные окружения

**Все ключи хранятся в `.env`** (не в репозитории). Нужны:
- `ELEVENLABS_API_KEY` — TTS (диджей, новости, погода)
- `GROQ_API_KEY` — AI-диджей (комментарии, переходы)
- Для деплоя: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PASS`

## Архитектура

1. **ai-radio** (Flask) — веб, API, Scheduler (генерирует сегменты в очередь)
2. **ai-radio-broadcaster** — читает очередь, стримит в Icecast
3. **Icecast** — раздаёт поток клиентам

Клиенты слушают `/live` (проксируется на Icecast).

## Локальная разработка (Windows)

1. Установить: Python, ffmpeg, Icecast для Windows (или Docker)
2. Создать `.env` с ключами
3. Запустить в двух терминалах: `python run.py` и `python run_broadcaster.py`
4. Фронтенд: `static/index.html`, поток `/live`

## Деплой

```bash
git push origin Ubuntu
python deploy/force_update.py
```

Сервер: Ubuntu, systemd (ai-radio, ai-radio-broadcaster, icecast2).

## Важные детали

- `icecast.broadcaster`: "ffmpeg" (по умолчанию) или "socket"
- ffmpeg: pipe→decode→CBR 128k→Icecast, без ручного дросселя
- При пустой очереди — тишина (`cache/silence_3s.mp3`)
- TTS: ElevenLabs с retry 3x при сбоях
- Музыка: `music/*.mp3`, подкасты: `podcasts/*.mp3`
