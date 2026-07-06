from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Fetcher(ABC):
    def __init__(self, source_name: str, enabled: bool = True):
        self.source_name = source_name
        self.enabled = enabled

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Return list of normalized raw article dicts."""
        pass

    def is_enabled(self) -> bool:
        return self.enabled
