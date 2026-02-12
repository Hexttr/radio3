"""Fetch news from RSS (free, no API key)."""
import re
import feedparser
from datetime import datetime

from . import lang


def _strip_html(text: str) -> str:
    """Удаление HTML-тегов и лишних пробелов."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_summary(entry) -> str:
    """Извлечь summary или description, очистить от HTML, обрезать."""
    raw = (
        getattr(entry, "summary", "") or
        getattr(entry, "description", "") or
        ""
    )
    text = _strip_html(raw)
    # Ограничим длину: ~100 слов или 600 символов
    if len(text) > 600:
        text = text[:597].rsplit(maxsplit=1)[0] + "..."
    return text


def fetch_news(limit: int = 5, language: str = "ru") -> str:
    """
    Собирает последние новости из RSS.
    Для каждой новости: заголовок + краткое содержание (если есть).
    Возвращает текст для TTS.
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
                summary = _get_summary(entry)
                if summary:
                    items.append(f"{title}. {summary}")
                else:
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
