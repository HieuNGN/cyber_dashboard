import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, List

from fetchers import CISAKEVFetcher, Fetcher, RSSFetcher
from ingestion import Ingestion
from repositories import SQLiteArticleRepository


# ponytail: table replaces 8 if-blocks; same names/URLs/order as before.
SOURCES = [
    ("hackernews", "rss", "The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("bleepingcomputer", "rss", "BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("krebs", "rss", "Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("cisa_kev", "kev", "", ""),  # ponytail: KEV fetcher hardcodes name/url
    ("tomshardware", "rss", "Tom's Hardware", "https://www.tomshardware.com/feeds.xml"),
    ("servethehome", "rss", "ServeTheHome", "https://www.servethehome.com/feed/"),
    ("wccftech", "rss", "Wccftech", "https://wccftech.com/feed/"),
    ("theregister", "rss", "The Register", "https://www.theregister.com/headlines.atom"),
]

EventCallback = Callable[[str, dict], Awaitable[None]]


class _SchedulerShim:
    """ponytail: tiny stand-in exposing .running so main.py's health check stays
    unchanged after dropping apscheduler. Only attribute main.py reads."""
    def __init__(self):
        self._running = False

    @property
    def running(self) -> bool:
        return self._running


class DashboardScheduler:
    def __init__(self, ingestion: Ingestion, config):
        self.scheduler = _SchedulerShim()
        self.event_callbacks: List[EventCallback] = []
        self.ingestion = ingestion
        self.config = config
        self._update_lock = asyncio.Lock()
        self._tasks: List[asyncio.Task] = []

    def register_event_callback(self, callback: EventCallback):
        self.event_callbacks.append(callback)

    async def emit(self, event: str, payload: dict):
        for cb in self.event_callbacks:
            try:
                await cb(event, payload)
            except Exception:
                pass

    def start(self):
        interval_seconds = self.config.update_interval_hours * 3600

        async def _interval_loop():
            # ponytail: fixed sleep-first cadence; apscheduler IntervalTrigger also
            # sleeps before first fire. Drift not compensated. Add if SLA matters.
            while True:
                await asyncio.sleep(interval_seconds)
                await self.run_update(manual=False)

        self._tasks = [
            asyncio.ensure_future(_interval_loop()),
            asyncio.ensure_future(self._startup_update()),
        ]
        self.scheduler._running = True

    async def _startup_update(self):
        await asyncio.sleep(3)
        if not self.config.fetch_on_startup:
            return

        if self.config.startup_staleness_minutes > 0:
            try:
                statuses = await self.ingestion.repository.get_source_statuses()
                if statuses:
                    last_fetch = max((s.get("last_fetch") or "") for s in statuses)
                    if last_fetch:
                        from datetime import datetime as dt
                        last_dt = dt.fromisoformat(last_fetch)
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=timezone.utc)
                        age_minutes = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
                        if age_minutes < self.config.startup_staleness_minutes:
                            return
            except Exception:
                pass

        await self.run_update(manual=False)

    async def run_update(self, manual: bool = False):
        if self._update_lock.locked():
            await self.emit("news_updated", {
                "manual": manual,
                "new_articles": 0,
                "errors": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "skipped": True,
                "reason": "update already in progress",
            })
            return

        async with self._update_lock:
            result = await self.ingestion.ingest(manual=manual)

            await self.emit("news_updated", {
                "manual": manual,
                "new_articles": result.total_new,
                "errors": result.total_errors,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def shutdown(self):
        for task in self._tasks:
            task.cancel()
        self._tasks = []
        self.scheduler._running = False


def build_fetchers(config) -> List[Fetcher]:
    fetchers = []
    for attr, kind, name, url in SOURCES:
        if not getattr(config, f"fetch_{attr}", False):
            continue
        if kind == "kev":
            fetchers.append(CISAKEVFetcher(config))
        else:
            fetchers.append(RSSFetcher(name, url, config))
    return fetchers


def create_scheduler(
    repository=None,
    config=None,
) -> DashboardScheduler:
    if config is None:
        from config import settings
        config = settings
    if repository is None:
        repository = SQLiteArticleRepository(config.resolved_database_path)
    ingestion = Ingestion(fetchers=build_fetchers(config), repository=repository, config=config)
    return DashboardScheduler(ingestion=ingestion, config=config)