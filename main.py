import asyncio
import os
import re
import json
import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings
import database
from scheduler import scheduler
from models import ExportRequest


base_dir = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="News Dashboard", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static
app.mount("/static", StaticFiles(directory=base_dir / "static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse(base_dir / "static" / "index.html")


@app.get("/api/news")
async def get_news():
    digest = await database.get_daily_digest()
    return JSONResponse(digest)


@app.get("/api/articles")
async def get_articles(
    tag: str = Query(None),
    source: str = Query(None),
    q: str = Query(None),
    bookmarked: bool = Query(None),
    read: bool = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    articles = await database.get_articles(
        tag=tag, source=source, q=q, bookmarked=bookmarked, read=read,
        limit=limit, offset=offset,
    )
    return articles


@app.get("/api/articles/{article_id}")
async def get_article(article_id: int):
    article = await database.get_article_by_id(article_id)
    if not article:
        return JSONResponse({"error": "not found"}, status_code=404)
    return article


@app.post("/api/articles/{article_id}/bookmark")
async def toggle_bookmark(article_id: int):
    state = await database.toggle_bookmark(article_id)
    return {"id": article_id, "is_bookmarked": state}


@app.post("/api/articles/{article_id}/read")
async def mark_read_endpoint(article_id: int, is_read: bool = True):
    await database.mark_read(article_id, is_read)
    return {"id": article_id, "is_read": is_read}


@app.get("/api/bookmarks")
async def get_bookmarks():
    articles = await database.get_articles(bookmarked=True, limit=500)
    return articles


@app.get("/api/sources")
async def get_sources():
    statuses = await database.get_source_statuses()
    return statuses


@app.post("/api/trigger-update")
async def trigger_update():
    # Run in background so request doesn't hang
    asyncio.create_task(scheduler.run_update(manual=True))
    return {"success": True, "message": "Update triggered"}


@app.get("/api/events")
async def events(request: Request):
    queue: asyncio.Queue = asyncio.Queue()

    async def callback(event: str, payload: dict):
        await queue.put((event, payload))

    scheduler.register_event_callback(callback)

    async def stream() -> AsyncGenerator[str, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event, payload = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: {event}\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'time': datetime.datetime.now(datetime.timezone.utc).isoformat()})}\n\n"
        finally:
            try:
                scheduler.event_callbacks.remove(callback)
            except ValueError:
                pass

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/export")
async def export_md(req: ExportRequest):
    content = req.content
    safe_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    today = datetime.date.today().isoformat()
    filename = f"daily-digest-{today}.md"

    base = settings.resolved_obsidian_vault_path.resolve()
    if req.vault_path:
        requested = Path(req.vault_path).expanduser()
        # Reject absolute paths that escape base; relative paths are resolved under base
        if requested.is_absolute():
            vault_path = requested
        else:
            vault_path = base / requested
    else:
        vault_path = base

    resolved = vault_path.resolve()
    if not resolved.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid vault path: must be under configured vault")

    vault_path.mkdir(parents=True, exist_ok=True)
    filepath = vault_path / filename

    with open(filepath, "w") as f:
        f.write(safe_content)
    return {"success": True, "file": str(filepath)}


@app.get("/health")
async def health_check():
    try:
        statuses = await database.get_source_statuses()
        db_ok = True
    except Exception as e:
        statuses = []
        db_ok = False
    return {
        "status": "online",
        "version": "4.0.0",
        "engine": "FastAPI/Uvicorn",
        "database_ok": db_ok,
        "sources": len(statuses),
        "scheduler_running": scheduler.scheduler.running,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
