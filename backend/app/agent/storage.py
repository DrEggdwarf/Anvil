"""SQLite persistence for agent sessions (ADR-023).

Schema is intentionally minimal: messages are stored as a JSON blob to keep
the loop simple. Provider/model are recorded so a session can be replayed
even after the user changes settings.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.agent.config_store import db_path
from backend.app.agent.models import AgentSession, ChatMessage

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL,
    last_used    TEXT NOT NULL,
    title        TEXT NOT NULL,
    module       TEXT NOT NULL,
    provider     TEXT NOT NULL,
    model        TEXT NOT NULL,
    messages     TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_sessions_last_used ON sessions(last_used DESC);
"""


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or db_path()
    conn = sqlite3.connect(target, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _row_to_session(row: sqlite3.Row) -> AgentSession:
    raw = json.loads(row["messages"])
    return AgentSession(
        id=row["id"],
        title=row["title"],
        module=row["module"],
        provider=row["provider"],
        model=row["model"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_used=datetime.fromisoformat(row["last_used"]),
        messages=[ChatMessage.model_validate(m) for m in raw],
    )


class AgentStorage:
    """Sync SQLite wrapper — small writes, called from FastAPI threadpool."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path

    def _conn(self) -> sqlite3.Connection:
        return _connect(self._path)

    def create_session(
        self,
        *,
        module: str,
        provider: str,
        model: str,
        title: str = "Nouvelle conversation",
    ) -> AgentSession:
        sid = uuid.uuid4().hex[:16]
        now = datetime.now(UTC)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions(id,created_at,last_used,title,module,provider,model,messages) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (sid, now.isoformat(), now.isoformat(), title, module, provider, model, "[]"),
            )
        return AgentSession(
            id=sid,
            title=title,
            module=module,
            provider=provider,  # type: ignore[arg-type]
            model=model,
            created_at=now,
            last_used=now,
            messages=[],
        )

    def get(self, session_id: str) -> AgentSession | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return _row_to_session(row) if row else None

    def list_sessions(self, limit: int = 100) -> list[AgentSession]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY last_used DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_session(r) for r in rows]

    def update_messages(
        self,
        session_id: str,
        messages: list[ChatMessage],
        *,
        title: str | None = None,
    ) -> None:
        payload = json.dumps([m.model_dump(mode="json") for m in messages])
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            if title is not None:
                conn.execute(
                    "UPDATE sessions SET messages=?, last_used=?, title=? WHERE id=?",
                    (payload, now, title, session_id),
                )
            else:
                conn.execute(
                    "UPDATE sessions SET messages=?, last_used=? WHERE id=?",
                    (payload, now, session_id),
                )

    def delete(self, session_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            return cur.rowcount > 0

    def purge_all(self) -> int:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM sessions")
            return cur.rowcount


def derive_title(first_message: str) -> str:
    snippet = first_message.strip().splitlines()[0] if first_message.strip() else "Nouvelle conversation"
    snippet = snippet.strip()
    return (snippet[:60] + "…") if len(snippet) > 60 else snippet or "Nouvelle conversation"


# Singleton (not strictly needed since SQLite is process-shared, but matches other singletons)
_storage: AgentStorage | None = None


def get_storage() -> AgentStorage:
    global _storage
    if _storage is None:
        _storage = AgentStorage()
    return _storage


def reset_storage_for_tests(path: Any | None = None) -> AgentStorage:
    """Reset the storage singleton (used by tests)."""
    global _storage
    _storage = AgentStorage(path)
    return _storage
