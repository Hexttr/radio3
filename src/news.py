"""Fetch news from RSS (free, no API key)."""
import feedparser
from datetime import datetime

from . import lang


def fetch_news(limit: int = 5, language: str = "ru") -> str:
    """
    Collect latest news from RSS.
    Returns text for TTS (brief bulletin).
    """
    feeds = lang.RSS_BY_LANG.get(language, lang.RSS_BY_LANG["en"])
    items = []
    seen_titles = set()

    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title = getattr(entry, "title", "") or ""
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                items.append(title)
                if len(items) >= limit:
                    break
        except Exception:
            continue
        if len(items) >= limit:
            break

    if not items:
        return lang.get(language, "news_unavailable")

    now = datetime.now()
    date_str_val = lang.date_str(language, now.day, now.month)
    intro = lang.get(language, "news_intro", date=date_str_val)
    lines = [intro] + [f"{i + 1}. {t}" for i, t in enumerate(items[:limit])]
    return " ".join(lines)
