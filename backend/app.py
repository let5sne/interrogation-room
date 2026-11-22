from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from session_store import SessionStore
from cases.case_001 import get_case
from prompt_builder import PromptBuilder
from llm_client import LLMClient, LLMError
from truth_engine import TruthEngine
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


class InterrogateRequest(BaseModel):
    session_id: str
    text: str


@app.post("/api/interrogate")
def interrogate(req: InterrogateRequest):
    s = _store.get(req.session_id)
    if s is None:
        return {"error": "session not found"}
    case = get_case(s["case_id"])
    pb = PromptBuilder(case)
    llm = LLMClient()

    def gen():
        # 先用「历史 + 本回合输入」组装提示（此时 transcript 尚未含本回合输入，避免重复）
        system = pb.build_system(state=s["state"])
        user = pb.build_turn(state=s["state"], player_input=req.text)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        full = []
        try:
            for delta in llm.stream(messages):
                full.append(delta)
                yield delta
        except LLMError:
            yield "（嫌疑人沉默不语，请重试）"
        # 收尾：把本回合「玩家输入 + 嫌疑人回复」写入 transcript，更新回合数
        reply = "".join(full) or "（沉默）"
        s["state"]["transcript"].append({"role": "detective", "text": req.text})
        s["state"]["transcript"].append({"role": "suspect", "text": reply})
        s["turn_count"] += 1
        _store.update(
            s["session_id"],
            turn_count=s["turn_count"],
            state=s["state"],
        )

    return StreamingResponse(gen(), media_type="text/event-stream")


class PresentRequest(BaseModel):
    session_id: str
    lie_id: str | None = None
    evidence_id: str


@app.post("/api/present")
def present(req: PresentRequest):
    s = _store.get(req.session_id)
    if s is None:
        return {"error": "session not found"}
    case = get_case(s["case_id"])
    eng = TruthEngine(case)
    res = eng.present_evidence(req.lie_id, s["state"], req.evidence_id)
    if res["hit"]:
        new_comp = eng.clamp(s["composure"] + res["composure_delta"])
        s["state"]["contradictions"].append(
            {"evidence": req.evidence_id, "note": res["contradiction"]}
        )
        _store.update(s["session_id"], composure=new_comp, state=s["state"])
        return {"hit": True, "composure": new_comp, "message": res["contradiction"]}
    return {"hit": False, "composure": s["composure"], "message": "这条证据没能戳中矛盾。"}


class AccuseRequest(BaseModel):
    session_id: str
    culprit: str
    method: str
    motive: str


@app.post("/api/accuse")
def accuse(req: AccuseRequest):
    s = _store.get(req.session_id)
    if s is None:
        return {"error": "session not found"}
    case = get_case(s["case_id"])
    eng = TruthEngine(case)
    res = eng.judge({
        "culprit": req.culprit,
        "method": req.method,
        "motive": req.motive,
    })
    new_status = "won" if res["win"] else "lost"
    s["state"]["accusation"] = {
        "culprit": req.culprit, "method": req.method, "motive": req.motive,
    }
    _store.update(s["session_id"], status=new_status, state=s["state"])
    return {
        "win": res["win"],
        "ending": res["ending"],
        "reason": res["reason"],
        "truth": {
            "culprit": case["culprit"],
            "method": case["method"],
            "motive": case["motive"],
        },
    }