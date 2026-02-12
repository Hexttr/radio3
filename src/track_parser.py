"""Парсинг исполнителя и названия трека из файла."""
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def parse_track(filepath: Path) -> tuple[str, str]:
    """
    Извлекает artist и title из mp3.
    Сначала пробует ID3-теги, затем парсит имя файла (Artist - Title.mp3).
    """
    artist, title = "", ""

    if MUTAGEN_AVAILABLE:
        try:
            audio = MP3(filepath, ID3=ID3)
            if audio.tags:
                artist = str(audio.tags.get("TPE1", audio.tags.get("TPE2", "")) or "").strip()
                title = str(audio.tags.get("TIT2", "") or "").strip()
        except Exception:
            pass

    if not artist or not title:
        # Парсим из имени файла: "Artist - Title.mp3" или "Artist-Title.mp3"
        stem = filepath.stem
        for sep in (" - ", " – ", " — ", "-", "–", "—"):
            if sep in stem:
                parts = stem.split(sep, 1)
                if len(parts) == 2:
                    artist, title = parts[0].strip(), parts[1].strip()
                    break
        if not artist:
            artist = "Unknown Artist"
        if not title:
            title = stem or "Untitled"

    return (artist or "Unknown Artist", title or "Untitled")
