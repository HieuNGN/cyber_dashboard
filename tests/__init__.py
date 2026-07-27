from fetchers import Fetcher


class FakeFetcher(Fetcher):
    """Test fetcher that returns a fixed list of raw article dicts."""

    def __init__(self, source_name, articles):
        super().__init__(source_name)
        self.articles = articles

    async def fetch(self):
        return self.articles


class BrokenFetcher(Fetcher):
    """Test fetcher that always raises, simulating a down source."""

    async def fetch(self):
        raise RuntimeError("network down")