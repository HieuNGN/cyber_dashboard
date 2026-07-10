from typing import Dict, Any, Set


class Deduplicator:
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_titles: Set[str] = set()

    def is_duplicate(self, article: Dict[str, Any]) -> bool:
        url = article.get("url", "").lower().strip()
        title = article.get("title", "").lower().strip()
        if url in self.seen_urls or title in self.seen_titles:
            return True
        self.seen_urls.add(url)
        self.seen_titles.add(title)
        return False

    def reset(self):
        self.seen_urls.clear()
        self.seen_titles.clear()
