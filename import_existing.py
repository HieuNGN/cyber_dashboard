import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from config import settings
from dashboard_config import settings_to_config
from ingestion import Ingestion
from repositories import SQLiteArticleRepository, SourceResult
from services import normalize_article, classify


async def main():
    config = settings_to_config(settings)
    repo = SQLiteArticleRepository(config.resolved_database_path)
    await repo.init_db()

    ingestion = Ingestion(fetchers=[], repository=repo, config=config)
    data_file = Path(__file__).parent / "data" / "news.json"
    if not data_file.exists():
        print("No existing news.json found.")
        return

    with open(data_file, "r") as f:
        data = json.load(f)

    count = 0
    for day_key, day_data in data.items():
        date_label = day_data.get("date", "")
        base_published = _parse_existing_date(date_label)
        for item in day_data.get("items", []):
            raw = {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "source": "Existing Digest",
                "published_at": base_published,
                "summary": item.get("summary", ""),
                "desc": item.get("desc", ""),
                "importance": item.get("importance", ""),
                "noteworthy": item.get("noteworthy", ""),
                "raw_tags": [item.get("tag", "")],
            }
            article = normalize_article(raw)
            if not article:
                continue
            article["tag"] = item.get("tag", "") or classify(article)
            inserted = await repo.insert_or_ignore_article(article)
            if inserted:
                count += 1

    await repo.update_source_status(
        SourceResult(source="Existing Digest", status="ok", item_count=count)
    )
    print(f"Imported {count} articles from existing news.json")


def _parse_existing_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%d/%m/%y")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    asyncio.run(main())
