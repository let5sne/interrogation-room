from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from session_store import SessionStore
from cases.case_001 import get_case
import settings

app = FastAPI(title="Interrogation Room")

_store = SessionStore(settings.DB_PATH)

WEB_DIR = Path(__file__).parent / "web"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


# 静态资源（css/js）
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class SessionRequest(BaseModel):
    case_id: str = "case_001"


def _public_evidence(case: dict):
    return [
        {"id": e["id"], "name": e["name"], "detail": e["detail"]}
        for e in case["evidence"]
    ]


@app.post("/api/session")
def create_session(req: SessionRequest):
    case = get_case(req.case_id)
    if case is None:
        return {"error": "case not found"}
    s = _store.create(case["case_id"])
    return {
        "session_id": s["session_id"],
        "title": case["title"],
        "brief": case["brief"],
        "suspect_name": case["suspect_name"],
        "composure": s["composure"],
        "evidence": _public_evidence(case),
    }