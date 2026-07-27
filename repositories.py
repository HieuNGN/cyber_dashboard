from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiosqlite

from config import settings
from services.article import Article


@dataclass
class SourceResult:
    source: str
    status: str  # "ok" | "error"
    item_count: int = 0
    error_message: Optional[str] = None


@dataclass
class IngestResult:
    total_new: int
    total_errors: int
    source_results: List[SourceResult] = field(default_factory=list)


class SQLiteArticleRepository:
    """SQLite adapter for ArticleRepository."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = Path(db_path) if db_path else settings.resolved_database_path

    def _ensure_db_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _row_to_article(row) -> Article:
        # sqlite Row -> dict; raw_tags is not a column so default to [].
        d = dict(row) if not isinstance(row, dict) else row
        return Article(
            id=d.get("id"),
            title=d.get("title", ""),
            url=d.get("url", ""),
            source=d.get("source", "unknown"),
            published_at=d.get("published_at"),
            summary=d.get("summary", "") or "",
            desc=d.get("desc", "") or "",
            tag=d.get("tag", "General / Tech"),
            importance=d.get("importance", "") or "",
            noteworthy=d.get("noteworthy", "") or "",
            raw_tags=[],
            fetched_at=d.get("fetched_at"),
            is_read=d.get("is_read", 0) or 0,
            is_bookmarked=d.get("is_bookmarked", 0) or 0,
        )

    async def init_db(self):
        self._ensure_db_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    async def insert_or_ignore_article(self, article: Article) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO articles
                (title, url, source, published_at, summary, desc, tag, importance, noteworthy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.title,
                    article.url,
                    article.source,
                    article.published_at,
                    article.summary,
                    article.desc,
                    article.tag,
                    article.importance,
                    article.noteworthy,
                ),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_source_status(self, result: SourceResult) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO source_status (source, last_fetch, status, error_message, item_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source) DO UPDATE SET
                    last_fetch=excluded.last_fetch,
                    status=excluded.status,
                    error_message=excluded.error_message,
                    item_count=excluded.item_count
                """,
                (
                    result.source,
                    datetime.now(timezone.utc).isoformat(),
                    result.status,
                    result.error_message,
                    result.item_count,
                ),
            )
            await db.commit()

    async def prune_old_articles(self, retention_days: int) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM articles WHERE published_at < ? AND is_bookmarked = 0",
                (cutoff,),
            )
            await db.commit()

    async def get_articles(
        self,
        tag: Optional[str] = None,
        source: Optional[str] = None,
        q: Optional[str] = None,
        bookmarked: Optional[bool] = None,
        read: Optional[bool] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Article]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM articles WHERE 1=1"
            params = []
            if tag:
                query += " AND tag LIKE ?"
                params.append(f"%{tag}%")
            if source:
                query += " AND source = ?"
                params.append(source)
            if q:
                query += " AND (title LIKE ? OR summary LIKE ?)"
                params.extend([f"%{q}%", f"%{q}%"])
            if bookmarked is not None:
                query += " AND is_bookmarked = ?"
                params.append(1 if bookmarked else 0)
            if read is not None:
                query += " AND is_read = ?"
                params.append(1 if read else 0)
            query += " ORDER BY published_at DESC, fetched_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_article(row) for row in rows]

    async def get_article_by_id(self, article_id: int) -> Optional[Article]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM articles WHERE id = ?", (article_id,)) as cursor:
                row = await cursor.fetchone()
                return self._row_to_article(row) if row else None

    async def update_article_classification(self, article_id: int, tag: str, importance: str, noteworthy: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE articles SET tag = ?, importance = ?, noteworthy = ? WHERE id = ?",
                (tag, importance, noteworthy, article_id),
            )
            await db.commit()

    async def toggle_bookmark(self, article_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE articles SET is_bookmarked = NOT is_bookmarked WHERE id = ?",
                (article_id,),
            )
            await db.commit()
            async with db.execute(
                "SELECT is_bookmarked FROM articles WHERE id = ?", (article_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

    async def mark_read(self, article_id: int, is_read: bool = True) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE articles SET is_read = ? WHERE id = ?",
                (1 if is_read else 0, article_id),
            )
            await db.commit()

    async def get_source_statuses(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM source_status ORDER BY source") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def build_digest(self, timezone_name: str = "Asia/Bangkok") -> Dict[str, Any]:
        """Build today/yesterday/day_before_yesterday digest from SQLite.

        Buckets are computed in the configured timezone (default Asia/Bangkok, UTC+7)
        so 'today' matches the user's local day. Falls back to relative recency if
        calendar buckets are empty.
        """
        from services.digest_formatting import bucket_by_recency, local_day_bounds, rows_to_items

        boundaries = {
            "today": local_day_bounds(0, timezone_name),
            "yesterday": local_day_bounds(1, timezone_name),
            "day_before_yesterday": local_day_bounds(2, timezone_name),
        }

        result = {}
        any_hits = False

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            for key, (start_iso, end_iso, label) in boundaries.items():
                async with db.execute(
                    """
                    SELECT id, title, url, source, published_at, summary, desc, tag,
                           importance, noteworthy, is_read, is_bookmarked
                    FROM articles
                    WHERE published_at >= ? AND published_at < ?
                    ORDER BY published_at DESC
                    """,
                    (start_iso, end_iso),
                ) as cursor:
                    rows = await cursor.fetchall()
                    if rows:
                        any_hits = True
                    result[key] = {"date": label, "items": rows_to_items([dict(row) for row in rows])}

            # Fallback: relative recency if calendar buckets are empty
            if not any_hits:
                async with db.execute(
                    """
                    SELECT id, title, url, source, published_at, summary, desc, tag,
                           importance, noteworthy, is_read, is_bookmarked
                    FROM articles
                    ORDER BY published_at DESC
                    LIMIT 300
                    """
                ) as cursor:
                    rows = await cursor.fetchall()
                    result = bucket_by_recency([dict(row) for row in rows], timezone_name)

        return result


_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    published_at TEXT,
    summary TEXT,
    desc TEXT,
    tag TEXT,
    importance TEXT,
    noteworthy TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT 0,
    is_bookmarked BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_bookmark ON articles(is_bookmarked);

CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    last_fetch TEXT,
    status TEXT,
    error_message TEXT,
    item_count INTEGER DEFAULT 0
);
"""
