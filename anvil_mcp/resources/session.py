"""Session resources — stubs for MCP resource protocol."""

from __future__ import annotations

_STUB = "Session resource not yet wired — implement alongside session tooling."


async def session_list_resource() -> str:
    """Resource: session://list — returns all active sessions as JSON text."""
    raise NotImplementedError(_STUB)


async def session_binary_resource(session_id: str) -> str:
    """Resource: session://{id}/binary — path to the binary loaded in the session."""
    raise NotImplementedError(_STUB)


async def session_workspace_resource(session_id: str) -> str:
    """Resource: session://{id}/workspace — path to the session workspace directory."""
    raise NotImplementedError(_STUB)
