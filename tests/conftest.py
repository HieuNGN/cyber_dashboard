import importlib
import tempfile

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from pathlib import Path


@pytest_asyncio.fixture
async def repo(tmp_path):
    from repositories import SQLiteArticleRepository
    r = SQLiteArticleRepository(str(tmp_path / "test.db"))
    await r.init_db()
    yield r


def _build_isolated_client(monkeypatch, tmp_path, *, with_auth: bool):
    """Build a TestClient whose lifespan scheduler uses an isolated SQLite repo.

    Patches ``main.create_scheduler`` so the real fetchers never run. Uses a
    tmp_path-backed SQLite db so nothing touches ``data/dashboard.db``.
    """
    if with_auth:
        monkeypatch.setenv("API_KEY", "test-secret-key")
    else:
        monkeypatch.delenv("API_KEY", raising=False)
    # Keep CORS empty so no real-env origins leak in.
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    import config
    importlib.reload(config)
    cfg = config.Settings()

    from repositories import SQLiteArticleRepository
    from scheduler import create_scheduler as real_create_scheduler

    # ponytail: tmp_path fixture-scoped dir; lifecycle's init_db() runs in lifespan
    db_path = str(Path(tempfile.mkdtemp()) / "test.db")
    mem_repo = SQLiteArticleRepository(db_path)

    def _fake_create_scheduler(repository=None, config=None):
        return real_create_scheduler(repository=mem_repo, config=cfg)

    import main
    main.config = cfg
    monkeypatch.setattr(main, "create_scheduler", _fake_create_scheduler)

    from main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_with_auth(monkeypatch, tmp_path):
    yield from _build_isolated_client(monkeypatch, tmp_path, with_auth=True)


@pytest.fixture
def client_no_auth(monkeypatch, tmp_path):
    yield from _build_isolated_client(monkeypatch, tmp_path, with_auth=False)