import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from zoneinfo import ZoneInfo
import aiosqlite

from config import settings


def _to_date_label(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo(settings.timezone)).strftime("%d/%m/%y")
    except Exception:
        return "-"


def _local_day_bounds(day_offset: int = 0) -> tuple[str, str, str]:
    """Return (utc_start_iso, utc_end_iso, local_label) for the configured timezone."""
    tz = ZoneInfo(settings.timezone)
    local_now = datetime.now(tz)
    local_day = local_now.date() - timedelta(days=day_offset)
    local_start = datetime(local_day.year, local_day.month, local_day.day, tzinfo=tz)
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = utc_start + timedelta(days=1)
    label = local_start.strftime("%d/%m/%y")
    return utc_start.isoformat(), utc_end.isoformat(), label


async def build_digest(db: aiosqlite.Connection) -> Dict[str, Any]:
    """Build today/yesterday/day_before_yesterday digest from SQLite.

    Buckets are computed in the configured timezone (default Asia/Bangkok, UTC+7)
    so 'today' matches the user's local day. Falls back to relative recency if
    calendar buckets are empty.
    """
    now_utc = datetime.now(timezone.utc)

    boundaries = {
        "today": _local_day_bounds(0),
        "yesterday": _local_day_bounds(1),
        "day_before_yesterday": _local_day_bounds(2),
    }

    result = {}
    any_hits = False

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
        ("latest", now_utc.isoformat(), json.dumps(result), now_utc.isoformat()),
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
