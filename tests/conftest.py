import pytest_asyncio

from tests import InMemoryArticleRepository


@pytest_asyncio.fixture
async def repo():
    r = InMemoryArticleRepository()
    await r.init_db()
    yield r
