"""WebSocket infrastructure — typed messages, dispatcher, heartbeat.

All WebSocket communication follows the WSMessage schema.
Handlers are registered in the dispatcher and routed by session_type + command.
"""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import Awaitable, Callable

from backend.app.core.config import settings
from backend.app.core.exceptions import SessionExpired, SessionNotFound, ValidationError
from backend.app.models.ws import WSMessage, WSMessageType
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# WS close codes (RFC 6455)
_WS_POLICY_VIOLATION = 1008
_WS_UNSUPPORTED_DATA = 1003

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Handler signature: async (websocket, message, session_id) -> dict | None
WSHandler = Callable[[WebSocket, WSMessage, str], Awaitable[dict | None]]


class WSDispatcher:
    """Routes incoming WebSocket messages to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, WSHandler] = {}

    def register(self, command: str, handler: WSHandler) -> None:
        """Register a handler for 'session_type.command'."""
        self._handlers[command] = handler

    def get_handler(self, command: str) -> WSHandler | None:
        return self._handlers.get(command)

    @property
    def commands(self) -> list[str]:
        return list(self._handlers.keys())


# Global dispatcher — bridges register their WS handlers here
ws_dispatcher = WSDispatcher()


def _origin_allowed(origin: str | None) -> bool:
    """ADR-015 / ADR-016: refuse connections from unlisted origins."""
    if not origin:
        # Native WS clients (Tauri WebView, Python tests) often omit Origin — allow.
        return True
    allowed = settings.cors_origins
    return "*" in allowed or origin in allowed


@router.websocket("/ws/{session_type}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_type: str,
    session_id: str,
) -> None:
    """Generic WebSocket endpoint — dispatches messages to registered handlers.

    ADR-016: requires `?token=...` query string matching the session's token.
    Validates session exists, type matches, and Origin is allowed before accept().
    """
    # 1. Origin gate (defense in depth on top of CORS middleware).
    if not _origin_allowed(websocket.headers.get("origin")):
        await websocket.close(code=_WS_POLICY_VIOLATION, reason="Origin not allowed")
        return

    # 2. Token gate — must precede accept() to avoid leaking handshake to unauth clients.
    sm = getattr(websocket.app.state, "session_manager", None)
    if sm is None:
        await websocket.close(code=_WS_POLICY_VIOLATION, reason="Server not ready")
        return

    token = websocket.query_params.get("token", "")
    try:
        session = sm.get(session_id)
    except (SessionNotFound, SessionExpired, ValidationError):
        await websocket.close(code=_WS_POLICY_VIOLATION, reason="Session invalid")
        return

    if not token or not secrets.compare_digest(token, session.token):
        await websocket.close(code=_WS_POLICY_VIOLATION, reason="Invalid token")
        return

    if session.bridge_type != session_type:
        await websocket.close(
            code=_WS_UNSUPPORTED_DATA,
            reason=f"Session type mismatch (expected {session.bridge_type})",
        )
        return

    await websocket.accept()
    logger.info("WS connected: %s/%s", session_type, session_id)

    try:
        while True:
            raw = await websocket.receive_text()

            # Parse message
            try:
                data = json.loads(raw)
                message = WSMessage(**data)
            except (json.JSONDecodeError, Exception) as e:
                await _send_error(websocket, "INVALID_MESSAGE", str(e))
                continue

            # Heartbeat
            if message.type == WSMessageType.PING:
                await websocket.send_json(
                    WSMessage(
                        type=WSMessageType.PONG,
                        request_id=message.request_id,
                    ).model_dump()
                )
                continue

            # Command dispatch
            if message.type == WSMessageType.COMMAND:
                command_name = message.payload.get("command", "")
                handler_key = f"{session_type}.{command_name}"
                handler = ws_dispatcher.get_handler(handler_key)

                if handler is None:
                    await _send_error(
                        websocket,
                        "UNKNOWN_COMMAND",
                        f"No handler for '{handler_key}'",
                        request_id=message.request_id,
                    )
                    continue

                try:
                    result = await handler(websocket, message, session_id)
                    if result is not None:
                        await websocket.send_json(
                            WSMessage(
                                type=WSMessageType.RESULT,
                                session_id=session_id,
                                request_id=message.request_id,
                                payload=result,
                            ).model_dump()
                        )
                except Exception:
                    logger.exception("Handler error: %s", handler_key)
                    await _send_error(
                        websocket,
                        "HANDLER_ERROR",
                        f"Internal error in handler '{handler_key}'",
                        request_id=message.request_id,
                    )

    except WebSocketDisconnect:
        logger.info("WS disconnected: %s/%s", session_type, session_id)


async def _send_error(
    ws: WebSocket,
    code: str,
    message: str,
    request_id: str | None = None,
) -> None:
    """Send a typed error message over WebSocket."""
    await ws.send_json(
        WSMessage(
            type=WSMessageType.ERROR,
            request_id=request_id or "",
            payload={"code": code, "message": message},
        ).model_dump()
    )
