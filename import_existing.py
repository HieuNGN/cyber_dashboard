import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import settings
import database
from services import normalize_article, classify


def parse_existing_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%d/%m/%y")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


async def main():
    await database.init_db()
    data_file = Path(__file__).parent / "data" / "news.json"
    if not data_file.exists():
        print("No existing news.json found.")
        return

    with open(data_file, "r") as f:
        data = json.load(f)

    count = 0
    for day_key, day_data in data.items():
        date_label = day_data.get("date", "")
        base_published = parse_existing_date(date_label)
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
            await database.insert_or_ignore_article(
                title=article["title"],
                url=article["url"],
                source=article["source"],
                published_at=article["published_at"],
                summary=article["summary"],
                desc=article["desc"],
                tag=article["tag"],
                importance=article["importance"],
                noteworthy=article["noteworthy"],
            )
            count += 1

    print(f"Imported {count} articles from existing news.json")


if __name__ == "__main__":
    asyncio.run(main())
