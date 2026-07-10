from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fetchers.base import Fetcher
from repositories import ArticleRepository, IngestResult, SourceResult
from services.classifier import classify
from services.dedup import Deduplicator
from services.enricher import enrich
from services.normalizer import normalize_article


class Ingestion:
    """Deep module: raw fetcher output → stored articles.

    Dependencies are injected through the constructor so tests can supply
    fake fetchers, an in-memory repository, and a fake config.
    """

    def __init__(
        self,
        fetchers: List[Fetcher],
        repository: ArticleRepository,
        config=None,
    ):
        self.fetchers = fetchers
        self.repository = repository
        self.config = config

    async def ingest(self, manual: bool = False) -> IngestResult:
        total_new = 0
        total_errors = 0
        source_results: List[SourceResult] = []
        deduplicator = Deduplicator()

        for fetcher in self.fetchers:
            if not fetcher.is_enabled():
                continue
            result = await self._ingest_source(fetcher, deduplicator)
            source_results.append(result)
            if result.status == "ok":
                total_new += result.item_count
            else:
                total_errors += 1

        retention = self.config.retention_days if self.config else 90
        await self.repository.prune_old_articles(retention)

        return IngestResult(
            total_new=total_new,
            total_errors=total_errors,
            source_results=source_results,
        )

    async def _ingest_source(
        self, fetcher: Fetcher, deduplicator: Deduplicator
    ) -> SourceResult:
        try:
            raw_articles = await fetcher.fetch()
        except Exception as e:
            result = SourceResult(
                source=fetcher.source_name,
                status="error",
                error_message=str(e)[:500],
                item_count=0,
            )
            await self.repository.update_source_status(result)
            return result

        new_for_source = 0
        for raw in raw_articles:
            article = normalize_article(raw)
            if not article:
                continue
            if deduplicator.is_duplicate(article):
                continue
            article["tag"] = classify(article)
            article = enrich(article)
            inserted = await self.repository.insert_or_ignore_article(article)
            if inserted:
                new_for_source += 1

        result = SourceResult(
            source=fetcher.source_name,
            status="ok",
            item_count=new_for_source,
        )
        await self.repository.update_source_status(result)
        return result
