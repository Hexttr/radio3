"""
Планировщик сегментов: музыка, диджей, новости, погода, подкасты.
Расписание по часам МСК. Между слотыми — треки + реплики диджея.
"""
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

from .track_parser import parse_track
from .tts import generate_tts
from .ai_dj import get_dj_comment, get_transition
from .news import fetch_news
from .weather import fetch_weather
from . import lang

MSK = "Europe/Moscow"


def _msk_hour() -> int:
    """Текущий час по Москве."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(MSK)).hour
    except ImportError:
        return datetime.utcnow().hour + 3  # грубо МСК


def _msk_date_str() -> str:
    """Дата по МСК для cache salt."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(MSK)).strftime("%Y-%m-%d-%H")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d-%H")


class Scheduler:
    def __init__(
        self,
        music_dir: Path,
        cache_dir: Path,
        config: dict,
        podcasts_dir: Path | None = None,
    ):
        self.music_dir = Path(music_dir)
        self.cache_dir = Path(cache_dir)
        self.podcasts_dir = Path(podcasts_dir) if podcasts_dir else Path(config.get("podcasts_dir", "podcasts"))
        self.config = config
        self.segment_queue: Queue[Path] = Queue()
        self._tracks: list[Path] = []
        self._track_index = 0
        self._track_lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_news_hour: int = -1
        self._last_weather_hour: int = -1
        self._last_podcast_hour: int = -1
        self._podcast_index: int = 0

        region = config.get("region", {})
        self.city = region.get("city", "Dushanbe")
        self.lat = region.get("latitude", 38.56)
        self.lon = region.get("longitude", 68.78)
        self.timezone = region.get("timezone", "Asia/Dushanbe")
        sched = config.get("schedule", {})
        self.news_hours = set(sched.get("news_hours", [9, 12, 15, 18, 21]))
        self.weather_hours = set(sched.get("weather_hours", [7, 10, 13, 16, 19]))
        self.podcast_hours = set(sched.get("podcast_hours", [11, 14, 17, 20]))
        self.news_items = sched.get("news_items", 8)
        tts_cfg = config.get("tts", {})
        self.tts_config = dict(tts_cfg)
        self.language = config.get("language", "ru")

    def _load_tracks(self) -> list[Path]:
        """Горячая замена: каждый раз читаем с диска."""
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
                self._tracks = self._load_tracks()
                if self._tracks:
                    random.shuffle(self._tracks)
                    self._track_index = 0
            return track

    def _load_podcasts(self) -> list[Path]:
        """Подкасты из папки — каждый раз свежий список."""
        items = []
        if not self.podcasts_dir.exists():
            return items
        for ext in ("*.mp3", "*.MP3"):
            items.extend(self.podcasts_dir.glob(ext))
        return sorted(p.resolve() for p in items)

    def _get_next_podcast(self) -> Path | None:
        pods = self._load_podcasts()
        if not pods:
            return None
        idx = self._podcast_index % len(pods)
        self._podcast_index += 1
        return pods[idx]

    def _should_play_news(self) -> bool:
        h = _msk_hour()
        if h not in self.news_hours:
            return False
        if h == self._last_news_hour:
            return False
        self._last_news_hour = h
        return True

    def _should_play_weather(self) -> bool:
        h = _msk_hour()
        if h not in self.weather_hours:
            return False
        if h == self._last_weather_hour:
            return False
        self._last_weather_hour = h
        return True

    def _should_play_podcast(self) -> bool:
        h = _msk_hour()
        if h not in self.podcast_hours:
            return False
        if h == self._last_podcast_hour:
            return False
        self._last_podcast_hour = h
        return True

    def _add_tts(self, text: str, subdir: str = "dj", cache_salt: str = "") -> Path | None:
        cache_sub = self.cache_dir / subdir
        try:
            return generate_tts(text, cache_sub, self.tts_config, cache_salt)
        except Exception as e:
            import sys
            print(f"TTS failed ({subdir}): {e}", file=sys.stderr)
            return None

    def _generate_next_segments(self) -> None:
        """Добавляет в очередь: transition + segment (news/weather/podcast/track)."""
        play_news = self._should_play_news()
        play_weather = self._should_play_weather()
        play_podcast = self._should_play_podcast()

        if play_news:
            trans = get_transition("", "", "news", self.language)
            trans_path = self._add_tts(trans, "dj")
            if trans_path:
                self.segment_queue.put(trans_path)
            text = fetch_news(limit=self.news_items, language=self.language)
            path = self._add_tts(text, "news", _msk_date_str())
            if path:
                self.segment_queue.put(path)
            return

        if play_weather:
            trans = get_transition("", "", "weather", self.language)
            trans_path = self._add_tts(trans, "dj")
            if trans_path:
                self.segment_queue.put(trans_path)
            text = fetch_weather(self.lat, self.lon, self.city, self.timezone, language=self.language)
            path = self._add_tts(text, "weather")
            if path:
                self.segment_queue.put(path)
            return

        if play_podcast:
            trans = get_transition("", "", "podcast", self.language)
            trans_path = self._add_tts(trans, "dj")
            if trans_path:
                self.segment_queue.put(trans_path)
            pod = self._get_next_podcast()
            if pod:
                self.segment_queue.put(pod)
            return

        # Обычный трек: [комментарий о прошлом] → [переход] → [трек]
        next_track = self._get_next_track()
        if not next_track:
            return

        artist, title = parse_track(next_track)

        if hasattr(self, "_last_artist") and hasattr(self, "_last_title"):
            comment = get_dj_comment(self._last_artist, self._last_title, self.city, self.language)
            comment_path = self._add_tts(comment, "dj")
            if comment_path:
                self.segment_queue.put(comment_path)
            else:
                import sys
                print(f"DJ SKIP comment (TTS failed): {self._last_artist} — {self._last_title}", file=sys.stderr)

        self._last_artist, self._last_title = artist, title
        trans = get_transition(artist, title, "track", self.language)
        trans_path = self._add_tts(trans, "dj")
        if trans_path:
            self.segment_queue.put(trans_path)
        else:
            import sys
            print(f"DJ SKIP transition (TTS failed): {artist} — {title}", file=sys.stderr)
        self.segment_queue.put(next_track)

    def _run_generator(self) -> None:
        while self._running:
            try:
                while self._running and self.segment_queue.qsize() < 5:
                    self._generate_next_segments()
            except Exception:
                pass
            time.sleep(1)

    def start(self) -> None:
        self._running = True
        self._tracks = self._load_tracks()
        self.podcasts_dir.mkdir(exist_ok=True)
        if self._tracks:
            random.shuffle(self._tracks)
            first = self._get_next_track()
            if first:
                self.segment_queue.put(first)
                self._last_artist, self._last_title = parse_track(first)
        else:
            self._last_artist, self._last_title = "Radio", "No tracks in music folder"
            fallback = self._add_tts(lang.get(self.language, "welcome"), "system")
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

    def get_segment_nowait(self) -> Path | None:
        """Неблокирующий запрос сегмента — для stream, чтобы не останавливать выдачу байтов."""
        try:
            return self.segment_queue.get_nowait()
        except Empty:
            return None
