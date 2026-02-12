"""
Broadcaster — читает сегменты из Scheduler и стримит в Icecast.
Единый эфир для всех слушателей.
"""
import base64
import sys
import time
from pathlib import Path

import requests


def stream_generator(scheduler, chunk_size: int = 8192):
    """Бесконечный генератор: читает сегменты и отдаёт байты."""
    while True:
        seg = scheduler.get_segment()
        if seg is None:
            time.sleep(1)
            continue
        path = Path(seg)
        if not path.exists() or path.stat().st_size == 0:
            continue
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception:
            continue


def run_broadcaster(scheduler, icecast_url: str, password: str, mount: str = "/live", name: str = "NAVO RADIO"):
    """
    Стримит аудио в Icecast. Блокирующий вызов.
    icecast_url: http://127.0.0.1:8000
    password: source password из icecast.xml
    """
    url = f"{icecast_url.rstrip('/')}{mount}"
    auth = base64.b64encode(f"source:{password}".encode()).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "audio/mpeg",
        "Ice-Public": "1",
        "Ice-Name": name,
        "Ice-Description": "NAVO RADIO 24/7 AI Radio",
    }
    gen = stream_generator(scheduler)
    while True:
        try:
            r = requests.put(url, data=gen, headers=headers, timeout=None, stream=True)
            if r.status_code in (200, 201):
                print("Connected to Icecast", file=sys.stderr)
            else:
                print(f"Icecast rejected: {r.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"Broadcaster error: {e}", file=sys.stderr)
        time.sleep(5)
