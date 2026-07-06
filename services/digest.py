import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import aiosqlite


def _to_date_label(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d/%m/%y")
    except Exception:
        return "-"


async def build_digest(db: aiosqlite.Connection) -> Dict[str, Any]:
    """Build today/yesterday/day_before_yesterday digest from SQLite.

    Uses calendar buckets when data exists; otherwise falls back to relative
    recency so the dashboard is never empty on first run.
    """
    today = datetime.now(timezone.utc)

    # Calendar boundaries
    boundaries = {
        "today": (today.replace(hour=0, minute=0, second=0, microsecond=0),
                  today.strftime("%d/%m/%y")),
        "yesterday": ((today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                      (today - timedelta(days=1)).strftime("%d/%m/%y")),
        "day_before_yesterday": ((today - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0),
                                 (today - timedelta(days=2)).strftime("%d/%m/%y")),
    }

    result = {}
    any_hits = False

    for key, (start, label) in boundaries.items():
        end = (start + timedelta(days=1)).isoformat()
        async with db.execute(
            """
            SELECT id, title, url, source, published_at, summary, desc, tag,
                   importance, noteworthy, is_read, is_bookmarked
            FROM articles
            WHERE published_at >= ? AND published_at < ?
            ORDER BY published_at DESC
            """,
            (start.isoformat(), end),
        ) as cursor:
            rows = await cursor.fetchall()
            if rows:
                any_hits = True
            result[key] = {"date": label, "items": _rows_to_items(rows)}

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
            result = _bucket_by_recency(rows)

    # Cache
    await db.execute(
        """
        INSERT INTO daily_digest_cache (day_key, date, data_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(day_key) DO UPDATE SET date=excluded.date, data_json=excluded.data_json, updated_at=excluded.updated_at
        """,
        ("latest", today.isoformat(), json.dumps(result), today.isoformat()),
    )
    await db.commit()

    return result


def _rows_to_items(rows: List[aiosqlite.Row]) -> List[Dict[str, Any]]:
    items = []
    for row in rows:
        d = dict(row)
        items.append({
            "id": d["id"],
            "title": d["title"],
            "tag": d["tag"] or "General / Tech",
            "desc": d["desc"] or "",
            "summary": d["summary"] or "",
            "importance": d["importance"] or "",
            "noteworthy": d["noteworthy"] or "",
            "link": d["url"],
            "source": d["source"],
            "is_read": bool(d["is_read"]),
            "is_bookmarked": bool(d["is_bookmarked"]),
        })
    return items


def _bucket_by_recency(rows: List[aiosqlite.Row]) -> Dict[str, Any]:
    """Split rows into today/yesterday/dby by distinct published dates."""
    from collections import OrderedDict
    by_date: Dict[str, List[aiosqlite.Row]] = OrderedDict()
    for row in rows:
        label = _to_date_label(dict(row)["published_at"])
        by_date.setdefault(label, []).append(row)

    keys = ["today", "yesterday", "day_before_yesterday"]
    result = {}
    date_keys = list(by_date.keys())
    for i, key in enumerate(keys):
        if i < len(date_keys):
            result[key] = {"date": date_keys[i], "items": _rows_to_items(by_date[date_keys[i]])}
        else:
            result[key] = {"date": "-", "items": []}
    return result
