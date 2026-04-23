from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="CyberSec Intel API")

# Define the path to your dashboard folder
DASHBOARD_PATH = "/home/cqrtp/.openclaw/workspace/cybersec_dashboard_server"

# Serve the static files (CSS, JS, Images)
app.mount("/static", StaticFiles(directory=DASHBOARD_PATH), name="static")

@app.get("/")
async def read_index():
    """Serves the main dashboard HTML file."""
    return FileResponse(os.path.join(DASHBOARD_PATH, "index.html"))

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "online", "version": "1.0.0", "engine": "FastAPI/Uvicorn"}

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 to allow access from the local network
    uvicorn.run(app, host="0.0.0.0", port=8080)
