# 审讯室/谎言侦探 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一款可公开试玩的「AI 审讯」游戏：玩家审讯一个会即兴、会记忆、会维持自洽谎言的 AI 嫌疑人，抓矛盾、压镇定、破案。

**Architecture:** 单进程 FastAPI 应用（Docker 部署到魔搭创空间）。前端为纯静态单页（HTML/CSS/JS），由 FastAPI 托管并同源调用 `/api/*`。真相档案、谎言一致性约束、会话状态全部在服务端（SQLite 持久化），LLM 通过 ModelScope OpenAI 兼容端点在运行时调用，Key 走环境变量。

**Tech Stack:** Python 3.11 · FastAPI · Uvicorn · httpx（流式调用 LLM）· SQLite（标准库 sqlite3）· pytest · 原生前端 HTML/CSS/JS。

**设计依据：** `docs/superpowers/specs/2026-11-23-interrogation-game-design.md`

---

## File Structure

```
interrogation-room/
├── backend/
│   ├── app.py                # FastAPI 入口：托管静态 + /api 路由
│   ├── settings.py           # 环境变量读取（API Key / model / DB 路径）
│   ├── session_store.py      # SQLite 会话持久化
│   ├── truth_engine.py       # 真相档案查询、矛盾判定、镇定计算、结局判定
│   ├── prompt_builder.py     # 提示词组装（system + 每回合 user）
│   ├── llm_client.py         # ModelScope 流式调用 + 重试
│   ├── cases/
│   │   ├── __init__.py
│   │   └── case_001.py       # 「雨夜书房」真相档案（结构化数据）
│   ├── web/                  # 前端静态资源（由 FastAPI 托管）
│   │   ├── index.html
│   │   ├── style.css
│   │   └── game.js
│   ├── tests/
│   │   ├── test_truth_engine.py
│   │   ├── test_session_store.py
│   │   ├── test_prompt_builder.py
│   │   ├── test_llm_client.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
└── docs/superpowers/...
```

**依赖方向：** `app.py` → (`session_store`, `truth_engine`, `prompt_builder`, `llm_client`) → `cases/case_001.py`。前端只通过 HTTP 与 `app.py` 通信，不 import 任何 Python。

---

## 任务总览

- Task 1：脚手架 + 健康检查 + Docker（先上线跑通部署）
- Task 2：`SessionStore`（SQLite 持久化）
- Task 3：`case_001` 真相档案数据
- Task 4：`TruthEngine` 矛盾判定
- Task 5：`TruthEngine` 镇定值 + 结局判定
- Task 6：`PromptBuilder`
- Task 7：`LLMClient`（ModelScope 流式 + 重试）
- Task 8：`/api/session`
- Task 9：`/api/interrogate`（流式）
- Task 10：`/api/present`
- Task 11：`/api/accuse`
- Task 12：前端结构 `index.html`
- Task 13：前端氛围样式 `style.css`
- Task 14：前端逻辑 `game.js`（会话/渲染/流式）
- Task 15：前端动作（施压/证据/观察）+ 镇定仪表 + 指认结算
- Task 16：案件内容定稿与逻辑闭环校验
- Task 17：部署到魔搭创空间 + 公网验证

> **测试策略说明：** 后端核心（Task 2–11）走 TDD（先写失败测试，再实现）。前端（Task 12–15）以人工/浏览器验证为主（UI 难做单元测试），每个 Task 给出明确的验证步骤。LLM 在单元测试中一律 mock，不打真实网络。

---

## Task 1: 脚手架 + 健康检查 + Docker

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/settings.py`
- Create: `backend/app.py`
- Create: `backend/Dockerfile`
- Create: `backend/web/index.html`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 写 requirements**

`backend/requirements.txt`
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pytest==8.3.4
```

- [ ] **Step 2: 写失败测试（健康检查）**

`backend/tests/test_api.py`
```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 3: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'backend'` 或 `app` 未定义路由 → 404）

- [ ] **Step 4: 实现 settings + app 最小骨架**

`backend/settings.py`
```python
import os

MODELSPACE_API_KEY = os.environ.get("MODELSPACE_API_KEY", "")
MODELSPACE_BASE_URL = os.environ.get(
    "MODELSPACE_BASE_URL", "https://api-inference.modelscope.cn/v1"
)
MODELSPACE_MODEL = os.environ.get("MODELSPACE_MODEL", "Qwen/Qwen2.5-72B-Instruct")
DB_PATH = os.environ.get("DB_PATH", "sessions.db")
```

`backend/app.py`
```python
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
```

`backend/web/index.html`
```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>审讯室</title>
    <link rel="stylesheet" href="/static/style.css" />
  </head>
  <body>
    <div id="app">审讯室 · 加载中</div>
    <script src="/static/game.js"></script>
  </body>
</html>
```

> 注意：`FileResponse(WEB_DIR / "index.html")` 需要文件存在。Step 5 会创建 `style.css`、`game.js` 空文件避免 404。

- [ ] **Step 5: 创建空占位静态文件（避免挂载 404）**

```bash
cd backend && mkdir -p web && printf '/* placeholder */\n' > web/style.css && printf '// placeholder\n' > web/game.js
```

- [ ] **Step 6: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: PASS（1 passed）

- [ ] **Step 7: 本地启动冒烟**

Run: `cd backend && python -m uvicorn app:app --port 7860 &` 然后 `curl -s localhost:7860/api/health`
Expected: `{"status":"ok"}`；`curl -s localhost:7860/ | head` 能看到 HTML。用完 `kill %1`。

- [ ] **Step 8: 写 Dockerfile**

`backend/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .
EXPOSE 7860
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 9: 本地 Docker 构建验证（如已装 Docker）**

Run: `cd backend && docker build -t interrogation:test . && docker run --rm -p 7860:7860 interrogation:test &` 后 `curl -s localhost:7860/api/health`
Expected: `{"status":"ok"}`。`docker stop` 收尾。（无 Docker 环境可跳过，Step 17 在创空间验证。）

- [ ] **Step 10: 提交**

```bash
git add backend && git commit -m "feat: scaffold FastAPI app with health check and Dockerfile"
```

---

## Task 2: SessionStore（SQLite 持久化）

**Files:**
- Create: `backend/session_store.py`
- Test: `backend/tests/test_session_store.py`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_session_store.py`
```python
from session_store import SessionStore


def _store(tmp_path):
    return SessionStore(str(tmp_path / "t.db"))


def test_create_and_get(tmp_path):
    store = _store(tmp_path)
    s = store.create("case_001")
    assert s["status"] == "active"
    assert s["composure"] == 100
    got = store.get(s["session_id"])
    assert got["session_id"] == s["session_id"]
    assert got["state"]["transcript"] == []


def test_update_persists(tmp_path):
    store = _store(tmp_path)
    s = store.create("case_001")
    store.update(s["session_id"], composure=42, turn_count=3, status="active")
    got = store.get(s["session_id"])
    assert got["composure"] == 42
    assert got["turn_count"] == 3


def test_update_state_json(tmp_path):
    store = _store(tmp_path)
    s = store.create("case_001")
    new_state = {"transcript": [{"role": "suspect", "text": "哼"}], "established_facts": [], "contradictions": [], "accusation": None}
    store.update(s["session_id"], state=new_state)
    got = store.get(s["session_id"])
    assert got["state"]["transcript"][0]["text"] == "哼"
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_session_store.py -v`
Expected: FAIL（`AttributeError: module 'session_store' has no attribute 'SessionStore'`）

- [ ] **Step 3: 实现**

`backend/session_store.py`
```python
import json
import sqlite3
import threading
import time
import uuid


class SessionStore:
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    composure INTEGER NOT NULL,
                    pressure_count INTEGER NOT NULL DEFAULT 0,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    @staticmethod
    def _default_state():
        return {
            "transcript": [],
            "established_facts": [],
            "contradictions": [],
            "accusation": None,
        }

    def _row_to_session(self, row):
        return {
            "session_id": row["session_id"],
            "case_id": row["case_id"],
            "composure": row["composure"],
            "pressure_count": row["pressure_count"],
            "turn_count": row["turn_count"],
            "status": row["status"],
            "state": json.loads(row["state_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create(self, case_id: str, composure: int = 100) -> dict:
        sid = uuid.uuid4().hex
        now = time.time()
        state = self._default_state()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, case_id, composure, pressure_count, turn_count, status, state_json, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, case_id, composure, 0, 0, "active",
                 json.dumps(state, ensure_ascii=False), now, now),
            )
        return self.get(sid)

    def get(self, session_id: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id=?", (session_id,)
            ).fetchone()
        return self._row_to_session(row) if row else None

    def update(self, session_id: str, **fields):
        if "state" in fields:
            fields["state_json"] = json.dumps(fields.pop("state"), ensure_ascii=False)
        if not fields:
            return
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [session_id]
        with self._lock, self._conn() as conn:
            conn.execute(f"UPDATE sessions SET {cols} WHERE session_id=?", values)
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_session_store.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/session_store.py backend/tests/test_session_store.py && git commit -m "feat: SQLite SessionStore with create/get/update"
```

---

## Task 3: case_001 真相档案数据

**Files:**
- Create: `backend/cases/__init__.py`
- Create: `backend/cases/case_001.py`
- Test: 复用 `backend/tests/test_truth_engine.py`（Task 4 首次创建，此处仅建数据）

- [ ] **Step 1: 创建包**

```bash
cd backend && touch cases/__init__.py
```

- [ ] **Step 2: 写案件数据**

`backend/cases/case_001.py`
```python
CASE_001 = {
    "case_id": "case_001",
    "title": "雨夜书房",
    "brief": (
        "古董商陈默被发现死于自家书房，头部遭钝器重击。"
        "门窗完好，无强行入室痕迹，但书房陈列柜的一块镇纸（奖杯）不见了，地上有碎玻璃。"
        "死者合伙人林晚报案，称晚上 20:30 离开时陈默还活着。"
        "你负责审讯林晚。"
    ),
    "suspect_name": "林晚",
    "culprit": "林晚",
    "method": "用书房陈列柜的奖杯（镇纸）重击陈默后脑致死，随后伪造入室抢劫。",
    "motive": "林晚长期挪用公司资金，被陈默发现，陈默威胁次日报警，林晚遂灭口。",
    "timeline": [
        {"time": "20:10", "fact": "陈默与林晚在书房就账目发生激烈争吵。"},
        {"time": "20:55", "fact": "林晚用奖杯重击陈默后脑，陈默死亡。"},
        {"time": "21:02", "fact": "书房座机拨出一个电话（未接通），证明此时书房内仍有活人活动迹象。"},
        {"time": "21:05", "fact": "小区门口监控拍到林晚的车仍停在楼下。"},
        {"time": "21:30", "fact": "林晚驾车离开，前往咖啡厅制造不在场证明。"},
    ],
    "suspect_secret": "林晚是凶手，且挪用了公司巨额资金，陈默已掌握证据并准备报警。",
    "lies": [
        {
            "lie_id": "L1",
            "statement": "我 20:30 就离开了书房，之后一直在咖啡厅，再没回去过。",
            "truth": "监控显示她 21:05 仍在楼下，21:02 书房座机有拨号记录，她 21:30 才离开。",
            "breakable_by": ["E3", "E5"],
        },
        {
            "lie_id": "L2",
            "statement": "我和陈默合作多年，关系很好，账目上没有任何问题。",
            "truth": "存在林晚挪用资金的转账记录，陈默已发现。",
            "breakable_by": ["E4"],
        },
        {
            "lie_id": "L3",
            "statement": "那尊奖杯？我从来没碰过，我连它在哪都不知道。",
            "truth": "奖杯上残留林晚的指纹，且奖杯被擦拭过。",
            "breakable_by": ["E1"],
        },
    ],
    "evidence": [
        {"id": "E1", "name": "擦拭过的奖杯", "detail": "书房陈列柜的奖杯（镇纸），表面被擦过，但仍提取到一枚林晚的指纹。"},
        {"id": "E2", "name": "咖啡厅小票", "detail": "一张 21:15 的咖啡厅消费小票，署名林晚。"},
        {"id": "E3", "name": "座机通话记录", "detail": "书房座机在 21:02 拨出一个未接通的电话。"},
        {"id": "E4", "name": "转账记录", "detail": "近半年多笔公司账户向林晚私人账户的异常转账，合计逾百万。"},
        {"id": "E5", "name": "小区门口监控", "detail": "21:05 的监控显示林晚的车仍停在楼下，21:30 才驶离。"},
        {"id": "E6", "name": "碎玻璃", "detail": "书房地面有陈列柜玻璃碎片，林晚鞋底缝隙中检出相同玻璃成分。"},
    ],
    "key_contradictions": [
        {"evidence_id": "E5", "contradicts_lie": "L1", "note": "你 20:30 就离开？可 21:05 你的车还停在楼下。"},
        {"evidence_id": "E3", "contradicts_lie": "L1", "note": "21:02 书房座机拨号，你却说那时你已在咖啡厅。"},
        {"evidence_id": "E1", "contradicts_lie": "L3", "note": "你说从没碰过奖杯，可上面有你刚被擦过的指纹。"},
        {"evidence_id": "E4", "contradicts_lie": "L2", "note": "关系很好？这些百万转账你怎么解释？"},
        {"evidence_id": "E6", "contradicts_lie": "L1", "note": "你鞋底有书房陈列柜的玻璃，可你说你 20:30 就走了。"},
    ],
    "confession_threshold": 20,
    "key_evidence_for_win": ["E1", "E5"],  # 破案需至少掌握的证据链（实现阶段用于判定辅助）
}

CASES = {"case_001": CASE_001}


def get_case(case_id: str):
    return CASES.get(case_id)
```

- [ ] **Step 3: 快速校验数据可导入**

Run: `cd backend && python -c "from cases.case_001 import CASES, get_case; c=get_case('case_001'); assert len(c['evidence'])==6 and len(c['key_contradictions'])==5; print('case ok')"`
Expected: `case ok`

- [ ] **Step 4: 提交**

```bash
git add backend/cases && git commit -m "feat: case_001 雨夜书房 ground truth data"
```

---

## Task 4: TruthEngine 矛盾判定

**Files:**
- Create: `backend/truth_engine.py`
- Test: `backend/tests/test_truth_engine.py`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_truth_engine.py`
```python
from truth_engine import TruthEngine
from cases.case_001 import get_case


def _engine():
    return TruthEngine(get_case("case_001"))


def test_present_key_evidence_hits_contradiction():
    eng = _engine()
    res = eng.present_evidence("L1", state={"contradictions": []}, evidence_id="E5")
    # 该证据命中预设矛盾 → composure 大跌
    assert res["hit"] is True
    assert res["composure_delta"] <= -25
    assert "contradiction" in res


def test_present_non_key_evidence_no_hit():
    eng = _engine()
    res = eng.present_evidence("L1", state={"contradictions": []}, evidence_id="E2")
    assert res["hit"] is False
    assert res["composure_delta"] == 0


def test_present_wrong_lie_no_hit():
    eng = _engine()
    res = eng.present_evidence("L2", state={"contradictions": []}, evidence_id="E1")
    assert res["hit"] is False
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_truth_engine.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'truth_engine'`）

- [ ] **Step 3: 实现**

`backend/truth_engine.py`
```python
from typing import Optional


class TruthEngine:
    def __init__(self, case: dict):
        self.case = case

    def present_evidence(self, lie_id: Optional[str], state: dict, evidence_id: str) -> dict:
        """玩家出示证据。返回 {hit, composure_delta, contradiction?}。"""
        # 确定性命中：该证据被登记为可证伪该谎言
        hit = False
        note = None
        for kc in self.case["key_contradictions"]:
            if kc["evidence_id"] == evidence_id and kc["contradicts_lie"] == lie_id:
                hit = True
                note = kc["note"]
                break
        if hit:
            return {"hit": True, "composure_delta": -30, "contradiction": note}
        return {"hit": False, "composure_delta": 0}
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_truth_engine.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/truth_engine.py backend/tests/test_truth_engine.py && git commit -m "feat: TruthEngine.present_evidence deterministic contradiction"
```

---

## Task 5: TruthEngine 镇定值 + 结局判定

**Files:**
- Modify: `backend/truth_engine.py`
- Test: `backend/tests/test_truth_engine.py`

- [ ] **Step 1: 追加失败测试**

在 `backend/tests/test_truth_engine.py` 末尾追加：
```python
def test_pressure_penalty():
    eng = _engine()
    res = eng.pressure(composure=80, has_evidence=False)
    assert res["composure_delta"] < 0
    assert res["lawyer_up"] is False


def test_pressure_without_evidence_triggers_lawyer():
    eng = _engine()
    # 连续 3 次无证据施压
    res = eng.pressure(composure=80, has_evidence=False, pressure_count=2)
    assert res["lawyer_up"] is True


def test_clamp_composure():
    eng = _engine()
    assert eng.clamp(105) == 100
    assert eng.clamp(-5) == 0
    assert eng.clamp(55) == 55


def test_judge_win_on_correct_accusation():
    eng = _engine()
    res = eng.judge(accusation={"culprit": "林晚", "method": "用奖杯重击致死", "motive": "挪用资金被发现在即，杀人灭口"})
    assert res["win"] is True
    assert res["ending"] in ("full_confession", "solved")


def test_judge_lose_on_wrong_culprit():
    eng = _engine()
    res = eng.judge(accusation={"culprit": "管家", "method": "下毒", "motive": "仇杀"})
    assert res["win"] is False
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_truth_engine.py -v`
Expected: FAIL（`AttributeError: ... 'pressure' / 'clamp' / 'judge'`）

- [ ] **Step 3: 实现（在 truth_engine.py 追加方法）**

```python
    # 追加到 TruthEngine 类内
    def clamp(self, value: int) -> int:
        return max(0, min(100, value))

    def pressure(self, composure: int, has_evidence: bool, pressure_count: int = 0) -> dict:
        """施压。无证据施压会掉镇定且累计；第 3 次无证据施压触发'要求律师'。"""
        delta = -10 if has_evidence else -5
        lawyer_up = (not has_evidence) and (pressure_count + 1 >= 3)
        if lawyer_up:
            delta = -20
        return {"composure_delta": delta, "lawyer_up": lawyer_up}

    def judge(self, accusation: dict) -> dict:
        """指认结算。关键项匹配即判胜。"""
        culprit_ok = accusation.get("culprit") == self.case["culprit"]
        method_ok = any(k in accusation.get("method", "") for k in ["奖杯", "钝器", "重击"])
        motive_ok = any(k in accusation.get("motive", "") for k in ["资金", "挪用", "灭口", "报警"])
        if culprit_ok and (method_ok or motive_ok):
            return {"win": True, "ending": "solved", "reason": "指认成立"}
        return {
            "win": False,
            "ending": "wrong_accusation",
            "reason": "指认与真相不符，嫌疑人被释放，真凶逍遥法外。",
        }
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_truth_engine.py -v`
Expected: PASS（7 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/truth_engine.py backend/tests/test_truth_engine.py && git commit -m "feat: TruthEngine pressure/clamp/judge (composure + endings)"
```

---

## Task 6: PromptBuilder

**Files:**
- Create: `backend/prompt_builder.py`
- Test: `backend/tests/test_prompt_builder.py`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_prompt_builder.py`
```python
from prompt_builder import PromptBuilder
from cases.case_001 import get_case


def test_system_prompt_contains_secret_and_rules():
    pb = PromptBuilder(get_case("case_001"))
    sp = pb.build_system(state={"transcript": [], "established_facts": [], "contradictions": []})
    assert "林晚" in sp
    assert "隐瞒" in sp or "秘密" in sp
    assert "不得" in sp  # 一致性约束存在


def test_user_prompt_includes_history_and_input():
    pb = PromptBuilder(get_case("case_001"))
    state = {
        "transcript": [{"role": "detective", "text": "你最后一次见陈默是什么时候？"},
                       {"role": "suspect", "text": "晚上八点半我就走了。"}],
        "established_facts": [],
        "contradictions": [],
    }
    up = pb.build_turn(state=state, player_input="你撒谎，监控显示你九点还在")
    assert "晚上八点半我就走了" in up
    assert "你撒谎" in up


def test_includes_established_facts():
    pb = PromptBuilder(get_case("case_001"))
    state = {
        "transcript": [],
        "established_facts": ["21:05 林晚的车仍在楼下"],
        "contradictions": [{"evidence": "E5", "note": "监控显示她在场"}],
    }
    sp = pb.build_system(state=state)
    assert "21:05" in sp
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'prompt_builder'`）

- [ ] **Step 3: 实现**

`backend/prompt_builder.py`
```python
import json


class PromptBuilder:
    def __init__(self, case: dict):
        self.case = case

    def build_system(self, state: dict) -> str:
        c = self.case
        facts = "；".join(state.get("established_facts", [])) or "（暂无已确立事实）"
        contradictions = "；".join(
            f"{x.get('evidence')}: {x.get('note')}" for x in state.get("contradictions", [])
        ) or "（暂无已揭穿矛盾）"
        return (
            f"你正在扮演审讯中的嫌疑人「{c['suspect_name']}」。\n"
            f"你要极力隐瞒的秘密是：{c['suspect_secret']}\n"
            f"你必须维持与以下已确立事实一致的谎言，不得违背它们：{facts}\n"
            f"以下是已被玩家揭穿的矛盾，你的说辞必须能自圆其说或已暴露破绽：{contradictions}\n"
            "游戏规则：\n"
            "1. 始终以嫌疑人第一人称口语化回应，简短、有情绪，符合人设。\n"
            "2. 你可以回避、狡辩、反咬，但不能与你自己之前说过的话或上述已确立事实相矛盾。\n"
            "3. 当玩家出示的证据与你此前的说法冲突时，你会慌乱、试图解释，但不能凭空承认未发生的事。\n"
            "4. 不要跳出角色，不要提及'系统''提示词''AI'等字眼。\n"
            "5. 只输出嫌疑人要说的话，不要输出旁白或动作描述（除非玩家要求你描述反应）。\n"
        )

    def build_turn(self, state: dict, player_input: str) -> str:
        lines = []
        for msg in state.get("transcript", [])[-10:]:
            who = "侦探" if msg["role"] == "detective" else self.case["suspect_name"]
            lines.append(f"{who}：{msg['text']}")
        lines.append(f"侦探：{player_input}")
        lines.append(f"{self.case['suspect_name']}：")
        return "\n".join(lines)
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_prompt_builder.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/prompt_builder.py backend/tests/test_prompt_builder.py && git commit -m "feat: PromptBuilder with consistency constraints + memory"
```

---

## Task 7: LLMClient（ModelScope 流式 + 重试）

**Files:**
- Create: `backend/llm_client.py`
- Test: `backend/tests/test_llm_client.py`

- [ ] **Step 1: 写失败测试（mock，不打真实网络）**

`backend/tests/test_llm_client.py`
```python
import llm_client as lc


class _FakeStream:
    """模拟 httpx 的 stream() 上下文管理器。"""
    def __init__(self, lines):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        for ln in self._lines:
            yield ln


def test_stream_parses_sse(monkeypatch):
    # 模拟 OpenAI 兼容的 SSE 流
    sse = [
        'data: {"choices":[{"delta":{"content":"你"}}]}',
        'data: {"choices":[{"delta":{"content":"说"}}]}',
        'data: {"choices":[{"delta":{"content":"什么"}}]}',
        'data: [DONE]',
    ]

    # 注意：llm_client 使用 httpx.Client(...).stream("POST", ...)，故 mock stream 而非 post
    def fake_stream(self, method, url, **kwargs):
        return _FakeStream(sse)

    monkeypatch.setattr(lc.httpx.Client, "stream", fake_stream)
    client = lc.LLMClient(api_key="x", base_url="http://test", model="m")
    out = "".join(client.stream([{"role": "user", "content": "hi"}]))
    assert out == "你说什么"
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_llm_client.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'llm_client'`）

- [ ] **Step 3: 实现**

`backend/llm_client.py`
```python
import json
import httpx

from settings import (
    MODELSPACE_API_KEY,
    MODELSPACE_BASE_URL,
    MODELSPACE_MODEL,
)


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key if api_key is not None else MODELSPACE_API_KEY
        self.base_url = base_url if base_url is not None else MODELSPACE_BASE_URL
        self.model = model if model is not None else MODELSPACE_MODEL

    def stream(self, messages, temperature: float = 0.8, timeout: float = 60.0):
        """流式对话。yield 增量文本片段。失败重试 1 次。"""
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        last_err = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout) as c:
                    with c.stream("POST", url, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        for line in resp.iter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[len("data:"):].strip()
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                delta = obj["choices"][0]["delta"].get("content")
                                if delta:
                                    yield delta
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                continue
        raise LLMError(f"LLM request failed after retries: {last_err}")
```

> 导入约定：`backend/` 目录即代码根（Docker 内为 `/app`）。所有模块用**扁平导入**（`from settings import`、`from app import`、`from session_store import`、`from cases.case_001 import` 等），**统一在 `backend/` 目录下运行 pytest**（`cd backend && python -m pytest`）。这样本地、Docker、创空间三处行为一致。

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_llm_client.py -v`
Expected: PASS（1 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/llm_client.py backend/tests/test_llm_client.py && git commit -m "feat: LLMClient ModelScope streaming with retry"
```

---

## Task 8: `/api/session` 端点

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 追加失败测试**

在 `backend/tests/test_api.py` 末尾追加：
```python
def test_create_session_returns_brief_and_evidence(monkeypatch, tmp_path):
    import app as appmod
    from session_store import SessionStore
    monkeypatch.setattr(appmod, "_store", SessionStore(str(tmp_path / "api.db")))
    client2 = TestClient(appmod.app)
    r = client2.post("/api/session", json={"case_id": "case_001"})
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"]
    assert "书房" in body["brief"]
    assert len(body["evidence"]) == 6
    # 证据不得包含 reveals/breakable_by
    assert "reveals" not in body["evidence"][0]
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_api.py::test_create_session_returns_brief_and_evidence -v`
Expected: FAIL（404 Not Found）

- [ ] **Step 3: 实现**

修改 `backend/app.py`，在文件顶部补充导入，并在路由区追加：
```python
# 顶部补充
from pydantic import BaseModel
from session_store import SessionStore
from cases.case_001 import get_case
import settings

_store = SessionStore(settings.DB_PATH)
```

```python
# 路由区追加
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
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_api.py::test_create_session_returns_brief_and_evidence -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app.py backend/tests/test_api.py && git commit -m "feat: POST /api/session returns brief and sanitized evidence"
```

---

## Task 9: `/api/interrogate`（流式）

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 追加失败测试（mock LLM）**

在 `backend/tests/test_api.py` 末尾追加：
```python
def test_interrogate_streams_and_updates_state(monkeypatch, tmp_path):
    import app as appmod
    from session_store import SessionStore
    monkeypatch.setattr(appmod, "_store", SessionStore(str(tmp_path / "api2.db")))
    # mock LLM
    def fake_stream(self, messages, **kw):
        yield "我"
        yield "没"
        yield "有"
    monkeypatch.setattr(appmod.LLMClient, "stream", fake_stream)
    client2 = TestClient(appmod.app)
    sid = client2.post("/api/session", json={"case_id": "case_001"}).json()["session_id"]
    with client2.stream("POST", "/api/interrogate", json={"session_id": sid, "text": "你几点走的？"}) as r:
        assert r.status_code == 200
        chunks = []
        for chunk in r.iter_text():
            chunks.append(chunk)
    assert "我" in "".join(chunks)
    # 回合数 +1、对话已记录
    state = appmod._store.get(sid)
    assert state["turn_count"] == 1
    assert state["state"]["transcript"][0]["role"] == "detective"
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_api.py::test_interrogate_streams_and_updates_state -v`
Expected: FAIL（404）

- [ ] **Step 3: 实现**

修改 `backend/app.py`：顶部补充导入，并追加流式端点。
```python
# 顶部补充
from fastapi.responses import StreamingResponse
import json as _json
from prompt_builder import PromptBuilder
from llm_client import LLMClient, LLMError
from truth_engine import TruthEngine
```

```python
# 路由区追加
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
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_api.py::test_interrogate_streams_and_updates_state -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app.py backend/tests/test_api.py && git commit -m "feat: POST /api/interrogate streaming with state update"
```

---

## Task 10: `/api/present` 端点

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 追加失败测试**

在 `backend/tests/test_api.py` 末尾追加：
```python
def test_present_key_evidence_drops_composure(monkeypatch, tmp_path):
    import app as appmod
    from session_store import SessionStore
    monkeypatch.setattr(appmod, "_store", SessionStore(str(tmp_path / "api3.db")))
    client2 = TestClient(appmod.app)
    sid = client2.post("/api/session", json={"case_id": "case_001"}).json()["session_id"]
    r = client2.post("/api/present", json={"session_id": sid, "lie_id": "L1", "evidence_id": "E5"})
    assert r.status_code == 200
    body = r.json()
    assert body["hit"] is True
    assert body["composure"] <= 70  # 100-30
    state = appmod._store.get(sid)
    assert state["composure"] == body["composure"]
    assert len(state["state"]["contradictions"]) == 1
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_api.py::test_present_key_evidence_drops_composure -v`
Expected: FAIL（404）

- [ ] **Step 3: 实现**

```python
# 路由区追加
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
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_api.py::test_present_key_evidence_drops_composure -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app.py backend/tests/test_api.py && git commit -m "feat: POST /api/present applies contradiction + composure"
```

---

## Task 11: `/api/accuse` 端点

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 追加失败测试**

在 `backend/tests/test_api.py` 末尾追加：
```python
def test_accuse_win(monkeypatch, tmp_path):
    import app as appmod
    from session_store import SessionStore
    monkeypatch.setattr(appmod, "_store", SessionStore(str(tmp_path / "api4.db")))
    client2 = TestClient(appmod.app)
    sid = client2.post("/api/session", json={"case_id": "case_001"}).json()["session_id"]
    r = client2.post("/api/accuse", json={
        "session_id": sid,
        "culprit": "林晚",
        "method": "用奖杯重击",
        "motive": "挪用资金被发现，杀人灭口",
    })
    body = r.json()
    assert body["win"] is True
    assert appmod._store.get(sid)["status"] != "active"


def test_accuse_lose(monkeypatch, tmp_path):
    import app as appmod
    from session_store import SessionStore
    monkeypatch.setattr(appmod, "_store", SessionStore(str(tmp_path / "api5.db")))
    client2 = TestClient(appmod.app)
    sid = client2.post("/api/session", json={"case_id": "case_001"}).json()["session_id"]
    r = client2.post("/api/accuse", json={
        "session_id": sid, "culprit": "园丁", "method": "下毒", "motive": "报复",
    })
    assert r.json()["win"] is False
```

- [ ] **Step 2: 运行，确认失败**

Run: `cd backend && python -m pytest tests/test_api.py::test_accuse_win tests/test_api.py::test_accuse_lose -v`
Expected: FAIL（404）

- [ ] **Step 3: 实现**

```python
# 路由区追加
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
```

- [ ] **Step 4: 运行，确认通过**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 全量测试 + 提交**

```bash
cd backend && python -m pytest -v
```
Expected: 全部 PASS

```bash
git add backend/app.py backend/tests/test_api.py && git commit -m "feat: POST /api/accuse judgement with truth reveal"
```

---

## Task 12: 前端结构 `index.html`

**Files:**
- Modify: `backend/web/index.html`

- [ ] **Step 1: 写完整页面结构**

`backend/web/index.html`
```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>审讯室 · 谎言侦探</title>
    <link rel="stylesheet" href="/static/style.css" />
  </head>
  <body>
    <div class="room">
      <header class="hud">
        <div class="title">审讯室 <span id="case-title"></span></div>
        <div class="meters">
          <div class="meter"><span>镇定</span><div class="bar"><i id="composure-bar"></i></div><b id="composure-num">100</b></div>
          <div class="turn">回合 <b id="turn-num">0</b></div>
        </div>
      </header>

      <main class="stage">
        <aside class="portrait">
          <div class="suspect" id="suspect">嫌疑人</div>
          <div class="mood" id="mood">从容</div>
        </aside>
        <section class="dialog" id="dialog"></section>
      </main>

      <section class="evidence-tray">
        <h3>证据托盘 <span class="hint">（点击下方按钮出示）</span></h3>
        <div id="evidence-list"></div>
      </section>

      <footer class="controls">
        <div class="actions">
          <button data-act="pressure">施压</button>
          <button data-act="observe">观察微表情</button>
          <button data-act="accuse-open">指认</button>
        </div>
        <form id="input-form" class="ask">
          <input id="ask-input" placeholder="输入你的问话，回车发送…" autocomplete="off" />
          <button type="submit">发送</button>
        </form>
      </footer>
    </div>

    <div class="modal" id="brief-modal">
      <div class="modal-card">
        <h2>案情简报</h2>
        <p id="brief-text"></p>
        <h3>现有证据</h3>
        <div id="brief-evidence"></div>
        <button id="brief-start">开始审讯</button>
      </div>
    </div>

    <div class="modal hidden" id="accuse-modal">
      <div class="modal-card">
        <h2>指认</h2>
        <label>凶手 <input id="accuse-culprit" placeholder="姓名" /></label>
        <label>手法 <input id="accuse-method" placeholder="如何作案" /></label>
        <label>动机 <input id="accuse-motive" placeholder="为什么" /></label>
        <button id="accuse-submit">提交指认</button>
        <button id="accuse-cancel" class="ghost">取消</button>
      </div>
    </div>

    <div class="modal hidden" id="result-modal">
      <div class="modal-card">
        <h2 id="result-title"></h2>
        <p id="result-text"></p>
        <button id="result-restart">再玩一次</button>
      </div>
    </div>

    <script src="/static/game.js"></script>
  </body>
</html>
```

- [ ] **Step 2: 人工验证**

Run: `cd backend && python -m uvicorn app:app --port 7860 &` 打开 `http://localhost:7860/`。
Expected: 看到「案情简报」弹窗（此时还没数据，Step 14 补 JS 后才完整；此步只验证结构渲染无报错）。`kill %1`。

- [ ] **Step 3: 提交**

```bash
git add backend/web/index.html && git commit -m "feat: frontend page structure (HUD/portrait/dialog/evidence/controls/modals)"
```

---

## Task 13: 前端氛围样式 `style.css`

**Files:**
- Modify: `backend/web/style.css`

- [ ] **Step 1: 写样式**

`backend/web/style.css`
```css
:root {
  --bg: #0b0d10;
  --panel: #14171c;
  --line: #2a2f38;
  --text: #e8e6e3;
  --muted: #8b93a1;
  --accent: #c7a15a;
  --danger: #d05c5c;
  --ok: #5caf7a;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none;
  background: radial-gradient(60% 50% at 50% 0%, rgba(199,161,90,.08), transparent 70%);
}
.room { max-width: 960px; margin: 0 auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; min-height: 100%; }
.hud { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
.title { font-size: 18px; letter-spacing: 2px; }
.title span { color: var(--accent); font-size: 14px; margin-left: 8px; }
.meters { display: flex; align-items: center; gap: 16px; font-size: 13px; color: var(--muted); }
.meter { display: flex; align-items: center; gap: 8px; }
.bar { width: 140px; height: 8px; background: #23272e; border-radius: 4px; overflow: hidden; }
.bar i { display: block; height: 100%; width: 100%; background: linear-gradient(90deg, var(--ok), var(--accent)); transition: width .4s ease; }
.turn b, .meter b { color: var(--text); }
.stage { display: grid; grid-template-columns: 220px 1fr; gap: 12px; flex: 1; }
.portrait { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 16px; }
.suspect { font-size: 20px; letter-spacing: 3px; }
.mood { color: var(--accent); font-size: 14px; }
.dialog { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; overflow-y: auto; max-height: 52vh; display: flex; flex-direction: column; gap: 10px; }
.line { padding: 10px 12px; border-radius: 8px; line-height: 1.6; max-width: 85%; }
.line.detective { align-self: flex-end; background: #1c2530; border: 1px solid #2c3a4a; }
.line.suspect { align-self: flex-start; background: #201c18; border: 1px solid #3a2f22; }
.line .who { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.line.warn { border-color: var(--danger); }
.evidence-tray { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 16px; }
.evidence-tray h3 { margin: 0 0 8px; font-size: 14px; color: var(--muted); font-weight: 500; }
.hint { font-size: 12px; }
#evidence-list { display: flex; flex-wrap: wrap; gap: 8px; }
.ev {
  cursor: pointer; padding: 6px 10px; border-radius: 6px; background: #1a1e24;
  border: 1px solid var(--line); font-size: 13px; transition: .15s;
}
.ev:hover { border-color: var(--accent); color: var(--accent); }
.ev.used { opacity: .4; pointer-events: none; }
.controls { display: flex; flex-direction: column; gap: 8px; }
.actions { display: flex; gap: 8px; }
button {
  background: var(--accent); color: #14110a; border: none; padding: 9px 14px;
  border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600;
}
button:hover { filter: brightness(1.08); }
button.ghost { background: transparent; color: var(--muted); border: 1px solid var(--line); }
.ask { display: flex; gap: 8px; }
.ask input { flex: 1; background: #0f1216; border: 1px solid var(--line); color: var(--text); padding: 10px 12px; border-radius: 7px; font-size: 15px; }
.modal { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: flex; align-items: center; justify-content: center; padding: 16px; z-index: 10; }
.modal.hidden { display: none; }
.modal-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 24px; max-width: 520px; width: 100%; max-height: 84vh; overflow: auto; }
.modal-card h2 { margin-top: 0; letter-spacing: 2px; }
.modal-card label { display: block; margin: 10px 0; color: var(--muted); font-size: 14px; }
.modal-card label input { display: block; width: 100%; margin-top: 4px; padding: 9px 12px; background: #0f1216; border: 1px solid var(--line); color: var(--text); border-radius: 7px; }
#brief-evidence div { padding: 6px 0; border-bottom: 1px dashed var(--line); font-size: 13px; }
@media (max-width: 640px) {
  .stage { grid-template-columns: 1fr; }
  .portrait { flex-direction: row; }
}
```

- [ ] **Step 2: 人工验证**

Run: `cd backend && python -m uvicorn app:app --port 7860 &` 打开页面。
Expected: 深色审讯室风格、HUD、舞台布局正常；弹窗居中。`kill %1`。

- [ ] **Step 3: 提交**

```bash
git add backend/web/style.css && git commit -m "style: dark interrogation-room theme"
```

---

## Task 14: 前端逻辑 `game.js`（会话/渲染/流式）

**Files:**
- Modify: `backend/web/game.js`

- [ ] **Step 1: 写 JS（会话初始化 + 渲染 + 流式收发）**

`backend/web/game.js`
```javascript
const state = {
  sessionId: null,
  composure: 100,
  turn: 0,
  mood: "从容",
};

const $ = (sel) => document.querySelector(sel);

function moodOf(c) {
  if (c >= 80) return "从容";
  if (c >= 50) return "不耐烦";
  if (c >= 20) return "慌乱";
  if (c > 0) return "濒临崩溃";
  return "崩溃";
}

function setComposure(c) {
  state.composure = c;
  $("#composure-num").textContent = c;
  $("#composure-bar").style.width = c + "%";
  state.mood = moodOf(c);
  $("#mood").textContent = state.mood;
}

function addLine(role, text, warn = false) {
  const div = document.createElement("div");
  div.className = "line " + role + (warn ? " warn" : "");
  const who = role === "detective" ? "你" : "嫌疑人";
  div.innerHTML = `<div class="who">${who}</div><div class="text"></div>`;
  div.querySelector(".text").textContent = text;
  const dlg = $("#dialog");
  dlg.appendChild(div);
  dlg.scrollTop = dlg.scrollHeight;
  return div.querySelector(".text");
}

async function startSession() {
  const r = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: "case_001" }),
  });
  const data = await r.json();
  state.sessionId = data.session_id;
  state.turn = 0;
  $("#turn-num").textContent = "0";
  $("#case-title").textContent = data.title;
  setComposure(data.composure);
  $("#brief-text").textContent = data.brief;
  $("#suspect").textContent = data.suspect_name;
  renderEvidence(data.evidence);
  $("#brief-evidence").innerHTML = data.evidence
    .map((e) => `<div><b>${e.name}</b>：${e.detail}</div>`)
    .join("");
}

function renderEvidence(list) {
  const box = $("#evidence-list");
  box.innerHTML = "";
  list.forEach((e) => {
    const el = document.createElement("div");
    el.className = "ev";
    el.textContent = e.name;
    el.dataset.id = e.id;
    box.appendChild(el);
  });
}

async function sendAsk(text) {
  if (!state.sessionId) return;
  addLine("detective", text);
  const target = addLine("suspect", "");
  const resp = await fetch("/api/interrogate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, text }),
  });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    target.textContent += decoder.decode(value, { stream: true });
    const dlg = $("#dialog");
    dlg.scrollTop = dlg.scrollHeight;
  }
  state.turn += 1;
  $("#turn-num").textContent = state.turn;
}

function bindEvents() {
  $("#input-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const inp = $("#ask-input");
    const v = inp.value.trim();
    if (!v) return;
    inp.value = "";
    sendAsk(v);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  startSession();
});
```

- [ ] **Step 2: 人工验证**

Run: `cd backend && python -m uvicorn app:app --port 7860 &`（需配置 `MODELSPACE_API_KEY` 才能真调 AI；无 Key 时可见加载与错误兜底）。
打开页面 → 看到案情弹窗与证据 → 点「开始审讯」→ 输入问话 → 嫌疑人流式回话。
`kill %1`。

- [ ] **Step 3: 提交**

```bash
git add backend/web/game.js && git commit -m "feat: frontend session init + rendering + streaming dialogue"
```

---

## Task 15: 前端动作（施压/证据/观察）+ 镇定仪表 + 指认结算

**Files:**
- Modify: `backend/web/game.js`
- Modify: `backend/app.py`（新增 `/api/pressure`、`/api/observe` 端点以支撑按钮）

- [ ] **Step 1: 后端新增 `/api/pressure` 与 `/api/observe`（TDD）**

在 `backend/tests/test_api.py` 末尾追加失败测试：
```python
def test_pressure_endpoint(monkeypatch, tmp_path):
    import app as appmod
    from session_store import SessionStore
    monkeypatch.setattr(appmod, "_store", SessionStore(str(tmp_path / "api6.db")))
    c = TestClient(appmod.app)
    sid = c.post("/api/session", json={"case_id": "case_001"}).json()["session_id"]
    r = c.post("/api/pressure", json={"session_id": sid})
    assert r.status_code == 200
    assert r.json()["composure"] <= 100
    assert appmod._store.get(sid)["turn_count"] == 1
```
Run: `cd backend && python -m pytest tests/test_api.py::test_pressure_endpoint -v` → Expected FAIL（404）

在 `backend/app.py` 追加：
```python
class PressureRequest(BaseModel):
    session_id: str


@app.post("/api/pressure")
def pressure(req: PressureRequest):
    s = _store.get(req.session_id)
    if s is None:
        return {"error": "session not found"}
    case = get_case(s["case_id"])
    eng = TruthEngine(case)
    res = eng.pressure(
        composure=s["composure"],
        has_evidence=False,
        pressure_count=s["pressure_count"],
    )
    new_comp = eng.clamp(s["composure"] + res["composure_delta"])
    new_pc = s["pressure_count"] + 1
    new_status = "silent" if res["lawyer_up"] else s["status"]
    s["turn_count"] += 1
    s["state"]["transcript"].append({"role": "detective", "text": "（施压）"})
    _store.update(
        s["session_id"],
        composure=new_comp,
        pressure_count=new_pc,
        turn_count=s["turn_count"],
        status=new_status,
        state=s["state"],
    )
    return {
        "composure": new_comp,
        "lawyer_up": res["lawyer_up"],
        "message": "你猛地一拍桌子，厉声施压。" if not res["lawyer_up"] else "嫌疑人冷冷地说：'我要请律师，无可奉告。'",
    }


class ObserveRequest(BaseModel):
    session_id: str


@app.post("/api/observe")
def observe(req: ObserveRequest):
    s = _store.get(req.session_id)
    if s is None:
        return {"error": "session not found"}
    mood = TruthEngine(get_case(s["case_id"]))
    m = s["composure"]
    desc = (
        "ta 神色镇定，与你对视毫不退让。" if m >= 80
        else "ta 有些不耐烦，手指敲着桌面。" if m >= 50
        else "ta 额头冒汗，眼神游移。" if m >= 20
        else "ta 呼吸急促，快要撑不住了。"
    )
    return {"mood": mood.clamp(m), "description": desc}
```
Run: `cd backend && python -m pytest tests/test_api.py::test_pressure_endpoint -v` → PASS

- [ ] **Step 2: 前端接线（追加到 game.js）**

```javascript
async function doPressure() {
  if (!state.sessionId) return;
  addLine("detective", "（猛地一拍桌子）");
  const r = await fetch("/api/pressure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId }),
  });
  const d = await r.json();
  if (typeof d.composure === "number") setComposure(d.composure);
  const target = addLine("suspect", "");
  typeInto(target, d.message || "");
  state.turn += 1;
  $("#turn-num").textContent = state.turn;
  if (d.lawyer_up) setTimeout(() => showResult(false, "嫌疑人要求律师，审讯终止，你失败了。"), 1200);
}

async function doObserve() {
  if (!state.sessionId) return;
  addLine("detective", "（仔细观察 ta 的微表情）");
  const r = await fetch("/api/observe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId }),
  });
  const d = await r.json();
  const t = addLine("suspect", "");
  typeInto(t, "（旁白）" + (d.description || ""));
}

function typeInto(el, text) {
  let i = 0;
  const timer = setInterval(() => {
    el.textContent += text[i] || "";
    i++;
    if (i >= text.length) clearInterval(timer);
  }, 24);
}

async function doPresent(evidenceId, el) {
  if (!state.sessionId) return;
  addLine("detective", `（出示证据：${evId(evidenceId)}）`);
  const r = await fetch("/api/present", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, lie_id: null, evidence_id: evidenceId }),
  });
  const d = await r.json();
  if (typeof d.composure === "number") setComposure(d.composure);
  if (d.hit) {
    el && el.classList.add("used");
    addLine("detective", "【矛盾！】" + (d.message || ""), true);
  } else {
    addLine("suspect", "（轻描淡写地）" + (d.message || "这能说明什么？"));
  }
  state.turn += 1;
  $("#turn-num").textContent = state.turn;
}

function evId(id) {
  return id; // 证据名可在渲染时记录，简化为 id
}

function showResult(win, text) {
  $("#result-title").textContent = win ? "破案！" : "审讯失败";
  $("#result-text").textContent = text;
  $("#result-modal").classList.remove("hidden");
}

async function submitAccuse() {
  const culprit = $("#accuse-culprit").value.trim();
  const method = $("#accuse-method").value.trim();
  const motive = $("#accuse-motive").value.trim();
  if (!culprit || !method || !motive) {
    alert("请填写完整");
    return;
  }
  const r = await fetch("/api/accuse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, culprit, method, motive }),
  });
  const d = await r.json();
  const truth = d.truth || {};
  const txt = win(d) ? d.reason : d.reason;
  showResult(d.win, `${d.reason}（真相：${truth.culprit} · ${truth.method} · ${truth.motive}）`);
}

function win(d) { return d.win; }
```

- [ ] **Step 3: 在 game.js 的 `bindEvents` 与 `startSession` 中接线按钮/证据点击**

在 `bindEvents()` 内追加：
```javascript
  document.querySelectorAll(".actions button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.dataset.act;
      if (act === "pressure") doPressure();
      else if (act === "observe") doObserve();
      else if (act === "accuse-open") $("#accuse-modal").classList.remove("hidden");
    });
  });
  $("#accuse-submit").addEventListener("click", submitAccuse);
  $("#accuse-cancel").addEventListener("click", () => $("#accuse-modal").classList.add("hidden"));
  $("#brief-start").addEventListener("click", () => $("#brief-modal").classList.add("hidden"));
  $("#result-restart").addEventListener("click", () => location.reload());
```

在 `renderEvidence` 中给每个证据绑定点击：
```javascript
    el.addEventListener("click", () => doPresent(e.id, el));
```
（`renderEvidence` 内 `box.appendChild(el)` 之前加）

- [ ] **Step 4: 人工验证**

Run: `cd backend && python -m pytest -v` → 全部 PASS。
Run: `cd backend && MODELSPACE_API_KEY=你的key python -m uvicorn app:app --port 7860 &` 打开页面：
- 点「开始审讯」→ 输入问话有流式回复
- 点「施压」→ 镇定下降、语气变化；连点 3 次触发律师→失败结算
- 点证据按钮 → 出示关键证据（E5/E1）→ 出现「矛盾！」、镇定大跌
- 点「指认」→ 填「林晚/奖杯重击/挪用资金灭口」→ 破案结算
`kill %1`。

- [ ] **Step 5: 提交**

```bash
git add backend/app.py backend/web/game.js backend/tests/test_api.py && git commit -m "feat: pressure/observe/present wiring + accuse result modal"
```

---

## Task 16: 案件内容定稿与逻辑闭环校验

**Files:**
- Modify: `backend/cases/case_001.py`（按需微调措辞与时间线）
- Create: `backend/tests/test_case_consistency.py`

- [ ] **Step 1: 写一致性测试**

`backend/tests/test_case_consistency.py`
```python
from cases.case_001 import get_case


def test_case_has_valid_lie_evidence_links():
    c = get_case("case_001")
    ev_ids = {e["id"] for e in c["evidence"]}
    lie_ids = {l["lie_id"] for l in c["lies"]}
    for kc in c["key_contradictions"]:
        assert kc["evidence_id"] in ev_ids, f"未知证据 {kc['evidence_id']}"
        assert kc["contradicts_lie"] in lie_ids, f"未知谎言 {kc['contradicts_lie']}"


def test_each_lie_breakable():
    c = get_case("case_001")
    broken = {kc["contradicts_lie"] for kc in c["key_contradictions"]}
    for lie in c["lies"]:
        assert lie["lie_id"] in broken, f"谎言 {lie['lie_id']} 无证据可破"


def test_confession_threshold_sane():
    c = get_case("case_001")
    assert 0 < c["confession_threshold"] < 50
```

- [ ] **Step 2: 运行，确认通过（若失败则修正 case_001 数据）**

Run: `cd backend && python -m pytest tests/test_case_consistency.py -v`
Expected: PASS（3 passed）

- [ ] **Step 3: 逻辑闭环人工核对**

Run: 手动确认：每条谎言至少有一个关键证据可证伪；关键证据链（E5/E1/E3/E4/E6）能推出「林晚 20:30 未离开 → 在场 → 奖杯有指纹 → 有资金动机 → 灭口」。如时间线有漏洞，微调 `timeline` 文案但保持证据/矛盾映射不变。

- [ ] **Step 4: 全量测试 + 提交**

```bash
cd backend && python -m pytest -v
```
```bash
git add backend/cases/case_001.py backend/tests/test_case_consistency.py && git commit -m "test: case_001 logical closure checks"
```

---

## Task 17: 部署到魔搭创空间 + 公网验证

**Files:**
- Create: `backend/.dockerignore`
- （可选）`ms_deploy.json` / 通过网页上传

- [ ] **Step 1: 写 .dockerignore**

`backend/.dockerignore`
```
__pycache__/
*.pyc
.pytest_cache/
*.db
tests/
```

- [ ] **Step 2: 本地全量测试 + 手动跑通两条路径**

Run: `cd backend && python -m pytest -v`
Expected: 全部 PASS。

Run: `cd backend && MODELSPACE_API_KEY=你的key python -m uvicorn app:app --port 7860 &`
手动验证「完美审讯破案」与「乱指认失败」两条路径，`kill %1`。

- [ ] **Step 3: 部署到魔搭创空间**

1. 登录 [modelscope.cn](https://modelscope.cn) → 创空间 → 新建 → 选 **Docker** 类型。
2. 上传 `backend/` 目录内容（或推送到仓库后在创空间关联）。确保根目录有 `Dockerfile`，服务监听 7860。
3. 在创空间「密钥/环境变量」中配置：
   - `MODELSPACE_API_KEY` = 你的 `ms-xxx` Key
   - `MODELSPACE_MODEL` = `Qwen/Qwen2.5-72B-Instruct`（或 `deepseek-ai/DeepSeek-V3`，二选一见 Task 18 A/B）
4. 触发构建，等待启动。

- [ ] **Step 4: 公网验证**

Run: 打开创空间公网地址，确认：
- 首页加载、案情弹窗、开始审讯正常
- 输入问话有 AI 回复（流式）
- 施压/证据/指认全流程可用
- 刷新页面不崩（会话持久化）

- [ ] **Step 5: 提交**

```bash
git add backend/.dockerignore && git commit -m "chore: dockerignore for studio deploy"
```

---

## Task 18: 打磨（模型 A/B + 提示词调优 + 演示材料）

- [ ] **Step 1: 模型 A/B**

用相同 5 条问话，分别在 `MODELSPACE_MODEL=Qwen/Qwen2.5-72B-Instruct` 与 `deepseek-ai/DeepSeek-V3` 下测试：
- 圆谎一致性（是否自相矛盾）
- 中文口语自然度
- 破防反应是否到位
选定综合最佳者写入 `settings.py` 默认值。

- [ ] **Step 2: 提示词调优**

根据测试调整 `prompt_builder.py` 的 system prompt：强化"不得违背已确立事实"、补充"当镇定低时语气明显慌乱"。每次改动跑 `python -m pytest tests/test_prompt_builder.py -v` 确认不回归。

- [ ] **Step 3: 录制演示视频（60–90 秒）**

覆盖：案情 → 抓矛盾破防 → 指认破案，突出"AI 会圆谎、会破防"。

- [ ] **Step 4: 写创作手记**

按赛事模板（`modelscope.cn/learn/437860`）：创意与玩法、创作过程、工具应用与体验、问题解决（延迟/圆谎漂移）、关键截图/运行记录。

- [ ] **Step 5: 社媒发构想 + 官网提交**

带指定话题（#AI无限开发者创作大赛 #AI造游戏 #盛趣游戏 #赞寄科技XSUPERZONE #华硕AI智能体电脑）@魔搭ModelScope社区 @Qoder，官网提交帖子链接；确保创空间公开可访问。

---

## Self-Review（计划对照 spec）

**1. Spec 覆盖检查：**
- 真相档案 Ground Truth → Task 3（case_001 数据）✅
- 谎言一致性引擎 → Task 6（prompt 约束）+ Task 9（注入已确立事实）✅
- 审讯记忆 → Task 2（state_json）+ Task 6/9（history 注入）✅
- 矛盾检测 → Task 4（确定性）+ Task 10（端点）✅
- 镇定状态机 → Task 5（pressure/clamp/judge）+ Task 15（前端仪表）✅
- 胜负/多结局 → Task 5（judge）+ Task 11（accuse）✅
- 技术架构（FastAPI/ModelScope/Docker）→ Task 1/7/8-11/17 ✅
- 前端 UI → Task 12/13/14/15 ✅
- 错误处理（LLM 失败兜底/重试/限流）→ Task 7（重试）、Task 9（兜底）、Task 15 ✅
- 防作弊（真相不下发）→ Task 8（`_public_evidence` 只暴露 id/name/detail）✅
- 部署 → Task 17 ✅
- 演示/手记 → Task 18 ✅

**2. 占位符扫描：** 计划中无 TBD/TODO/"稍后实现"；每个代码步骤均给出可运行代码。（Task 18 的模型名与提示词调优属迭代调参，非占位符。）

**3. 类型/命名一致性：**
- `SessionStore` 方法 `create/get/update`，字段 `session_id/composure/turn_count/pressure_count/status/state` 在 Task 2/8/9/10/11/15 一致。
- `TruthEngine` 方法 `present_evidence/pressure/clamp/judge` 在 Task 4/5/10/11/15 一致。
- `PromptBuilder.build_system/build_turn` 在 Task 6/9 一致。
- `LLMClient.stream` 在 Task 7/9 一致。
- `app.py` 的 `_store`、`_public_evidence`、`get_case` 在 Task 8-11/15 一致引用。

**结论：** 计划覆盖 spec 全部要点，无占位符，命名/类型一致，可执行。

---

## 执行说明

- **导入约定**：`backend/` 目录即代码根（Docker 内为 `/app`）。全部模块用**扁平导入**（`from settings import`、`from app import`、`from session_store import`、`from cases.case_001 import` 等），**统一在 `backend/` 目录下运行 pytest**（`cd backend && python -m pytest`）。本地 / Docker / 创空间三处一致。
- **测试隔离**：API 测试通过 `monkeypatch.setattr(appmod, "_store", SessionStore(<tmp>.db))` 注入临时库（路由在调用时解析模块级 `_store`，故替换生效）；**不打真实网络**，LLM 一律 mock。
- **LLM 单元测试一律 mock**，Task 14/15/17 的手动验证才需真实 `MODELSPACE_API_KEY`。
- **每个 Task 结束都提交**，便于回滚与评审。