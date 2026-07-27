import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser
import httpx

from .base import Fetcher

USER_AGENT = "CybersecDashboard/4.0 (+https://github.com/hieu/cybersec-dashboard)"


class RSSFetcher(Fetcher):
    def __init__(self, source_name: str, feed_url: str, config=None):
        super().__init__(source_name)
        self.feed_url = feed_url
        self.config = config

    async def fetch(self) -> List[Dict[str, Any]]:
        max_articles = self.config.max_articles_per_source if self.config else 50
        max_summary = self.config.max_summary_length if self.config else 500

        async with httpx.AsyncClient(
            timeout=30, follow_redirects=False, headers={"User-Agent": USER_AGENT}
        ) as client:
            resp = await client.get(self.feed_url)
            self._raise_on_redirect(resp)
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
        text = entry.get("summary", "") or ""
        if not text and "content" in entry:
            text = entry["content"][0].get("value", "")
        return text[:max_length].strip()

    def _extract_desc(self, entry, max_length: int) -> str:
        text = entry.get("description", "") or ""
        if not text:
            text = self._extract_summary(entry, max_length)
        # ponytail: light strip — normalizer does the full HTMLParser pass downstream.
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length]