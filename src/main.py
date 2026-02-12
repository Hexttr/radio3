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
from .track_parser import parse_track

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

    # Удалить битые 0-byte файлы из кэша
    for p in cache_dir.rglob("*.mp3"):
        if p.stat().st_size == 0:
            p.unlink()

    scheduler = Scheduler(music_dir, cache_dir, config)
    scheduler.start()

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    @app.route("/api/next")
    @app.route("/next")
    def next_segment():
        """Один сегмент — полный mp3-файл."""
        segment = scheduler.get_segment()
        if segment is None:
            return "", 204
        path = Path(segment)
        if not path.exists() or path.stat().st_size == 0:
            return "", 204
        data = path.read_bytes()

        # Метаданные для фронта: X-Segment-Type, X-Artist, X-Title
        parent = path.parent.name
        if parent == "news":
            seg_type, artist, title = "news", "", ""
        elif parent == "weather":
            seg_type, artist, title = "weather", "", ""
        elif parent in ("dj", "system"):
            seg_type, artist, title = "dj", "", ""
        else:
            seg_type = "track"
            artist, title = parse_track(path)

        headers = {
            "Cache-Control": "no-store",
            "Content-Length": str(len(data)),
            "X-Segment-Type": seg_type,
            "X-Artist": artist,
            "X-Title": title,
        }
        return Response(data, mimetype="audio/mpeg", headers=headers)

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
