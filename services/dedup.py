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


_is_duplicate_instance = Deduplicator()


def is_duplicate(article: Dict[str, Any]) -> bool:
    return _is_duplicate_instance.is_duplicate(article)


def reset_dedup():
    _is_duplicate_instance.seen_urls.clear()
    _is_duplicate_instance.seen_titles.clear()
