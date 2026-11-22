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