#!/usr/bin/env python
"""Создаёт cache/dj/fallback.mp3 для использования при сбое TTS. Запуск из корня: python scripts/create_fallback_dj.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import yaml
from src.tts import generate_tts
from src import lang

def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    tts = cfg.get("tts", {})
    lang_code = cfg.get("language", "ru")
    dj_dir = ROOT / "cache" / "dj"
    dj_dir.mkdir(parents=True, exist_ok=True)
    text = lang.get(lang_code, "fallback_dj")
    try:
        p = generate_tts(text, dj_dir, tts, "fallback")
        print(f"OK: {p}")
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
