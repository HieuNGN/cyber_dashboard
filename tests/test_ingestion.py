import pytest

from config import Settings
from ingestion import Ingestion
from repositories import SQLiteArticleRepository
from tests import BrokenFetcher, FakeFetcher


@pytest.mark.asyncio
async def test_ingestion_stores_articles(tmp_path):
    repo = SQLiteArticleRepository(str(tmp_path / "test.db"))
    await repo.init_db()
    fetcher = FakeFetcher("Test Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    result = await ingestion.ingest()

    assert result.total_new == 1
    assert result.total_errors == 0
    articles = await repo.get_articles()
    assert len(articles) == 1
    assert articles[0].title == "A"


@pytest.mark.asyncio
async def test_ingestion_dedups_within_run(tmp_path):
    repo = SQLiteArticleRepository(str(tmp_path / "test.db"))
    await repo.init_db()
    fetcher = FakeFetcher("Test Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    result = await ingestion.ingest()

    assert result.total_new == 1
    articles = await repo.get_articles()
    assert len(articles) == 1


@pytest.mark.asyncio
async def test_ingestion_handles_broken_fetcher(tmp_path):
    repo = SQLiteArticleRepository(str(tmp_path / "test.db"))
    await repo.init_db()
    fetcher = BrokenFetcher("Bad Source")

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    result = await ingestion.ingest()

    assert result.total_new == 0
    assert result.total_errors == 1
    statuses = await repo.get_source_statuses()
    bad = [s for s in statuses if s["source"] == "Bad Source"][0]
    assert bad["status"] == "error"


@pytest.mark.asyncio
async def test_ingestion_records_source_status(tmp_path):
    repo = SQLiteArticleRepository(str(tmp_path / "test.db"))
    await repo.init_db()
    fetcher = FakeFetcher("Good Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    ingestion = Ingestion(fetchers=[fetcher], repository=repo)
    await ingestion.ingest()

    statuses = await repo.get_source_statuses()
    good = [s for s in statuses if s["source"] == "Good Source"][0]
    assert good["status"] == "ok"
    assert good["item_count"] == 1


@pytest.mark.asyncio
async def test_ingestion_uses_config_retention(tmp_path):
    repo = SQLiteArticleRepository(str(tmp_path / "test.db"))
    await repo.init_db()
    fetcher = FakeFetcher("Test Source", [
        {"title": "A", "url": "https://example.com/a", "published_at": "2026-07-10T00:00:00+00:00"},
    ])

    config = Settings(retention_days=7)
    ingestion = Ingestion(fetchers=[fetcher], repository=repo, config=config)
    result = await ingestion.ingest()

    assert result.total_new == 1