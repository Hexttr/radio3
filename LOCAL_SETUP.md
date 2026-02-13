# NavoRadio — локальный запуск (Windows)

## Что уже сделано

- ✅ Репозиторий склонирован, ветка `local` создана
- ✅ Python venv и зависимости установлены
- ✅ ffmpeg установлен
- ✅ Создан `.env.example`

## Шаги для полного запуска

### 1. Создай `.env` с ключами

```powershell
copy .env.example .env
# Отредактируй .env — вставь ELEVENLABS_API_KEY и GROQ_API_KEY
```

**Важно:** Без ключей ElevenLabs TTS не сработает. Варианты:
- Если есть доступ к серверу — скопируй `ELEVENLABS_API_KEY` и `GROQ_API_KEY` из `.env` на сервере
- Для быстрого старта без ключей: в `config.yaml` → `tts:` → `provider: "edge"` (бесплатный TTS)

### 2. Установи Icecast для Windows

1. Скачай: https://downloads.xiph.org/releases/icecast/icecast_win64_2.5.0.exe  
   (или https://icecast.org/download/)
2. Установи в `C:\Program Files\Icecast` (или другую папку)
3. Запусти Icecast с нашим конфигом (из папки установки Icecast):
   ```powershell
   cd "C:\Program Files\Icecast"
   .\icecast.exe -c "C:\Users\User\Desktop\radio3-local\local\icecast.xml"
   ```
   Или используй `scripts\start_local.ps1` — он запустит всё автоматически.

**Проверка:** открой http://127.0.0.1:8000 — должна открыться страница Icecast.

### 3. Добавь музыку и подкасты (опционально)

- `music/` — MP3 для ротации между слотами
- `podcasts/` — MP3 для слотов подкастов (11, 14, 17, 20 по МСК)

Без файлов приложение будет использовать тишину и TTS.

### 4. Запуск в трёх терминалах

**Терминал 1 — Icecast:**
```powershell
cd c:\Users\User\Desktop\radio3-local
& "C:\Program Files\Icecast\icecast.exe" -c ".\local\icecast.xml"
```

**Терминал 2 — Broadcaster (стримит в Icecast):**
```powershell
cd c:\Users\User\Desktop\radio3-local
.\.venv\Scripts\Activate.ps1
python run_broadcaster.py
```

**Терминал 3 — Flask (веб + API):**
```powershell
cd c:\Users\User\Desktop\radio3-local
.\.venv\Scripts\Activate.ps1
python run.py
```

### 5. Открой в браузере

- http://127.0.0.1:5000 — главная страница, поток `/live`
- http://127.0.0.1:5000/api/status — время МСК, расписание
- http://127.0.0.1:5000/api/log — лог broadcaster

## Порядок запуска

1. Сначала Icecast (порт 8000)
2. Потом run_broadcaster.py
3. Потом run.py

## Сложности и решения

| Проблема | Решение |
|----------|---------|
| Icecast не находит конфиг | Укажи полный путь к `icecast.xml` |
| Порт 8000 занят | Измени в `config.yaml` → `icecast.url` и в `local\icecast.xml` → `<port>` |
| Нет ELEVENLABS_API_KEY | В `config.yaml` → `tts:` → `provider: "edge"` (бесплатно, качество ниже) |
| Нет GROQ_API_KEY | AI-диджей не будет генерировать комментарии (будет запасной текст) |
