# Деплой AI Radio на Ubuntu

## Быстрый запуск

```bash
# Установите paramiko
pip install paramiko

# Запустите деплой (укажите свои данные)
set DEPLOY_HOST=195.133.63.34
set DEPLOY_USER=root
set DEPLOY_PASS=ваш_пароль

python deploy/deploy.py
```

На Windows PowerShell:
```powershell
$env:DEPLOY_HOST="195.133.63.34"
$env:DEPLOY_USER="root"
$env:DEPLOY_PASS="ваш_пароль"
python deploy/deploy.py
```

## Что делает скрипт

1. Устанавливает Python3, pip, venv, FFmpeg, git
2. Клонирует репо (ветка Ubuntu) в `/opt/ai-radio`
3. Создаёт venv и ставит зависимости + gunicorn
4. Копирует локальный `.env` на сервер (если есть)
5. Настраивает systemd-сервис `ai-radio`
6. Открывает порт 5000 в firewall

## Загрузка музыки

```bash
# Те же переменные DEPLOY_*
python deploy/upload_music.py
```

Копирует mp3 из локальной `music/` на сервер и перезапускает сервис.

## После деплоя

- **Эфир:** http://IP_SERVER:5000
- **Музыка:** загрузите mp3 в `/opt/ai-radio/music/` или используйте `upload_music.py`
- **Groq:** `.env` копируется автоматически (если есть локально)

## Ручные команды на сервере

```bash
ssh root@IP_SERVER

# Статус
systemctl status ai-radio

# Логи
journalctl -u ai-radio -f

# Перезапуск
systemctl restart ai-radio
```
