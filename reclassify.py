import asyncio
from dataclasses import replace

from config import settings
from repositories import SQLiteArticleRepository
from services.classifier import classify
from services.enricher import enrich


async def main():
    config = settings
    repo = SQLiteArticleRepository(config.resolved_database_path)
    await repo.init_db()

    articles = await repo.get_articles()
    updated = 0
    for a in articles:
        # Preserve imported enriched tags for Existing Digest source.
        if a.tag and a.tag != "General / Tech" and a.source == "Existing Digest":
            continue
        new_tag = classify(a)
        enriched = enrich(replace(a, tag=new_tag))
        if (new_tag != a.tag or
            enriched.importance != a.importance or
            enriched.noteworthy != a.noteworthy):
            await repo.update_article_classification(a.id, new_tag, enriched.importance, enriched.noteworthy)
            updated += 1
    print(f"Updated {updated} articles")


if __name__ == "__main__":
    asyncio.run(main())