#!/usr/bin/env python
"""
Запуск broadcaster — стримит в Icecast.
Отдельный процесс: python run_broadcaster.py
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import yaml

from src.scheduler import Scheduler
from src.broadcaster import run_broadcaster

ROOT_DIR = Path(__file__).resolve().parent


def load_config() -> dict:
    path = ROOT_DIR / "config.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    config = load_config()
    music_dir = ROOT_DIR / config.get("music_dir", "music")
    cache_dir = ROOT_DIR / config.get("cache_dir", "cache")
    podcasts_dir = ROOT_DIR / config.get("podcasts_dir", "podcasts")
    music_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)
    podcasts_dir.mkdir(exist_ok=True)

    scheduler = Scheduler(music_dir, cache_dir, config, podcasts_dir)
    scheduler.start()

    ice = config.get("icecast", {})
    url = ice.get("url", "http://127.0.0.1:8000")
    password = ice.get("password", "hackme")
    mount = ice.get("mount", "/live")
    name = ice.get("name", "NAVO RADIO")

    print(f"Broadcaster → {url}{mount} ({name})")
    run_broadcaster(scheduler, url, password, mount, name)


if __name__ == "__main__":
    main()
