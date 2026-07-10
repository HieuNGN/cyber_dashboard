import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any

from .base import Fetcher


class RSSFetcher(Fetcher):
    def __init__(self, source_name: str, feed_url: str, config=None, enabled: bool = True):
        super().__init__(source_name, enabled)
        self.feed_url = feed_url
        self.config = config

    async def fetch(self) -> List[Dict[str, Any]]:
        max_articles = self.config.max_articles_per_source if self.config else 50
        max_summary = self.config.max_summary_length if self.config else 500

        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            resp = await client.get(self.feed_url)
            if 300 <= resp.status_code < 400:
                raise httpx.HTTPStatusError(
                    f"Feed {self.feed_url} returned redirect {resp.status_code}; refusing to follow",
                    request=resp.request, response=resp
                )
            resp.raise_for_status()
            data = feedparser.parse(resp.content)

        articles = []
        for entry in data.entries[:max_articles]:
            published = self._parse_date(entry)
            summary = self._extract_summary(entry, max_summary)
            desc = self._extract_desc(entry, max_summary)
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

    def _extract_summary(self, entry, max_length: int) -> str:
        import re
        text = entry.get("summary", "") or ""
        if not text and "content" in entry:
            text = entry["content"][0].get("value", "")
        return text[:max_length].strip()

    def _extract_desc(self, entry, max_length: int) -> str:
        import re
        text = entry.get("description", "") or ""
        if not text:
            text = self._extract_summary(entry, max_length)
        # Strip HTML tags lightly
        text = re.sub(r"<<[^\u003e]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length]


import feedparser
