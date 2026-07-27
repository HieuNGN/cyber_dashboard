from abc import ABC, abstractmethod
from typing import List, Dict, Any

import httpx


class Fetcher(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Return list of normalized raw article dicts."""
        pass

    def _raise_on_redirect(self, resp: "httpx.Response") -> None:
        """Refuse redirects; callers opt out of follow_redirects to detect them."""
        if 300 <= resp.status_code < 400:
            raise httpx.HTTPStatusError(
                f"{self.source_name} feed returned redirect {resp.status_code}; refusing to follow",
                request=resp.request, response=resp,
            )