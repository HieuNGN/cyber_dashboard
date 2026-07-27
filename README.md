# Cybersec Dashboard Server

FastAPI backend for a personal cybersecurity news dashboard. Aggregates RSS feeds and CISA KEV, classifies, enriches, serves a digest via REST + SSE.

## Quick start

```bash
conda activate cyberdashboard
python main.py
# → http://127.0.0.1:8080
```

Set `API_KEY` env var to enable state-changing endpoints (bookmark, read, export, trigger-update).

## Architecture

```
fetchers/        RSS + CISA KEV adapters (return raw dicts)
services/       Pipeline: normalize → dedup → classify → enrich
ingestion.py    Orchestrates fetch → persist
repositories.py SQLite adapter (sole aiosqlite importer)
scheduler.py    APScheduler interval + startup fetch
main.py         FastAPI app, SSE, static frontend
config.py       pydantic-settings env loader
```

### Seams (non-negotiable, see CONTEXT.md)
- **Fetcher seam**: fetchers return raw dicts, never touch DB.
- **Repository seam**: only module that imports `aiosqlite`.
- **Ingestion seam**: owns the per-run `Deduplicator`.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/news` | - | Today/yesterday/dby digest |
| GET | `/api/articles` | - | Filterable list (tag, source, q, bookmarked, read) |
| GET | `/api/articles/{id}` | - | Single article |
| POST | `/api/articles/{id}/bookmark` | API_KEY | Toggle bookmark |
| POST | `/api/articles/{id}/read` | API_KEY | Mark read |
| GET | `/api/bookmarks` | - | Bookmarked articles |
| GET | `/api/sources` | - | Fetcher status |
| POST | `/api/trigger-update` | API_KEY | Manual refresh |
| GET | `/api/events` | - | SSE stream (max 20 clients) |
| POST | `/api/export` | API_KEY | Write digest to Obsidian vault |
| GET | `/health` | - | Liveness |

## Config

Env vars (see `.env.example`): `API_KEY`, `CORS_ORIGINS`, `TIMEZONE`, `UPDATE_INTERVAL_HOURS`, `DATABASE_PATH`, `OBSIDIAN_VAULT_PATH`, source toggles (`FETCH_*`).

## Tests

```bash
conda activate cyberdashboard
python -m pytest tests/ -v
```

## Deploy

Docker: `docker/docker-compose.yml`. K8s: `k8s/` (Deployment + Secret for API_KEY + PVC).

<!-- ponytail: README is the only doc. CONTEXT.md and AGENTS.md hold agent instructions, not user docs. -->