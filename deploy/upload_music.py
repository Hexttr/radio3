#!/usr/bin/env python
"""Upload music from local music/ to server via SFTP."""
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
MUSIC_LOCAL = ROOT / "music"
REMOTE_DIR = "/opt/ai-radio/music"


def main():
    host = os.environ.get("DEPLOY_HOST")
    user = os.environ.get("DEPLOY_USER", "root")
    password = os.environ.get("DEPLOY_PASS")
    if not host or not password:
        print("Set DEPLOY_HOST, DEPLOY_PASS")
        sys.exit(1)
    if not MUSIC_LOCAL.exists():
        print("No local music/ folder")
        sys.exit(1)

    files = list(MUSIC_LOCAL.glob("*.mp3")) + list(MUSIC_LOCAL.glob("*.MP3"))
    if not files:
        print("No mp3 files in music/")
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)
    sftp = client.open_sftp()
    sftp.chdir(REMOTE_DIR)

    for f in files:
        print(f"Uploading {f.name}...")
        sftp.put(str(f), f.name)
    sftp.close()
    client.close()
    print(f"[OK] Uploaded {len(files)} files")


if __name__ == "__main__":
    main()
