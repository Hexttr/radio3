"""
AI Radio — точка входа.
Веб-сервер: заходи на страницу и слушай поток.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import yaml

from flask import Flask, Response, send_from_directory

from .scheduler import Scheduler

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent


def load_config() -> dict:
    path = ROOT_DIR / "config.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def create_app() -> Flask:
    app = Flask(__name__, static_folder=ROOT_DIR / "static")
    config = load_config()

    music_dir = ROOT_DIR / config.get("music_dir", "music")
    cache_dir = ROOT_DIR / config.get("cache_dir", "cache")
    music_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    scheduler = Scheduler(music_dir, cache_dir, config)
    scheduler.start()

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/next")
    def next_segment():
        """Один сегмент — полный mp3-файл."""
        segment = scheduler.get_segment()
        if segment is None:
            return "", 204
        path = Path(segment)
        if not path.exists():
            return "", 204
        data = path.read_bytes()
        return Response(
            data,
            mimetype="audio/mpeg",
            headers={
                "Cache-Control": "no-store",
                "Content-Length": str(len(data)),
            },
        )

    return app


def main():
    config = load_config()
    server = config.get("server", {})
    host = server.get("host", "0.0.0.0")
    port = server.get("port", 5000)

    app = create_app()
    print(f"AI Radio: http://127.0.0.1:{port}")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
