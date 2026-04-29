"""Session tools — wired to the FastAPI /api/sessions endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from anvil_mcp.client import get_client


async def session_create(bridge_type: str) -> dict:
    """Create a new Anvil session for the given bridge type.

    Args:
        bridge_type: One of "gdb", "rizin", "pwn", "firmware", "protocol".

    Returns:
        {"session_id": str, "state": str, "token": str}
    """
    client = get_client()
    data = await client.post("/api/sessions", json={"bridge_type": bridge_type})
    return {"session_id": data["id"], "state": data["state"], "token": data["token"]}


async def session_delete(session_id: str) -> dict:
    """Destroy a session and release its resources.

    Args:
        session_id: 16-hex-char session identifier.

    Returns:
        {"ok": True}
    """
    client = get_client()
    await client.delete(f"/api/sessions/{session_id}")
    return {"ok": True}


async def session_list() -> list[dict]:
    """List all active sessions.

    Returns:
        list of {id, bridge_type, state, age_s}
    """
    client = get_client()
    data = await client.get("/api/sessions")
    now = datetime.now(UTC)
    result = []
    for s in data.get("sessions", []):
        try:
            created = datetime.fromisoformat(s["created_at"])
            age_s = int((now - created).total_seconds())
        except Exception:
            age_s = -1
        result.append({
            "id": s["id"],
            "bridge_type": s["bridge_type"],
            "state": s["state"],
            "age_s": age_s,
        })
    return result
