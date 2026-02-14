#!/usr/bin/env python
"""
Принудительное обновление на сервере: git reset --hard, restart.
Запуск: set DEPLOY_HOST=... DEPLOY_USER=... DEPLOY_PASS=... && python deploy/force_update.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    for f in (ROOT / ".env.deploy", ROOT / ".env"):
        if f.exists():
            load_dotenv(f)
            break
except ImportError:
    pass

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
        "sed -i 's/<source-timeout>.*<\\/source-timeout>/<source-timeout>120<\\/source-timeout>/' /etc/icecast2/icecast.xml 2>/dev/null || true",
        "sed -i 's/<queue-size>.*<\\/queue-size>/<queue-size>1048576<\\/queue-size>/' /etc/icecast2/icecast.xml 2>/dev/null || true",
        f"cd {APP_DIR} && git fetch origin Ubuntu && git reset --hard origin/Ubuntu && git status",
        f"cd {APP_DIR} && mkdir -p cache cache/dj && ffmpeg -y -f lavfi -i anullsrc=d=3 -q:a 9 -acodec libmp3lame cache/silence_3s.mp3 2>/dev/null || true",
        f"cd {APP_DIR} && ./venv/bin/python scripts/create_fallback_dj.py 2>/dev/null || true",
        f"cd {APP_DIR} && head -70 src/news.py | tail -5",
        "systemctl restart icecast2 ai-radio ai-radio-broadcaster",
        "sleep 1 && systemctl status icecast2 --no-pager || true",
        "sleep 2 && systemctl is-active ai-radio ai-radio-broadcaster icecast2",
        # Nginx: отключить HTTP/2 для /live — ERR_HTTP2_PROTOCOL_ERROR при стриминге
        "for f in /etc/nginx/sites-available/navoradio /etc/nginx/sites-available/navoradio-le-ssl.conf /etc/nginx/sites-enabled/navoradio; do [ -f \"$f\" ] && sed -i 's/listen 443 ssl http2/listen 443 ssl/g' \"$f\"; done",
        "for f in /etc/nginx/sites-available/navoradio /etc/nginx/sites-available/navoradio-le-ssl.conf /etc/nginx/sites-enabled/navoradio; do [ -f \"$f\" ] && grep -q 'proxy_send_timeout 86400' \"$f\" || sed -i '/proxy_read_timeout 86400s;/a\\\n        proxy_send_timeout 86400s;' \"$f\"; done",
        "nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || true",
    ]
    for cmd in cmds:
        print(f"\n$ {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        if out:
            s = out if isinstance(out, str) else out.decode("utf-8", errors="replace")
            try:
                print(s[:500])
            except UnicodeEncodeError:
                print(s[:500].encode("ascii", errors="replace").decode("ascii"))
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
