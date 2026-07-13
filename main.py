import asyncio
import os
import re
import json
import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings
from dashboard_config import settings_to_config
from scheduler import create_scheduler
from models import ExportRequest
from repositories import SQLiteArticleRepository


base_dir = Path(__file__).parent

security = HTTPBearer(auto_error=False)


def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not config.api_key:
        raise HTTPException(status_code=403, detail="State-changing endpoint disabled: no API_KEY configured")
    token = (credentials.credentials if credentials else "").strip()
    if not token or token != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not getattr(app.state, "scheduler", None):
        app.state.scheduler = create_scheduler()
    await app.state.scheduler.ingestion.repository.init_db()
    app.state.scheduler.start()
    yield
    app.state.scheduler.shutdown()


app = FastAPI(
    title="News Dashboard",
    version="4.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

config = settings_to_config(settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Unprocessable Entity", "detail": "Request validation failed"},
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self';"
    )
    return response

# Static
app.mount("/static", StaticFiles(directory=base_dir / "static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse(base_dir / "static" / "index.html")


def _get_repo():
    return app.state.scheduler.ingestion.repository


@app.get("/api/news")
async def get_news():
    repo = _get_repo()
    digest = await repo.build_digest()
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
    repo = _get_repo()
    articles = await repo.get_articles(
        tag=tag, source=source, q=q, bookmarked=bookmarked, read=read,
        limit=limit, offset=offset,
    )
    return articles


@app.get("/api/articles/{article_id}")
async def get_article(article_id: int):
    repo = _get_repo()
    article = await repo.get_article_by_id(article_id)
    if not article:
        return JSONResponse({"error": "not found"}, status_code=404)
    return article


@app.post("/api/articles/{article_id}/bookmark", dependencies=[Depends(require_api_key)])
async def toggle_bookmark(article_id: int):
    repo = _get_repo()
    state = await repo.toggle_bookmark(article_id)
    return {"id": article_id, "is_bookmarked": state}


@app.post("/api/articles/{article_id}/read", dependencies=[Depends(require_api_key)])
async def mark_read_endpoint(article_id: int, is_read: bool = True):
    repo = _get_repo()
    await repo.mark_read(article_id, is_read)
    return {"id": article_id, "is_read": is_read}


@app.get("/api/bookmarks")
async def get_bookmarks():
    repo = _get_repo()
    articles = await repo.get_articles(bookmarked=True, limit=500)
    return articles


@app.get("/api/sources")
async def get_sources():
    repo = _get_repo()
    statuses = await repo.get_source_statuses()
    return statuses


@app.post("/api/trigger-update", dependencies=[Depends(require_api_key)])
async def trigger_update():
    asyncio.create_task(app.state.scheduler.run_update(manual=True))
    return {"success": True, "message": "Update triggered"}


@app.get("/api/events")
async def events(request: Request):
    queue: asyncio.Queue = asyncio.Queue()

    async def callback(event: str, payload: dict):
        await queue.put((event, payload))

    app.state.scheduler.register_event_callback(callback)

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
                app.state.scheduler.event_callbacks.remove(callback)
            except ValueError:
                pass

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/export", dependencies=[Depends(require_api_key)])
async def export_md(req: ExportRequest):
    content = req.content
    safe_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    today = datetime.date.today().isoformat()
    filename = f"daily-digest-{today}.md"

    base = config.resolved_obsidian_vault_path.resolve()
    if req.vault_path:
        requested = Path(req.vault_path).expanduser()
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
    repo = _get_repo()
    try:
        statuses = await repo.get_source_statuses()
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
        "scheduler_running": app.state.scheduler.scheduler.running,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
