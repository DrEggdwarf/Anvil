"""Shared test fixtures for the Anvil test suite.

Provides:
- MockBridge: a fake bridge for testing sessions/registry without real tools
- test_app: FastAPI app with lifespan disabled (no background tasks)
- async_client: httpx AsyncClient for API testing
- session_manager: fresh SessionManager per test
- subprocess_manager: fresh SubprocessManager per test
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import BridgeRegistry, bridge_registry
from backend.app.core.subprocess_manager import SubprocessManager
from backend.app.sessions.manager import SessionManager


# ── Mock Bridge ──────────────────────────────────────────


class MockBridge(BaseBridge):
    """Fake bridge for testing — no real subprocess."""

    bridge_type = "mock"

    def __init__(self) -> None:
        super().__init__()
        self.commands_received: list[tuple[str, dict]] = []
        self.start_called = False
        self.stop_called = False
        self.should_fail_start = False
        self.should_fail_execute = False

    async def start(self) -> None:
        self.start_called = True
        if self.should_fail_start:
            self.state = BridgeState.ERROR
            raise RuntimeError("Mock bridge start failure")
        self.state = BridgeState.READY

    async def stop(self) -> None:
        self.stop_called = True
        self.state = BridgeState.STOPPED

    async def health(self) -> bool:
        return self.state == BridgeState.READY

    async def execute(self, command: str, **kwargs: Any) -> Any:
        self._require_ready()
        if self.should_fail_execute:
            raise RuntimeError("Mock bridge execute failure")
        self.commands_received.append((command, kwargs))
        return {"command": command, "result": "ok", **kwargs}


# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def register_mock_bridge():
    """Register MockBridge in the global registry for each test, then cleanup."""
    bridge_registry.register("mock", MockBridge)
    yield
    # Cleanup: remove mock from registry
    bridge_registry._bridges.pop("mock", None)


@pytest.fixture
def fresh_registry() -> BridgeRegistry:
    """A fresh isolated registry (not the global one)."""
    reg = BridgeRegistry()
    reg.register("mock", MockBridge)
    return reg


@pytest_asyncio.fixture
async def session_manager() -> SessionManager:
    """Fresh SessionManager for each test."""
    sm = SessionManager()
    yield sm
    await sm.cleanup_all()


@pytest.fixture
def subprocess_manager() -> SubprocessManager:
    """Fresh SubprocessManager for each test."""
    return SubprocessManager()


@pytest_asyncio.fixture
async def async_client():
    """httpx AsyncClient wired to the FastAPI app (with lifespan)."""
    from backend.app.core.lifecycle import lifespan
    from backend.app.main import app

    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
