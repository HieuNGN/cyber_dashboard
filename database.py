import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from config import settings


SCHEMA = """
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

CREATE TABLE IF NOT EXISTS daily_digest_cache (
    day_key TEXT PRIMARY KEY,
    date TEXT,
    data_json TEXT,
    updated_at TEXT
);
"""


def ensure_db_dir():
    path = settings.resolved_database_path
    path.parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def get_db():
    ensure_db_dir()
    async with aiosqlite.connect(settings.resolved_database_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    ensure_db_dir()
    async with aiosqlite.connect(settings.resolved_database_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def insert_or_ignore_article(
    title: str,
    url: str,
    source: str,
    published_at: Optional[str],
    summary: Optional[str],
    desc: Optional[str],
    tag: Optional[str],
    importance: Optional[str],
    noteworthy: Optional[str],
):
    async with get_db() as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO articles
            (title, url, source, published_at, summary, desc, tag, importance, noteworthy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, url, source, published_at, summary, desc, tag, importance, noteworthy),
        )
        await db.commit()


async def update_source_status(source: str, status: str, error_message: Optional[str] = None, item_count: int = 0):
    from datetime import datetime, timezone
    async with get_db() as db:
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
            (source, datetime.now(timezone.utc).isoformat(), status, error_message, item_count),
        )
        await db.commit()


async def get_source_statuses():
    async with get_db() as db:
        async with db.execute("SELECT * FROM source_status ORDER BY source") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_articles(
    tag: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
    bookmarked: Optional[bool] = None,
    read: Optional[bool] = None,
    limit: int = 200,
    offset: int = 0,
):
    async with get_db() as db:
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
            return [dict(row) for row in rows]


async def get_article_by_id(article_id: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM articles WHERE id = ?", (article_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def toggle_bookmark(article_id: int):
    async with get_db() as db:
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


async def mark_read(article_id: int, is_read: bool = True):
    async with get_db() as db:
        await db.execute(
            "UPDATE articles SET is_read = ? WHERE id = ?",
            (1 if is_read else 0, article_id),
        )
        await db.commit()


async def prune_old_articles(retention_days: int):
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    async with get_db() as db:
        # Never prune bookmarked articles
        await db.execute(
            "DELETE FROM articles WHERE published_at < ? AND is_bookmarked = 0",
            (cutoff,),
        )
        await db.commit()


async def get_daily_digest():
    from services.digest import build_digest
    async with get_db() as db:
        return await build_digest(db)
