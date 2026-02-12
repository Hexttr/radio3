"""
Broadcaster — читает сегменты из Scheduler и стримит в Icecast.
Icecast не поддерживает chunked encoding, поэтому используем HTTP/1.0.
"""
import base64
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


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
    Стримит аудио в Icecast. HTTP/1.0 без chunked (Icecast его не поддерживает).
    """
    parsed = urlparse(icecast_url.rstrip("/"))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    auth = base64.b64encode(f"source:{password}".encode()).decode("ascii")

    gen = stream_generator(scheduler)
    sock = None
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((host, port))

            path = mount or "/"
            req = (
                f"PUT {path} HTTP/1.0\r\n"
                f"Host: {host}:{port}\r\n"
                f"Authorization: Basic {auth}\r\n"
                f"Content-Type: audio/mpeg\r\n"
                f"Ice-Public: 1\r\n"
                f"Ice-Name: {name}\r\n"
                f"Ice-Description: NAVO RADIO 24/7\r\n"
                "\r\n"
            )
            sock.sendall(req.encode("ascii"))

            # Прочитать ответ Icecast (100/200) перед отправкой тела
            sock.settimeout(5)
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += sock.recv(4096)
                if not resp:
                    raise ConnectionError("Icecast closed connection")
            first_line = resp.split(b"\r\n")[0].decode("ascii", errors="replace")
            if "200" not in first_line and "100" not in first_line:
                raise ConnectionError(f"Icecast rejected: {first_line}")

            print("Connected to Icecast", file=sys.stderr)
            sock.settimeout(60)
            sent = 0
            for chunk in gen:
                sock.sendall(chunk)
                sent += len(chunk)
                if sent >= 65536:
                    sock.settimeout(60)
                    sent = 0

        except Exception as e:
            print(f"Broadcaster error: {e}", file=sys.stderr)
        finally:
            try:
                if sock:
                    sock.close()
            except Exception:
                pass
        time.sleep(5)
