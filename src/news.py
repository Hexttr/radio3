"""Загрузка новостей из RSS (бесплатно, без API-ключа)."""
import feedparser
from datetime import datetime

# RSS-ленты российских СМИ
RSS_FEEDS = [
    "https://ria.ru/export/rss2/archive/index.xml",  # РИА Новости
    "https://lenta.ru/rss/news",
    "https://www.vedomosti.ru/rss/news",
    "https://tass.ru/rss/v2.xml",
]


def fetch_news(limit: int = 5) -> str:
    """
    Собирает последние новости из RSS.
    Возвращает текст для озвучки (краткий выпуск).
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
        return "К сожалению, новости временно недоступны. Возвращаемся к музыке."

    intro = f"Краткий выпуск новостей. {datetime.now().strftime('%d %B')}."
    # Простое склонение месяца можно добавить при необходимости
    lines = [intro] + [f"{i + 1}. {t}" for i, t in enumerate(items[:limit])]
    return " ".join(lines)
