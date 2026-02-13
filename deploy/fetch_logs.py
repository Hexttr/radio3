#!/usr/bin/env python
"""
Получить логи с сервера. Запуск: python deploy/fetch_logs.py
Использует DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASS из .env или переменных окружения.
"""
import os
import sys
from pathlib import Path

# Загрузить .env и .env.deploy из корня проекта
ROOT = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv
for f in (ROOT / ".env.deploy", ROOT / ".env"):
    if f.exists():
        load_dotenv(f)

try:
    import paramiko
except ImportError:
    print("pip install paramiko python-dotenv")
    sys.exit(1)

APP_DIR = "/opt/ai-radio"

CMDS = [
    ("broadcaster.log", f"tail -150 {APP_DIR}/broadcaster.log 2>/dev/null || echo 'no log'"),
    ("ai-radio stderr", "journalctl -u ai-radio -n 80 --no-pager 2>/dev/null"),  # TTS, scheduler
    ("ai-radio-broadcaster", "journalctl -u ai-radio-broadcaster -n 30 --no-pager 2>/dev/null"),
]


def main():
    host = os.environ.get("DEPLOY_HOST")
    user = os.environ.get("DEPLOY_USER", "root")
    password = os.environ.get("DEPLOY_PASS")
    if not host or not password:
        print("Укажите DEPLOY_HOST и DEPLOY_PASS в .env или переменных окружения")
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)

    for name, cmd in CMDS:
        print(f"\n{'='*60}\n### {name}\n{'='*60}")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="replace")
        print(out[:8000])

    client.close()


if __name__ == "__main__":
    main()
