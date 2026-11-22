from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Interrogation Room")

WEB_DIR = Path(__file__).parent / "web"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


# 静态资源（css/js）
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")