#!/usr/bin/env python
"""Проверка и исправление Icecast на сервере."""
import os
import sys
try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(os.environ["DEPLOY_HOST"], username=os.environ.get("DEPLOY_USER","root"), password=os.environ["DEPLOY_PASS"])

    for cmd in [
        "journalctl -u icecast2 -n 30 --no-pager",
        "test -f /etc/icecast2/icecast.xml && head -50 /etc/icecast2/icecast.xml",
    ]:
        print(f"\n$ {cmd}")
        _, out, _ = c.exec_command(cmd)
        print(out.read().decode("utf-8", errors="replace"))

    c.close()

if __name__ == "__main__":
    main()
