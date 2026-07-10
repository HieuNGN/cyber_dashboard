from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List


def to_date_label(iso: str, timezone_name: str = "Asia/Bangkok") -> str:
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo(timezone_name)).strftime("%d/%m/%y")
    except Exception:
        return "-"


def local_day_bounds(day_offset: int = 0, timezone_name: str = "Asia/Bangkok") -> tuple[str, str, str]:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(timezone_name)
    local_now = datetime.now(tz)
    local_day = local_now.date() - timedelta(days=day_offset)
    local_start = datetime(local_day.year, local_day.month, local_day.day, tzinfo=tz)
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = utc_start + timedelta(days=1)
    label = local_start.strftime("%d/%m/%y")
    return utc_start.isoformat(), utc_end.isoformat(), label


def rows_to_items(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "title": row["title"],
            "tag": row.get("tag", "General / Tech"),
            "desc": row.get("desc", ""),
            "summary": row.get("summary", ""),
            "importance": row.get("importance", ""),
            "noteworthy": row.get("noteworthy", ""),
            "link": row["url"],
            "source": row["source"],
            "is_read": bool(row.get("is_read", 0)),
            "is_bookmarked": bool(row.get("is_bookmarked", 0)),
        })
    return items


def bucket_by_recency(rows: List[Dict[str, Any]], timezone_name: str = "Asia/Bangkok") -> Dict[str, Any]:
    from collections import OrderedDict
    by_date: Dict[str, List[Dict[str, Any]]] = OrderedDict()
    for row in rows:
        label = to_date_label(row["published_at"], timezone_name)
        by_date.setdefault(label, []).append(row)

    keys = ["today", "yesterday", "day_before_yesterday"]
    result = {}
    date_keys = list(by_date.keys())
    for i, key in enumerate(keys):
        if i < len(date_keys):
            result[key] = {"date": date_keys[i], "items": rows_to_items(by_date[date_keys[i]])}
        else:
            result[key] = {"date": "-", "items": []}
    return result
