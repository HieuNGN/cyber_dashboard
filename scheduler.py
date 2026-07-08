import asyncio
from datetime import datetime, timezone
from typing import Callable, List, Awaitable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from fetchers import RSSFetcher, CISAKEVFetcher
from fetchers.base import Fetcher
from services import normalize_article, classify, is_duplicate
from services.digest import build_digest
from services.enricher import enrich
import database


EventCallback = Callable[[str, dict], Awaitable[None]]


class DashboardScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self.event_callbacks: List[EventCallback] = []
        self._last_digest = {}

    def register_event_callback(self, callback: EventCallback):
        self.event_callbacks.append(callback)

    async def emit(self, event: str, payload: dict):
        for cb in self.event_callbacks:
            try:
                await cb(event, payload)
            except Exception:
                pass

    def build_fetchers(self) -> List[Fetcher]:
        fetchers = []
        if settings.fetch_hackernews:
            fetchers.append(RSSFetcher("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"))
        if settings.fetch_bleepingcomputer:
            fetchers.append(RSSFetcher("BleepingComputer", "https://www.bleepingcomputer.com/feed/"))
        if settings.fetch_krebs:
            fetchers.append(RSSFetcher("Krebs on Security", "https://krebsonsecurity.com/feed/"))
        if settings.fetch_cisa_kev:
            fetchers.append(CISAKEVFetcher())
        if settings.fetch_tomshardware:
            fetchers.append(RSSFetcher("Tom's Hardware", "https://www.tomshardware.com/feeds.xml"))
        if settings.fetch_servethehome:
            fetchers.append(RSSFetcher("ServeTheHome", "https://www.servethehome.com/feed/"))
        if settings.fetch_wccftech:
            fetchers.append(RSSFetcher("Wccftech", "https://wccftech.com/feed/"))
        if settings.fetch_theregister:
            fetchers.append(RSSFetcher("The Register", "https://www.theregister.com/headlines.atom"))
        return fetchers

    async def run_update(self, manual: bool = False):
        from services.dedup import reset_dedup
        reset_dedup()

        fetchers = self.build_fetchers()
        total_new = 0
        total_errors = 0

        for fetcher in fetchers:
            if not fetcher.is_enabled():
                continue
            try:
                raw_articles = await fetcher.fetch()
                new_for_source = 0
                for raw in raw_articles:
                    article = normalize_article(raw)
                    if not article:
                        continue
                    if is_duplicate(article):
                        continue
                    article["tag"] = classify(article)
                    article = enrich(article)
                    await database.insert_or_ignore_article(
                        title=article["title"],
                        url=article["url"],
                        source=article["source"],
                        published_at=article["published_at"],
                        summary=article["summary"],
                        desc=article["desc"],
                        tag=article["tag"],
                        importance=article["importance"],
                        noteworthy=article["noteworthy"],
                    )
                    new_for_source += 1
                    total_new += 1
                await database.update_source_status(
                    fetcher.source_name, "ok", item_count=new_for_source
                )
            except Exception as e:
                total_errors += 1
                await database.update_source_status(
                    fetcher.source_name, "error", error_message=str(e)[:500]
                )

        # Rebuild digest after update
        async with database.get_db() as db:
            self._last_digest = await build_digest(db)

        # Prune old articles (keep bookmarks)
        await database.prune_old_articles(settings.retention_days)

        await self.emit("news_updated", {
            "manual": manual,
            "new_articles": total_new,
            "errors": total_errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def start(self):
        self.scheduler.add_job(
            self.run_update,
            trigger=IntervalTrigger(hours=settings.update_interval_hours),
            id="interval_update",
            replace_existing=True,
        )
        # Run a fresh fetch shortly after every startup
        self.scheduler.add_job(
            self._startup_update,
            "date",
            run_date=datetime.now(timezone.utc),
            id="startup_update",
            replace_existing=True,
        )
        self.scheduler.start()

    async def _startup_update(self):
        # Wait a few seconds for app to finish starting
        await asyncio.sleep(3)
        if not settings.fetch_on_startup:
            return

        # If data exists and is fresh enough, skip startup fetch
        if settings.startup_staleness_minutes > 0:
            async with database.get_db() as db:
                async with db.execute(
                    "SELECT MAX(fetched_at) FROM articles"
                ) as cursor:
                    row = await cursor.fetchone()
                    last_fetched = row[0] if row else None
            if last_fetched:
                from datetime import datetime
                try:
                    last_dt = datetime.fromisoformat(last_fetched)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    age_minutes = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
                    if age_minutes < settings.startup_staleness_minutes:
                        return
                except Exception:
                    pass

        await self.run_update(manual=False)

    def shutdown(self):
        self.scheduler.shutdown()


scheduler = DashboardScheduler()
