"""
AI Radio — точка входа.
Веб-сервер: заходи на страницу и слушай поток.
"""
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import yaml

from flask import Flask, Response, jsonify, send_from_directory

from .scheduler import MSK, Scheduler
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
        r = send_from_directory(app.static_folder, "index.html")
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        return r

    @app.route("/live")
    def live_proxy():
        """Прокси к Icecast (для локальной разработки без nginx)."""
        ice = config.get("icecast", {})
        url = f"{ice.get('url', 'http://127.0.0.1:8000').rstrip('/')}{ice.get('mount', '/live')}"
        try:
            import requests as req
            r = req.get(url, stream=True, timeout=5)
            r.raise_for_status()

            def gen():
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

            return Response(gen(), mimetype="audio/mpeg", direct_passthrough=True)
        except Exception:
            return "", 502

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    @app.route("/api/ping")
    def api_ping():
        return "ok", 200

    @app.route("/api/log")
    def api_log():
        """Последние 100 строк broadcaster.log для отладки."""
        log_path = ROOT_DIR / "broadcaster.log"
        if not log_path.exists():
            return "No log yet", 404
        lines = log_path.read_text(encoding="utf-8", errors="replace").strip().split("\n")
        return Response("\n".join(lines[-100:]), mimetype="text/plain; charset=utf-8")

    @app.route("/api/status")
    def api_status():
        """Время сервера и МСК для отладки расписания."""
        from zoneinfo import ZoneInfo
        from datetime import datetime
        now = datetime.now()
        msk_now = datetime.now(ZoneInfo(MSK))
        return jsonify({
            "server_utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "server_local": now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "msk": msk_now.strftime("%Y-%m-%d %H:%M:%S MSK"),
            "msk_hour": msk_now.hour,
            "next_news": sorted(h for h in [9, 12, 15, 18, 21] if h > msk_now.hour or msk_now.hour >= 21)[:1] or [9],
            "next_weather": sorted(h for h in [7, 10, 13, 16, 19] if h > msk_now.hour or msk_now.hour >= 19)[:1] or [7],
            "next_podcast": sorted(h for h in [11, 14, 17, 20] if h > msk_now.hour or msk_now.hour >= 20)[:1] or [11],
        })

    @app.route("/api/now")
    def api_now():
        """Сегмент в эфире с учётом буфера плеера (~15 сек)."""
        import time as time_module
        now_file = cache_dir / ".now_playing.json"
        if now_file.exists():
            try:
                data = json.loads(now_file.read_text(encoding="utf-8"))
                history = data.get("history", [])
                if history:
                    now_ts = time_module.time()
                    delay = 20
                    target_ts = now_ts - delay
                    best = None
                    for e in history:
                        if e["t"] <= target_ts:
                            best = e
                        else:
                            break
                    if best is None:
                        best = history[0]
                    return jsonify({
                        "artist": best.get("artist", ""),
                        "title": best.get("title", ""),
                        "type": best.get("type", ""),
                    })
            except Exception:
                pass
        segment = scheduler.peek_next_segment()
        if segment is None:
            return jsonify({"artist": "", "title": "", "type": ""})
        path = Path(segment)
        parent = path.parent.name
        if parent == "news":
            return jsonify({"artist": "", "title": "", "type": "news"})
        if parent == "weather":
            return jsonify({"artist": "", "title": "", "type": "weather"})
        if parent in ("dj", "system"):
            return jsonify({"artist": "", "title": "", "type": "dj"})
        artist, title = parse_track(path)
        return jsonify({"artist": artist, "title": title, "type": "track"})

    @app.route("/api/next")
    @app.route("/next")
    def next_segment():
        """Превью следующего сегмента (peek) — не забирает из очереди эфира."""
        segment = scheduler.peek_next_segment()
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
