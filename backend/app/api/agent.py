"""Agent API — SSE chat, sessions CRUD, settings (BYOK), audit log (ADR-023)."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from backend.app.agent import audit, storage
from backend.app.agent.config_store import load_settings, save_settings, settings_for_frontend
from backend.app.agent.models import (
    PROVIDERS,
    AgentChatRequest,
    ProviderConfig,
    ProviderTestRequest,
)
from backend.app.agent.providers import ProviderError, get_provider
from backend.app.agent.runtime import Runtime
from backend.app.api.deps import get_session_manager
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ── Chat (SSE) ───────────────────────────────────────────
@router.post("/chat")
async def chat(
    req: AgentChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> StreamingResponse:
    runtime = Runtime(session_manager=session_manager)

    async def _gen():
        try:
            async for chunk in runtime.chat_stream(req):
                yield chunk
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("Agent chat crashed")
            import json as _json

            yield (
                "data: "
                + _json.dumps({"type": "error", "data": {"code": "RUNTIME_CRASH", "message": str(exc)}})
                + "\n\n"
            )

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Sessions ─────────────────────────────────────────────
@router.get("/sessions")
def list_sessions(limit: int = 100) -> dict[str, Any]:
    sessions = storage.get_storage().list_sessions(limit=limit)
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "module": s.module,
                "provider": s.provider,
                "model": s.model,
                "created_at": s.created_at.isoformat(),
                "last_used": s.last_used.isoformat(),
                "message_count": len(s.messages),
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str = Path(..., max_length=64)) -> dict[str, Any]:
    sess = storage.get_storage().get(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="session not found")
    return sess.model_dump(mode="json")


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str = Path(..., max_length=64)) -> dict[str, bool]:
    ok = storage.get_storage().delete(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")
    return {"deleted": True}


@router.delete("/sessions")
def purge_sessions() -> dict[str, int]:
    return {"deleted": storage.get_storage().purge_all()}


# ── Settings ─────────────────────────────────────────────
@router.get("/settings")
def get_settings() -> dict[str, Any]:
    return settings_for_frontend(load_settings())


@router.put("/settings")
def update_settings(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Partial update — fields omitted keep their previous value.

    To avoid clobbering API keys when the frontend never re-sends them, an
    empty string in ``providers[name].api_key`` is treated as 'no change'.
    """
    current = load_settings()
    if "active_provider" in payload and payload["active_provider"] in PROVIDERS:
        current.active_provider = payload["active_provider"]
    if "strict_mode" in payload:
        current.strict_mode = bool(payload["strict_mode"])
    if "allow_write_exec" in payload:
        current.allow_write_exec = bool(payload["allow_write_exec"])
    if "language" in payload and payload["language"] in ("fr", "en"):
        current.language = payload["language"]
    if "token_cap" in payload:
        with contextlib.suppress(TypeError, ValueError):
            current.token_cap = max(100, min(1_000_000, int(payload["token_cap"])))
    providers_in = payload.get("providers") or {}
    for name, conf in providers_in.items():
        if name not in PROVIDERS or not isinstance(conf, dict):
            continue
        existing = current.providers.get(name) or ProviderConfig()
        if conf.get("api_key"):
            existing.api_key = conf["api_key"]
        if "base_url" in conf:
            existing.base_url = conf["base_url"] or None
        if conf.get("default_model"):
            existing.default_model = conf["default_model"]
        current.providers[name] = existing  # type: ignore[index]
    save_settings(current)
    return settings_for_frontend(current)


@router.get("/providers")
def list_providers() -> dict[str, Any]:
    return {"providers": list(PROVIDERS)}


@router.post("/providers/test")
async def test_provider(req: ProviderTestRequest) -> dict[str, Any]:
    settings = load_settings()
    conf = settings.providers.get(req.provider) or ProviderConfig()
    if req.api_key:
        conf = ProviderConfig(
            api_key=req.api_key,
            base_url=req.base_url or conf.base_url,
            default_model=req.model or conf.default_model,
        )
    provider = get_provider(req.provider)
    try:
        return await provider.test(config=conf, model=req.model or conf.default_model or "")
    except ProviderError as exc:
        return {"ok": False, "error": str(exc)}


# ── Audit log ────────────────────────────────────────────
@router.get("/audit")
def audit_log(limit: int = 200) -> dict[str, Any]:
    limit = max(1, min(2000, limit))
    return {"entries": audit.read_recent(limit=limit)}
