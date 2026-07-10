from repositories import ArticleRepository, SourceResult


class InMemoryArticleRepository(ArticleRepository):
    """Test adapter for ArticleRepository."""

    def __init__(self):
        self.articles = []
        self.source_statuses = {}
        self._id = 0

    async def init_db(self):
        pass

    async def insert_or_ignore_article(self, article) -> bool:
        if any(a["url"] == article["url"] for a in self.articles):
            return False
        self._id += 1
        normalized = {
            **article,
            "id": self._id,
            "tag": article.get("tag", "General / Tech"),
            "desc": article.get("desc", ""),
            "summary": article.get("summary", ""),
            "importance": article.get("importance", ""),
            "noteworthy": article.get("noteworthy", ""),
            "is_read": article.get("is_read", 0),
            "is_bookmarked": article.get("is_bookmarked", 0),
        }
        self.articles.append(normalized)
        return True

    async def update_source_status(self, result: SourceResult) -> None:
        self.source_statuses[result.source] = {
            "source": result.source,
            "status": result.status,
            "item_count": result.item_count,
            "error_message": result.error_message,
        }

    async def prune_old_articles(self, retention_days: int) -> None:
        pass

    async def get_articles(self, **filters) -> list:
        return self.articles

    async def get_article_by_id(self, article_id: int):
        for a in self.articles:
            if a["id"] == article_id:
                return a
        return None

    async def toggle_bookmark(self, article_id: int) -> bool:
        return False

    async def mark_read(self, article_id: int, is_read: bool = True) -> None:
        pass

    async def get_source_statuses(self) -> list:
        return list(self.source_statuses.values())

    async def build_digest(self, timezone_name: str = "Asia/Bangkok") -> dict:
        from services.digest_formatting import bucket_by_recency, local_day_bounds, rows_to_items

        boundaries = {
            "today": local_day_bounds(0, timezone_name),
            "yesterday": local_day_bounds(1, timezone_name),
            "day_before_yesterday": local_day_bounds(2, timezone_name),
        }

        result = {}
        any_hits = False
        for key, (start_iso, end_iso, label) in boundaries.items():
            rows = [
                a for a in self.articles
                if a.get("published_at") and start_iso <= a["published_at"] < end_iso
            ]
            if rows:
                any_hits = True
            result[key] = {"date": label, "items": rows_to_items(rows)}

        if not any_hits:
            result = bucket_by_recency(self.articles[:300], timezone_name)

        return result
