# Domain Glossary

## Core concepts

- **Article**: a news item or vulnerability advisory the dashboard tracks. Key fields: title, url, source, published_at, summary, desc, tag, importance, noteworthy, is_read, is_bookmarked.
- **Source**: a feed or API that produces articles. Implemented as a `Fetcher` adapter (RSS feeds, CISA KEV JSON, etc.).
- **Fetcher**: adapter that fetches raw article-like dicts from a source. Implements `fetch() -> list[dict]`.
- **Ingestion**: the deep module that turns raw fetcher output into stored articles. Orchestrates normalize → dedup → classify → enrich → persist.
- **IngestResult**: value object returned by `Ingestion.ingest()`. Contains total_new, total_errors, and per-source results.
- **Repository**: persistence port. `ArticleRepository` defines the interface; `SQLiteArticleRepository` is the adapter.
- **Deduplicator**: per-run state that tracks seen URLs/titles to skip duplicates within one ingestion run.
- **Digest**: time-bucketed view (today / yesterday / day before yesterday) built from stored articles.

## Seams

- `Fetcher` seam lets tests supply fake sources.
- `ArticleRepository` seam lets tests use an in-memory store.
- `Ingestion` seam consolidates fetch → persist pipeline.

## Decisions

- Ingestion owns the per-run `Deduplicator`; no global singleton.
- Scheduler only schedules and emits events; it does not call the database or orchestrate fetch logic.
- Repository is the only module that writes/reads `articles` and `source_status` tables.
