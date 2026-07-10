import pytest

from dashboard_config import DashboardConfig
from fetchers.base import Fetcher
from ingestion import Ingestion
from tests import InMemoryArticleRepository


class FakeFetcher(Fetcher):
    def __init__(self, source_name, articles):
        super().__init__(source_name)
        self.articles = articles

    async def fetch(self):
        return self.articles


class BrokenFetcher(Fetcher):
    async def fetch(self):
        raise RuntimeError("network down")


@pytest.mark.asyncio
async def test_ingestion_stores_articles():
    repo = InMemoryArticleRepository()
    await repo.init_db()
    fetcher = FakeFetcher("Test Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    result = await ingestion.ingest()

    assert result.total_new == 1
    assert result.total_errors == 0
    assert len(repo.articles) == 1
    assert repo.articles[0]["title"] == "A"


@pytest.mark.asyncio
async def test_ingestion_dedups_within_run():
    repo = InMemoryArticleRepository()
    await repo.init_db()
    fetcher = FakeFetcher("Test Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    result = await ingestion.ingest()

    assert result.total_new == 1
    assert len(repo.articles) == 1


@pytest.mark.asyncio
async def test_ingestion_handles_broken_fetcher():
    repo = InMemoryArticleRepository()
    await repo.init_db()
    fetcher = BrokenFetcher("Bad Source")

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    result = await ingestion.ingest()

    assert result.total_new == 0
    assert result.total_errors == 1
    assert repo.source_statuses["Bad Source"]["status"] == "error"


@pytest.mark.asyncio
async def test_ingestion_records_source_status():
    repo = InMemoryArticleRepository()
    await repo.init_db()
    fetcher = FakeFetcher("Good Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    await ingestion.ingest()

    assert repo.source_statuses["Good Source"]["status"] == "ok"
    assert repo.source_statuses["Good Source"]["item_count"] == 1


@pytest.mark.asyncio
async def test_ingestion_uses_config_retention():
    repo = InMemoryArticleRepository()
    await repo.init_db()
    fetcher = FakeFetcher("Test Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    config = DashboardConfig(retention_days=7)
    ingestion = Ingestion(fetchers=[fetcher], repository=repo, config=config)
    result = await ingestion.ingest()

    assert result.total_new == 1
