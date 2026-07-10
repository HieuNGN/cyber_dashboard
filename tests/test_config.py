import pytest

from dashboard_config import DashboardConfig
from scheduler import build_fetchers, create_scheduler


def test_build_fetchers_respects_source_toggles():
    config = DashboardConfig(
        fetch_hackernews=True,
        fetch_bleepingcomputer=False,
        fetch_krebs=False,
        fetch_cisa_kev=False,
        fetch_tomshardware=False,
        fetch_servethehome=False,
        fetch_wccftech=False,
        fetch_theregister=False,
    )
    fetchers = build_fetchers(config)
    assert len(fetchers) == 1
    assert fetchers[0].source_name == "The Hacker News"


def test_build_fetchers_all_disabled():
    config = DashboardConfig(
        fetch_hackernews=False,
        fetch_bleepingcomputer=False,
        fetch_krebs=False,
        fetch_cisa_kev=False,
        fetch_tomshardware=False,
        fetch_servethehome=False,
        fetch_wccftech=False,
        fetch_theregister=False,
    )
    fetchers = build_fetchers(config)
    assert fetchers == []


@pytest.mark.asyncio
async def test_scheduler_uses_injected_config(tmp_path):
    from tests import InMemoryArticleRepository

    config = DashboardConfig(
        database_path=str(tmp_path / "test.db"),
        fetch_on_startup=False,
    )
    repo = InMemoryArticleRepository()
    scheduler = create_scheduler(repository=repo, config=config)

    assert scheduler.config.database_path == str(tmp_path / "test.db")
    assert scheduler.config.fetch_on_startup is False
