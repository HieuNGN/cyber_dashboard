from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import json
import datetime

base_dir = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Intel Dashboard")

# Static files (HTML, CSS, JS, assets)
app.mount("/static", StaticFiles(directory=base_dir), name="static")

data_dir = os.path.join(base_dir, "data")
data_file = os.path.join(data_dir, "news.json")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(base_dir, "index.html"))

@app.get("/api/news")
async def get_news():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return JSONResponse(json.load(f))
    return JSONResponse(content={"items": [], "last_updated": "", "error": "No news data found"})

@app.get("/health")
async def health_check():
    return {"status": "online", "version": "2.0.0", "engine": "FastAPI/Uvicorn"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
