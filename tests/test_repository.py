import pytest

from repositories import SQLiteArticleRepository, SourceResult


@pytest.mark.asyncio
async def test_insert_and_get_article(tmp_path):
    db = tmp_path / "test.db"
    repo = SQLiteArticleRepository(str(db))
    await repo.init_db()

    inserted = await repo.insert_or_ignore_article({
        "title": "A",
        "url": "https://example.com/a",
        "source": "test",
        "published_at": "2026-07-10T00:00:00+00:00",
        "summary": "",
        "desc": "",
        "tag": "General / Tech",
        "importance": "",
        "noteworthy": "",
    })
    assert inserted is True

    articles = await repo.get_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "A"


@pytest.mark.asyncio
async def test_insert_or_ignore_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    repo = SQLiteArticleRepository(str(db))
    await repo.init_db()

    article = {
        "title": "A",
        "url": "https://example.com/a",
        "source": "test",
        "published_at": "2026-07-10T00:00:00+00:00",
    }
    assert await repo.insert_or_ignore_article(article) is True
    assert await repo.insert_or_ignore_article(article) is False


@pytest.mark.asyncio
async def test_source_status(tmp_path):
    db = tmp_path / "test.db"
    repo = SQLiteArticleRepository(str(db))
    await repo.init_db()

    await repo.update_source_status(SourceResult(source="S", status="ok", item_count=3))
    statuses = await repo.get_source_statuses()
    assert statuses[0]["source"] == "S"
    assert statuses[0]["item_count"] == 3


@pytest.mark.asyncio
async def test_bookmark_and_read(tmp_path):
    db = tmp_path / "test.db"
    repo = SQLiteArticleRepository(str(db))
    await repo.init_db()

    await repo.insert_or_ignore_article({
        "title": "A",
        "url": "https://example.com/a",
        "source": "test",
        "published_at": "2026-07-10T00:00:00+00:00",
    })
    articles = await repo.get_articles()
    article_id = articles[0]["id"]

    state = await repo.toggle_bookmark(article_id)
    assert state is True
    state = await repo.toggle_bookmark(article_id)
    assert state is False

    await repo.mark_read(article_id)
    article = await repo.get_article_by_id(article_id)
    assert article["is_read"] == 1
