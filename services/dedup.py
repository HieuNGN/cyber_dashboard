from typing import Set

from services.article import Article


class Deduplicator:
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_titles: Set[str] = set()

    def is_duplicate(self, article: Article) -> bool:
        url = article.url.lower().strip()
        title = article.title.lower().strip()
        if url in self.seen_urls or title in self.seen_titles:
            return True
        self.seen_urls.add(url)
        self.seen_titles.add(title)
        return False