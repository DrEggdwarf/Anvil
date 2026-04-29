"""Tests for BaseBridge and BridgeRegistry."""

import pytest

from backend.app.bridges.base import BridgeState
from backend.app.bridges.registry import BridgeRegistry
from backend.app.core.exceptions import BridgeNotReady
from conftest import MockBridge


class TestBridgeState:
    def test_initial_state_is_created(self):
        bridge = MockBridge()
        assert bridge.state == BridgeState.CREATED

    @pytest.mark.asyncio
    async def test_start_sets_ready(self):
        bridge = MockBridge()
        await bridge.start()
        assert bridge.state == BridgeState.READY

    @pytest.mark.asyncio
    async def test_stop_sets_stopped(self):
        bridge = MockBridge()
        await bridge.start()
        await bridge.stop()
        assert bridge.state == BridgeState.STOPPED

    @pytest.mark.asyncio
    async def test_require_ready_raises_when_not_ready(self):
        bridge = MockBridge()
        with pytest.raises(BridgeNotReady):
            bridge._require_ready()

    @pytest.mark.asyncio
    async def test_require_ready_passes_when_ready(self):
        bridge = MockBridge()
        await bridge.start()
        bridge._require_ready()  # Should not raise

    @pytest.mark.asyncio
    async def test_execute_requires_ready(self):
        bridge = MockBridge()
        with pytest.raises(BridgeNotReady):
            await bridge.execute("test")

    @pytest.mark.asyncio
    async def test_execute_records_commands(self):
        bridge = MockBridge()
        await bridge.start()
        result = await bridge.execute("do_something", arg1="val1")
        assert result["command"] == "do_something"
        assert result["arg1"] == "val1"
        assert len(bridge.commands_received) == 1

    @pytest.mark.asyncio
    async def test_failed_start_sets_error(self):
        bridge = MockBridge()
        bridge.should_fail_start = True
        with pytest.raises(RuntimeError):
            await bridge.start()
        assert bridge.state == BridgeState.ERROR


class TestBridgeRegistry:
    def test_register_and_get(self, fresh_registry: BridgeRegistry):
        cls = fresh_registry.get("mock")
        assert cls is not None
        assert cls.bridge_type == "mock"

    def test_get_unknown_returns_none(self, fresh_registry: BridgeRegistry):
        assert fresh_registry.get("nonexistent") is None

    def test_list_types(self, fresh_registry: BridgeRegistry):
        types = fresh_registry.list_types()
        assert "mock" in types

    def test_contains(self, fresh_registry: BridgeRegistry):
        assert "mock" in fresh_registry
        assert "nonexistent" not in fresh_registry

    def test_len(self, fresh_registry: BridgeRegistry):
        assert len(fresh_registry) == 1

    def test_register_overwrite(self, fresh_registry: BridgeRegistry):
        """Registering the same type twice overwrites."""
        original_cls = fresh_registry.get("mock")

        class AnotherMock(original_cls):
            bridge_type = "mock"

        fresh_registry.register("mock", AnotherMock)
        assert fresh_registry.get("mock") is AnotherMock
