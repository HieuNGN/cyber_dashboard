import pytest

from services.digest_formatting import local_day_bounds, to_date_label


def test_local_day_bounds_returns_utc_range():
    start, end, label = local_day_bounds(0)
    assert start.endswith("+00:00")
    assert end.endswith("+00:00")
    assert start < end
    assert "/" in label


def test_to_date_label_handles_iso():
    assert to_date_label("2026-07-10T12:00:00+00:00") != "-"
    assert to_date_label("bad-date") == "-"


@pytest.mark.asyncio
async def test_build_digest_buckets_by_day(repo):
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).isoformat()

    await repo.insert_or_ignore_article({
        "title": "Today story",
        "url": "https://example.com/today",
        "source": "test",
        "published_at": today,
    })

    digest = await repo.build_digest()
    today_items = digest["today"]["items"]

    assert any(item["title"] == "Today story" for item in today_items)


@pytest.mark.asyncio
async def test_build_digest_falls_back_when_empty(repo):
    digest = await repo.build_digest()
    # Empty repo: no calendar hits, fallback recency still returns keys
    assert "today" in digest
    assert "yesterday" in digest
    assert "day_before_yesterday" in digest


@pytest.mark.asyncio
async def test_build_digest_items_shape(repo):
    from datetime import datetime, timezone

    await repo.insert_or_ignore_article({
        "title": "A",
        "url": "https://example.com/a",
        "source": "test",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "tag": "Security / Vulnerability",
    })

    digest = await repo.build_digest()
    item = digest["today"]["items"][0]
    assert item["title"] == "A"
    assert item["tag"] == "Security / Vulnerability"
    assert "id" in item
    assert "link" in item
    assert "is_read" in item
    assert "is_bookmarked" in item
