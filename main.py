from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import datetime

base_dir = os.path.dirname(os.path.abspath(__file__))
obsidian_vault = os.path.expanduser("~/Documents/Obsidian Vault")

app = FastAPI(title="News Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static
app.mount("/static", StaticFiles(directory=base_dir), name="static")

data_file = os.path.join(base_dir, "data", "news.json")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(base_dir, "index.html"))

@app.get("/api/news")
async def get_news():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return JSONResponse(json.load(f))
    return JSONResponse(content={"today": {"date": "", "items": []}, "yesterday": {"date": "", "items": []}})

@app.post("/api/export")
async def export_md(req: dict):
    content = req.get("content", "")
    import re
    safe_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    today = datetime.date.today().isoformat()
    filename = f"daily-digest-{today}.md"
    os.makedirs(obsidian_vault, exist_ok=True)
    filepath = os.path.join(obsidian_vault, filename)
    with open(filepath, "w") as f:
        f.write(safe_content)
    return {"success": True, "file": filepath}

@app.get("/health")
async def health_check():
    return {"status": "online", "version": "3.0.0", "engine": "FastAPI/Uvicorn"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
