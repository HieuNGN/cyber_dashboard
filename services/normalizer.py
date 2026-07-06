import re
import hashlib
from typing import Dict, Any, List


def normalize_article(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = (raw.get("title") or "").strip()
    url = (raw.get("url") or "").strip()
    if not title or not url:
        return {}

    # Clean URL for dedup
    url = url.split("?")[0].split("#")[0]

    desc = (raw.get("desc") or raw.get("description") or "").strip()
    summary = (raw.get("summary") or desc).strip()

    # Import path: if fields already enriched, keep them
    importance = (raw.get("importance") or "").strip()
    noteworthy = (raw.get("noteworthy") or "").strip()

    return {
        "title": title,
        "url": url,
        "source": (raw.get("source") or "unknown").strip(),
        "published_at": raw.get("published_at"),
        "summary": summary,
        "desc": desc,
        "importance": importance,
        "noteworthy": noteworthy,
        "raw_tags": raw.get("raw_tags", []),
    }


def article_hash(article: Dict[str, Any]) -> str:
    text = f"{article['url']}::{article['title']}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
