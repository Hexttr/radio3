#!/usr/bin/env python
"""
Принудительное обновление на сервере: git reset --hard, restart.
Запуск: set DEPLOY_HOST=... DEPLOY_USER=... DEPLOY_PASS=... && python deploy/force_update.py
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Установите paramiko: pip install paramiko")
    sys.exit(1)

APP_DIR = "/opt/ai-radio"


def main():
    host = os.environ.get("DEPLOY_HOST")
    user = os.environ.get("DEPLOY_USER", "root")
    password = os.environ.get("DEPLOY_PASS")
    if not host or not password:
        print("Укажите DEPLOY_HOST и DEPLOY_PASS")
        sys.exit(1)

    print(f"Подключение к {user}@{host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)

    cmds = [
        "getent group icecast2 >/dev/null || groupadd --system icecast2",
        "getent passwd icecast2 >/dev/null || useradd --system -g icecast2 -d /var/log/icecast2 -s /usr/sbin/nologin icecast2",
        "mkdir -p /var/log/icecast2 && chown icecast2:icecast2 /var/log/icecast2",
        "grep -o '<source-timeout>[0-9]*</source-timeout>' /etc/icecast2/icecast.xml || true",
        "sed -i 's/<source-timeout>[0-9]*<\\/source-timeout>/<source-timeout>120<\\/source-timeout>/' /etc/icecast2/icecast.xml 2>/dev/null || true",
        f"cd {APP_DIR} && git fetch origin Ubuntu && git reset --hard origin/Ubuntu && git status",
        f"cd {APP_DIR} && head -70 src/news.py | tail -5",
        "systemctl restart icecast2 ai-radio ai-radio-broadcaster",
        "sleep 1 && systemctl status icecast2 --no-pager || true",
        "sleep 2 && systemctl is-active ai-radio ai-radio-broadcaster icecast2",
    ]
    for cmd in cmds:
        print(f"\n$ {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        if out:
            try:
                s = out.decode("utf-8", errors="replace")
            except AttributeError:
                s = str(out)
            print(s[:500])
        if err:
            print(err, file=sys.stderr)
        if code != 0:
            print(f"Выход: {code}")
        else:
            print("OK")

    client.close()
    print("\nГотово. Проверь https://navoradio.com/api/ping и сделай Ctrl+Shift+R на главной.")


if __name__ == "__main__":
    main()
