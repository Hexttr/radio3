#!/usr/bin/env python
"""Проверка Icecast и broadcaster на сервере."""
import os
import sys
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.environ["DEPLOY_HOST"], username="root", password=os.environ["DEPLOY_PASS"])

for label, cmd in [
    ("Icecast GET /live", "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/live"),
    ("broadcaster.log", "tail -80 /opt/ai-radio/broadcaster.log 2>/dev/null || echo 'no log'"),
    ("journalctl broadcaster", "journalctl -u ai-radio-broadcaster -n 25 --no-pager 2>/dev/null"),
    ("Icecast status", "curl -s http://127.0.0.1:8000/status-json.xsl 2>/dev/null | head -20"),
]:
    sys.stdout.write("\n--- " + label + " ---\n")
    _, o, _ = c.exec_command(cmd)
    r = o.read().decode("utf-8", errors="replace")
    sys.stdout.write(r[:1200] + "\n" if len(r) > 1200 else r + "\n")

c.close()
