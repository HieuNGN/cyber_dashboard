import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any

from .base import Fetcher
from config import settings


CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class CISAKEVFetcher(Fetcher):
    def __init__(self, enabled: bool = True):
        super().__init__("CISA KEV", enabled)

    async def fetch(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(CISA_KEV_URL)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("vulnerabilities", [])[:settings.max_articles_per_source]
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
                "summary": desc[:settings.max_summary_length],
                "desc": desc[:settings.max_summary_length],
                "raw_tags": ["CISA KEV", item.get("vendorProject", ""), item.get("product", "")],
            })
        return articles
