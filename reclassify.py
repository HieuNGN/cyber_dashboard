import asyncio
import aiosqlite
from config import settings
from services.classifier import classify
from services.enricher import enrich


async def main():
    async with aiosqlite.connect(settings.resolved_database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, url, desc, summary, tag, source, importance, noteworthy FROM articles"
        ) as cursor:
            rows = await cursor.fetchall()
        updated = 0
        for row in rows:
            d = dict(row)
            # Preserve imported enriched tags if they exist and aren't generic
            if d["tag"] and d["tag"] != "General / Tech" and d["source"] == "Existing Digest":
                continue
            new_tag = classify({
                "title": d["title"],
                "desc": d["desc"],
                "summary": d["summary"],
                "raw_tags": [],
            })
            enriched = enrich({
                "title": d["title"],
                "url": d["url"],
                "source": d["source"],
                "tag": new_tag,
                "importance": d["importance"] or "",
                "noteworthy": d["noteworthy"] or "",
            })
            if (new_tag != d["tag"] or
                enriched["importance"] != (d["importance"] or "") or
                enriched["noteworthy"] != (d["noteworthy"] or "")):
                await db.execute(
                    "UPDATE articles SET tag = ?, importance = ?, noteworthy = ? WHERE id = ?",
                    (new_tag, enriched["importance"], enriched["noteworthy"], d["id"]),
                )
                updated += 1
        await db.commit()
    print(f"Updated {updated} articles")


if __name__ == "__main__":
    asyncio.run(main())
