import httpx
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Any

from .base import Fetcher
from config import settings


class RSSFetcher(Fetcher):
    def __init__(self, source_name: str, feed_url: str, enabled: bool = True):
        super().__init__(source_name, enabled)
        self.feed_url = feed_url

    async def fetch(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()
            data = feedparser.parse(resp.content)

        articles = []
        for entry in data.entries[:settings.max_articles_per_source]:
            published = self._parse_date(entry)
            summary = self._extract_summary(entry)
            desc = self._extract_desc(entry)
            articles.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", "").strip(),
                "source": self.source_name,
                "published_at": published,
                "summary": summary,
                "desc": desc,
                "raw_tags": [t.get("term", "") for t in entry.get("tags", [])],
            })
        return articles

    def _parse_date(self, entry) -> str:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            dt = datetime(*published[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        return datetime.now(timezone.utc).isoformat()

    def _extract_summary(self, entry) -> str:
        text = entry.get("summary", "") or ""
        if not text and "content" in entry:
            text = entry["content"][0].get("value", "")
        return text[:settings.max_summary_length].strip()

    def _extract_desc(self, entry) -> str:
        text = entry.get("description", "") or ""
        if not text:
            text = self._extract_summary(entry)
        # Strip HTML tags lightly
        import re
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:settings.max_summary_length]
