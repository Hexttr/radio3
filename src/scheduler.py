"""
Планировщик сегментов: музыка, комментарии диджея, новости, погода.
Генерирует сегменты заранее, чтобы не было пауз.
"""
import random
import threading
import time
from pathlib import Path
from queue import Queue, Empty

from .track_parser import parse_track
from .tts import generate_tts
from .ai_dj import get_dj_comment, get_transition
from .news import fetch_news
from .weather import fetch_weather


class Scheduler:
    def __init__(
        self,
        music_dir: Path,
        cache_dir: Path,
        config: dict,
    ):
        self.music_dir = Path(music_dir)
        self.cache_dir = Path(cache_dir)
        self.config = config
        self.segment_queue: Queue[Path] = Queue()
        self._tracks: list[Path] = []
        self._track_index = 0
        self._track_lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._start_time = time.monotonic()
        self._last_news_at: float = -999
        self._last_weather_at: float = -999

        region = config.get("region", {})
        self.city = region.get("city", "London")
        self.lat = region.get("latitude", 51.5074)
        self.lon = region.get("longitude", -0.1278)
        self.timezone = region.get("timezone", "Europe/London")
        intervals = config.get("intervals", {})
        self.news_minutes = intervals.get("news_minutes", 180)
        self.weather_minutes = intervals.get("weather_minutes", 240)
        tts_cfg = config.get("tts", {})
        self.voice = tts_cfg.get("voice", "ru-RU-SvetlanaNeural")
        self.rate = tts_cfg.get("rate", "+0%")
        self.volume = tts_cfg.get("volume", "+0%")

    def _load_tracks(self) -> list[Path]:
        tracks = []
        for ext in ("*.mp3", "*.MP3"):
            tracks.extend(self.music_dir.glob(ext))
        seen = set()
        unique = []
        for p in sorted(tracks):
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                unique.append(p.resolve())
        return unique

    def _get_next_track(self) -> Path | None:
        with self._track_lock:
            if not self._tracks:
                self._tracks = self._load_tracks()
                if not self._tracks:
                    return None
                random.shuffle(self._tracks)
                self._track_index = 0

            track = self._tracks[self._track_index]
            self._track_index = (self._track_index + 1) % len(self._tracks)
            if self._track_index == 0:
                random.shuffle(self._tracks)
            return track

    def _minutes_elapsed(self) -> float:
        return (time.monotonic() - self._start_time) / 60

    def _should_play_news(self) -> bool:
        m = self._minutes_elapsed()
        if m < 1:
            return False
        slot = int(m // self.news_minutes) * self.news_minutes
        if slot <= self._last_news_at:
            return False
        # Окно 15 мин в начале каждого слота — успеем попасть при любом темпе очереди
        if m - slot < 15:
            self._last_news_at = slot
            return True
        return False

    def _should_play_weather(self) -> bool:
        m = self._minutes_elapsed()
        if m < 1:
            return False
        slot = int(m // self.weather_minutes) * self.weather_minutes
        if slot <= self._last_weather_at:
            return False
        if m - slot < 15:
            self._last_weather_at = slot
            return True
        return False

    def _add_tts(self, text: str, subdir: str = "dj") -> Path | None:
        cache_sub = self.cache_dir / subdir
        try:
            return generate_tts(text, cache_sub, self.voice, self.rate, self.volume)
        except Exception:
            return None

    def _generate_next_segments(self) -> None:
        """Добавляет в очередь: [dj_comment, transition, next_segment]."""
        # Определяем, что идёт дальше
        play_news = self._should_play_news()
        play_weather = self._should_play_weather()

        if play_news:
            trans = get_transition("", "", "news")
            trans_path = self._add_tts(trans, "dj")
            if trans_path:
                self.segment_queue.put(trans_path)
            text = fetch_news()
            path = self._add_tts(text, "news")
            if path:
                self.segment_queue.put(path)
            return

        if play_weather:
            trans = get_transition("", "", "weather")
            trans_path = self._add_tts(trans, "dj")
            if trans_path:
                self.segment_queue.put(trans_path)
            text = fetch_weather(self.lat, self.lon, self.city, self.timezone)
            path = self._add_tts(text, "weather")
            if path:
                self.segment_queue.put(path)
            return

        # Обычный трек: [комментарий о прошлом] → [переход] → [трек]
        next_track = self._get_next_track()
        if not next_track:
            return

        artist, title = parse_track(next_track)

        if hasattr(self, "_last_artist") and hasattr(self, "_last_title"):
            comment = get_dj_comment(self._last_artist, self._last_title, self.city)
            comment_path = self._add_tts(comment, "dj")
            if comment_path:
                self.segment_queue.put(comment_path)

        self._last_artist, self._last_title = artist, title
        trans = get_transition(artist, title, "track")
        trans_path = self._add_tts(trans, "dj")
        if trans_path:
            self.segment_queue.put(trans_path)
        self.segment_queue.put(next_track)

    def _run_generator(self) -> None:
        """Фоновая нить: держит очередь заполненной."""
        while self._running:
            try:
                # Держим 3+ сегмента впереди
                while self._running and self.segment_queue.qsize() < 3:
                    self._generate_next_segments()
            except Exception:
                pass
            time.sleep(2)

    def start(self) -> None:
        self._running = True
        self._tracks = self._load_tracks()
        if self._tracks:
            random.shuffle(self._tracks)
            first = self._get_next_track()
            if first:
                self.segment_queue.put(first)
                self._last_artist, self._last_title = parse_track(first)
        else:
            self._last_artist, self._last_title = "Radio", "No tracks in music folder"
            fallback = self._add_tts(
                "Welcome to AI Radio. Add mp3 files to the music folder and restart.",
                "system",
            )
            if fallback:
                self.segment_queue.put(fallback)

        self._thread = threading.Thread(target=self._run_generator, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_segment(self, timeout: float = 30.0) -> Path | None:
        try:
            return self.segment_queue.get(timeout=timeout)
        except Empty:
            return None
