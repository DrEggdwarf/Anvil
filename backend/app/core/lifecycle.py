"""Application lifecycle — startup and shutdown events."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.core.workspace import WorkspaceManager
from backend.app.sessions.manager import SessionManager
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Ensure bridges are registered
import backend.app.bridges.firmware_bridge  # noqa: E402
import backend.app.bridges.gdb_bridge  # noqa: E402
import backend.app.bridges.protocol_bridge  # noqa: E402
import backend.app.bridges.pwn_bridge  # noqa: E402
import backend.app.bridges.rizin_bridge  # noqa: E402, F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup → yield → shutdown."""
    # ── Startup ──────────────────────────────────────────
    logger.info("Anvil backend starting...")

    app.state.subprocess_manager = SubprocessManager()
    app.state.session_manager = SessionManager()
    app.state.workspace_manager = WorkspaceManager()
    await app.state.session_manager.start_cleanup_loop()

    # Init WS handlers that need session_manager
    from backend.app.api.gdb_ws import init_gdb_ws_handlers
    init_gdb_ws_handlers(app.state.session_manager)

    logger.info("Anvil backend ready")

    yield

    # ── Shutdown ─────────────────────────────────────────
    logger.info("Anvil backend shutting down...")

    await app.state.session_manager.stop_cleanup_loop()
    sessions_cleaned = await app.state.session_manager.cleanup_all()
    processes_cleaned = await app.state.subprocess_manager.cleanup_all()
    workspaces_cleaned = app.state.workspace_manager.cleanup_all()

    logger.info(
        "Cleanup: %d sessions, %d processes, %d workspaces",
        sessions_cleaned,
        processes_cleaned,
        workspaces_cleaned,
    )
    logger.info("Anvil backend stopped")
