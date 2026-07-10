import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any

from .base import Fetcher


CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class CISAKEVFetcher(Fetcher):
    def __init__(self, config=None, enabled: bool = True):
        super().__init__("CISA KEV", enabled)
        self.config = config

    async def fetch(self) -> List[Dict[str, Any]]:
        max_articles = self.config.max_articles_per_source if self.config else 50
        max_summary = self.config.max_summary_length if self.config else 500

        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            resp = await client.get(CISA_KEV_URL)
            if 300 <= resp.status_code < 400:
                raise httpx.HTTPStatusError(
                    f"CISA KEV feed returned redirect {resp.status_code}; refusing to follow",
                    request=resp.request, response=resp
                )
            resp.raise_for_status()
            data = resp.json()

        items = data.get("vulnerabilities", [])[:max_articles]
        articles = []
        now = datetime.now(timezone.utc).isoformat()
        for item in items:
            cve = item.get("cveID", "")
            title = f"CISA KEV: {cve} — {item.get('vulnerabilityName', '')}".strip()
            desc = item.get("shortDescription", "") or item.get("notes", "")
            pub = item.get("dateAdded", "")
            published_at = None
            if pub:
                try:
                    published_at = datetime.strptime(pub, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    published_at = now
            articles.append({
                "title": title,
                "url": item.get("vendorAdvisory", "") or f"https://nvd.nist.gov/vuln/detail/{cve}",
                "source": self.source_name,
                "published_at": published_at or now,
                "summary": desc[:max_summary],
                "desc": desc[:max_summary],
                "raw_tags": ["CISA KEV", item.get("vendorProject", ""), item.get("product", "")],
            })
        return articles
