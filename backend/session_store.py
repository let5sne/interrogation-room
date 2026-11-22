import json
import sqlite3
import threading
import time
import uuid
from contextlib import closing


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
        with self._lock, closing(self._conn()) as conn:
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
            conn.commit()

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
        with self._lock, closing(self._conn()) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, case_id, composure, pressure_count, turn_count, status, state_json, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, case_id, composure, 0, 0, "active",
                 json.dumps(state, ensure_ascii=False), now, now),
            )
            conn.commit()
        return self.get(sid)

    def get(self, session_id: str):
        with closing(self._conn()) as conn:
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
        with self._lock, closing(self._conn()) as conn:
            conn.execute(f"UPDATE sessions SET {cols} WHERE session_id=?", values)
            conn.commit()