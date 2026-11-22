from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


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