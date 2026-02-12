"""Fetch news from RSS (free, no API key)."""
import feedparser
from datetime import datetime

RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.theguardian.com/world/rss",
]


def fetch_news(limit: int = 5) -> str:
    """
    Collect latest news from RSS.
    Returns text for TTS (brief bulletin).
    """
    items = []
    seen_titles = set()

    for url in RSS_FEEDS:
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
        return "News is temporarily unavailable. Back to the music."

    intro = f"News bulletin. {datetime.now().strftime('%d %B')}."
    lines = [intro] + [f"{i + 1}. {t}" for i, t in enumerate(items[:limit])]
    return " ".join(lines)
