"""Tests for the agent tool registry / dispatcher (ADR-023)."""

from __future__ import annotations

import pytest

from backend.app.agent import tools as tools_mod
from backend.app.core.exceptions import AnvilError


def test_registry_is_non_empty():
    names = [t.name for t in tools_mod.list_tools()]
    assert "rizin_open_binary" in names
    assert "pwn_checksec" in names
    assert "gdb_run" in names


def test_anthropic_schema_shape():
    schema = tools_mod.to_anthropic_schema(tools_mod.list_tools())
    assert schema and "input_schema" in schema[0]
    assert "name" in schema[0]


def test_openai_schema_shape():
    schema = tools_mod.to_openai_schema(tools_mod.list_tools())
    assert schema and schema[0]["type"] == "function"
    assert schema[0]["function"]["parameters"]


def test_strict_mode_filters_by_module():
    re_only = tools_mod.tools_for_modules(["re"], strict=True)
    names = {t.name for t in re_only}
    assert "rizin_decompile" in names
    assert "pwn_checksec" not in names
    # Non-strict returns everything.
    full = tools_mod.tools_for_modules(["re"], strict=False)
    assert len(full) >= len(re_only)


def test_destructive_flag():
    spec = tools_mod.get_tool("gdb_run")
    assert spec is not None
    assert spec.destructive is True


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_raises():
    with pytest.raises(AnvilError) as exc:
        await tools_mod.dispatch(
            tool_name="not_a_tool",
            arguments={},
            anvil_session_ids={},
            agent_session_id="agent1",
            session_manager=None,
        )
    assert exc.value.code == "TOOL_NOT_FOUND"


@pytest.mark.asyncio
async def test_dispatch_missing_session_raises():
    class _Mgr:
        def get(self, sid):  # pragma: no cover
            raise AssertionError("should not be called")

    with pytest.raises(AnvilError) as exc:
        await tools_mod.dispatch(
            tool_name="rizin_functions",
            arguments={},
            anvil_session_ids={},
            agent_session_id="agent1",
            session_manager=_Mgr(),
        )
    assert exc.value.code == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_dispatch_calls_handler_with_session(monkeypatch):
    captured = {}

    class _Bridge:
        bridge_type = "rizin"

        async def functions(self):
            captured["called"] = True
            return [{"addr": "0x401000", "name": "main"}]

    class _Session:
        bridge_type = "rizin"
        bridge = _Bridge()

    class _Mgr:
        def get(self, sid):
            assert sid == "anvil1"
            return _Session()

    out = await tools_mod.dispatch(
        tool_name="rizin_functions",
        arguments={},
        anvil_session_ids={"rizin": "anvil1"},
        agent_session_id="agent1",
        session_manager=_Mgr(),
    )
    assert captured.get("called") is True
    assert out["result"]["functions"][0]["name"] == "main"


@pytest.mark.asyncio
async def test_dispatch_wrong_session_type():
    class _Bridge:
        bridge_type = "gdb"

    class _Session:
        bridge_type = "gdb"
        bridge = _Bridge()

    class _Mgr:
        def get(self, sid):
            return _Session()

    with pytest.raises(AnvilError) as exc:
        await tools_mod.dispatch(
            tool_name="rizin_functions",
            arguments={},
            anvil_session_ids={"rizin": "anvil1"},
            agent_session_id="agent1",
            session_manager=_Mgr(),
        )
    assert exc.value.code == "WRONG_SESSION_TYPE"
