import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from dashboard_config import DashboardConfig
from fetchers import CISAKEVFetcher, RSSFetcher
from fetchers.base import Fetcher
from ingestion import Ingestion
from repositories import ArticleRepository, SQLiteArticleRepository


EventCallback = Callable[[str, dict], Awaitable[None]]


class DashboardScheduler:
    def __init__(self, ingestion: Ingestion, config: DashboardConfig):
        self.scheduler = AsyncIOScheduler(timezone=config.timezone)
        self.event_callbacks: List[EventCallback] = []
        self.ingestion = ingestion
        self.config = config
        self._update_lock = asyncio.Lock()

    def register_event_callback(self, callback: EventCallback):
        self.event_callbacks.append(callback)

    async def emit(self, event: str, payload: dict):
        for cb in self.event_callbacks:
            try:
                await cb(event, payload)
            except Exception:
                pass

    def start(self):
        self.scheduler.add_job(
            self.run_update,
            trigger=IntervalTrigger(hours=self.config.update_interval_hours),
            id="interval_update",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._startup_update,
            "date",
            run_date=datetime.now(timezone.utc),
            id="startup_update",
            replace_existing=True,
        )
        self.scheduler.start()

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
        self.scheduler.shutdown()


def build_fetchers(config: DashboardConfig) -> List[Fetcher]:
    fetchers = []
    if config.fetch_hackernews:
        fetchers.append(RSSFetcher("The Hacker News", "https://feeds.feedburner.com/TheHackersNews", config))
    if config.fetch_bleepingcomputer:
        fetchers.append(RSSFetcher("BleepingComputer", "https://www.bleepingcomputer.com/feed/", config))
    if config.fetch_krebs:
        fetchers.append(RSSFetcher("Krebs on Security", "https://krebsonsecurity.com/feed/", config))
    if config.fetch_cisa_kev:
        fetchers.append(CISAKEVFetcher(config))
    if config.fetch_tomshardware:
        fetchers.append(RSSFetcher("Tom's Hardware", "https://www.tomshardware.com/feeds.xml", config))
    if config.fetch_servethehome:
        fetchers.append(RSSFetcher("ServeTheHome", "https://www.servethehome.com/feed/", config))
    if config.fetch_wccftech:
        fetchers.append(RSSFetcher("Wccftech", "https://wccftech.com/feed/", config))
    if config.fetch_theregister:
        fetchers.append(RSSFetcher("The Register", "https://www.theregister.com/headlines.atom", config))
    return fetchers


def create_scheduler(
    repository: ArticleRepository = None,
    config: DashboardConfig = None,
) -> DashboardScheduler:
    if config is None:
        from config import settings
        from dashboard_config import settings_to_config
        config = settings_to_config(settings)
    if repository is None:
        repository = SQLiteArticleRepository(config.resolved_database_path)
    ingestion = Ingestion(fetchers=build_fetchers(config), repository=repository, config=config)
    return DashboardScheduler(ingestion=ingestion, config=config)
