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