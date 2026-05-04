"""Append-only audit log for tool calls (ADR-023)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from backend.app.agent.config_store import audit_log_path

logger = logging.getLogger(__name__)


def _hash_args(args: dict[str, Any]) -> str:
    blob = json.dumps(args, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def record_tool_call(
    *,
    session_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    result_size: int,
    duration_ms: int,
    error: str | None = None,
    approved: bool | None = None,
) -> None:
    """Append a single line to ``~/.anvil/agent.log``. Failures are swallowed."""
    line = {
        "ts": datetime.now(UTC).isoformat(),
        "session": session_id,
        "tool": tool_name,
        "args_hash": _hash_args(arguments),
        "result_bytes": result_size,
        "duration_ms": duration_ms,
        "error": error,
        "approved": approved,
    }
    try:
        path = audit_log_path()
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(line) + "\n")
    except OSError as exc:  # pragma: no cover
        logger.warning("Audit log write failed: %s", exc)


def read_recent(limit: int = 200) -> list[dict[str, Any]]:
    """Tail the audit log."""
    path = audit_log_path()
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
