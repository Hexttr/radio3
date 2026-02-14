#!/usr/bin/env python
"""
Деплой AI Radio на Ubuntu-сервер через SSH (paramiko).
Установка: pip install paramiko
Запуск: set DEPLOY_HOST=... DEPLOY_USER=... DEPLOY_PASS=... && python deploy/deploy.py
"""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("Установите paramiko: pip install paramiko")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/Hexttr/radio3.git"
APP_DIR = "/opt/ai-radio"


def get_ssh():
    host = os.environ.get("DEPLOY_HOST")
    user = os.environ.get("DEPLOY_USER", "root")
    password = os.environ.get("DEPLOY_PASS")
    if not host:
        print("Укажите DEPLOY_HOST (например: 195.133.63.34)")
        sys.exit(1)
    return host, user, password


def run_commands(client, cmds, desc=""):
    for cmd in cmds:
        print(f"$ {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        stdout.read()
        stderr.read()
        code = stdout.channel.recv_exit_status()
        if code != 0:
            print(f"Ошибка при выполнении: {cmd}", file=sys.stderr)
            return False
    return True


def main():
    host, user, password = get_ssh()
    if not password:
        print("Укажите DEPLOY_PASS")
        sys.exit(1)

    print(f"Подключение к {user}@{host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)

    try:
        # 1. Обновление и установка зависимостей
        run_commands(client, [
            "apt-get update -qq",
            "apt-get install -y -qq python3 python3-pip python3-venv ffmpeg git",
        ], "Системные пакеты")

        # 2. Клонирование/обновление репо
        run_commands(client, [
            f"(test -d {APP_DIR} && cd {APP_DIR} && git fetch origin Ubuntu && git checkout Ubuntu && git pull) "
            f"|| (git clone -b Ubuntu {REPO_URL} {APP_DIR})",
        ], "Репозиторий")

        # 3. Python-зависимости
        run_commands(client, [
            f"cd {APP_DIR} && python3 -m venv venv",
            f"cd {APP_DIR} && ./venv/bin/pip install -q -r requirements.txt gunicorn",
        ], "Python")

        # 4. Icecast2 (пароль source = hackme, как в config.yaml)
        run_commands(client, [
            "apt-get install -y -qq icecast2",
            "getent group icecast2 >/dev/null || groupadd --system icecast2",
            "getent passwd icecast2 >/dev/null || useradd --system -g icecast2 -d /var/log/icecast2 -s /usr/sbin/nologin icecast2",
            "mkdir -p /var/log/icecast2 && chown icecast2:icecast2 /var/log/icecast2",
            "sed -i 's/<source-password>.*<\\/source-password>/<source-password>hackme<\\/source-password>/' /etc/icecast2/icecast.xml 2>/dev/null || true",
            "sed -i 's/<source-timeout>.*<\\/source-timeout>/<source-timeout>120<\\/source-timeout>/' /etc/icecast2/icecast.xml 2>/dev/null || true",
            "sed -i 's/<queue-size>.*<\\/queue-size>/<queue-size>1048576<\\/queue-size>/' /etc/icecast2/icecast.xml 2>/dev/null || true",
            "systemctl enable icecast2",
            "systemctl start icecast2",
        ], "Icecast2")

        # 5. Директории и .env
        run_commands(client, [
            f"mkdir -p {APP_DIR}/music {APP_DIR}/cache {APP_DIR}/podcasts",
        ])

        env_local = ROOT / ".env"
        if env_local.exists():
            sftp = client.open_sftp()
            sftp.put(str(env_local), f"{APP_DIR}/.env")
            sftp.close()
            print("  .env copied from local machine")
        else:
            run_commands(client, [
                f"touch {APP_DIR}/.env",
            ])
            print("  Create .env on server with GROQ_API_KEY")

        # 6. Systemd — Flask + Broadcaster
        svc = f"""[Unit]
Description=AI Radio
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}
Environment="PATH={APP_DIR}/venv/bin:/usr/bin:/bin"
EnvironmentFile={APP_DIR}/.env
ExecStart={APP_DIR}/venv/bin/gunicorn -w 1 -b 127.0.0.1:5000 --timeout 300 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        broadcaster_svc = f"""[Unit]
Description=AI Radio Broadcaster (Icecast source)
After=network.target icecast2.service

[Service]
Type=simple
User=root
WorkingDirectory={APP_DIR}
Environment="PATH={APP_DIR}/venv/bin:/usr/bin:/bin"
EnvironmentFile={APP_DIR}/.env
ExecStart={APP_DIR}/venv/bin/python run_broadcaster.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        sftp = client.open_sftp()
        with sftp.open(f"{APP_DIR}/ai-radio.service", "w") as f:
            f.write(svc)
        with sftp.open(f"{APP_DIR}/ai-radio-broadcaster.service", "w") as f:
            f.write(broadcaster_svc)
        sftp.close()

        run_commands(client, [
            f"cp {APP_DIR}/ai-radio.service /etc/systemd/system/",
            f"cp {APP_DIR}/ai-radio-broadcaster.service /etc/systemd/system/",
            "systemctl daemon-reload",
            f"systemctl enable ai-radio ai-radio-broadcaster",
            "systemctl restart icecast2",
            f"systemctl restart ai-radio ai-radio-broadcaster",
        ], "Systemd")

        # 7. Nginx + HTTPS (домен navoradio.com)
        domain = os.environ.get("DEPLOY_DOMAIN", "navoradio.com")
        email = os.environ.get("DEPLOY_EMAIL", "admin@navoradio.com")

        run_commands(client, [
            "apt-get install -y -qq nginx certbot python3-certbot-nginx",
        ], "Nginx + Certbot")

        nginx_conf = f"""# NAVO RADIO — {domain} + Icecast stream
server {{
    listen 80;
    server_name {domain} www.{domain};
    location /live {{
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_connect_timeout 10s;
    }}
    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }}
}}
"""
        sftp = client.open_sftp()
        with sftp.open(f"/etc/nginx/sites-available/navoradio", "w") as f:
            f.write(nginx_conf)
        sftp.close()

        run_commands(client, [
            "rm -f /etc/nginx/sites-enabled/ai-radio",
            "ln -sf /etc/nginx/sites-available/navoradio /etc/nginx/sites-enabled/",
            "nginx -t && systemctl reload nginx",
        ], "Nginx config")

        run_commands(client, [
            f"certbot --nginx -d {domain} -d www.{domain} --non-interactive --agree-tos -m {email} 2>/dev/null || true",
        ], "SSL certificate")

        # 7. Firewall (ufw)
        run_commands(client, [
            "ufw allow 80/tcp 2>/dev/null || true",
            "ufw allow 443/tcp 2>/dev/null || true",
            "ufw --force enable 2>/dev/null || true",
        ])

        print("\n[OK] Deploy complete.")
        print(f"  https://{domain}")
        print(f"  Add mp3 to {APP_DIR}/music/ on server")

    finally:
        client.close()


if __name__ == "__main__":
    main()
