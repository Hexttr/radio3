#!/usr/bin/env python
"""Проверка Icecast и broadcaster на сервере."""
import os
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.environ["DEPLOY_HOST"], username="root", password=os.environ["DEPLOY_PASS"])

for label, cmd in [
    ("Icecast GET /live", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/live"),
    ("Broadcaster log", "journalctl -u ai-radio-broadcaster -n 20 --no-pager 2>/dev/null"),
    ("Icecast mounts", "curl -s http://127.0.0.1:8000/status-json.xsl 2>/dev/null | head -30"),
]:
    print("\n---", label, "---")
    _, o, _ = c.exec_command(cmd)
    r = o.read().decode("utf-8", errors="replace")
    print(r[:600] if len(r) > 600 else r)

c.close()
