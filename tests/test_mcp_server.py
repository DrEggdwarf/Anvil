"""Smoke tests for the Anvil MCP server skeleton.

Validates:
- All tool modules can be imported
- Stub tools raise NotImplementedError (not silent failures)
- Session tools have correct async signatures
- Prompt functions return strings without a backend
"""

from __future__ import annotations

import inspect

import pytest

from anvil_mcp.tools.asm import (
    gdb_breakpoint,
    gdb_disasm,
    gdb_load,
    gdb_memory,
    gdb_registers,
    gdb_run,
    gdb_step,
)
from anvil_mcp.tools.firmware import (
    firmware_entropy,
    firmware_extract,
    firmware_scan,
    firmware_triage,
)
from anvil_mcp.tools.pwn import (
    pwn_checksec,
    pwn_cyclic,
    pwn_cyclic_find,
    pwn_rop_gadgets,
    pwn_shellcraft,
)
from anvil_mcp.tools.re import (
    re_analyze,
    re_decompile,
    re_disasm,
    re_functions,
    re_strings,
    re_xrefs,
)
from anvil_mcp.tools.session import session_create, session_delete, session_list
from anvil_mcp.tools.wire import (
    wire_decode_frame,
    wire_load_pcap,
    wire_replay,
    wire_send,
)


# ── Import sanity ────────────────────────────────────────


def test_client_importable():
    from anvil_mcp.client import AnvilClient, get_client  # noqa: F401


def test_prompts_importable():
    from anvil_mcp.prompts.pipelines import ctf_binary, exploit_pipeline, firmware_audit  # noqa: F401


def test_resources_importable():
    from anvil_mcp.resources.session import (  # noqa: F401
        session_binary_resource,
        session_list_resource,
        session_workspace_resource,
    )


# ── Stub tools raise NotImplementedError ─────────────────


_STUBS = [
    (gdb_load, ("sid", "/tmp/bin")),
    (gdb_run, ("sid",)),
    (gdb_step, ("sid",)),
    (gdb_breakpoint, ("sid", "main")),
    (gdb_registers, ("sid",)),
    (gdb_memory, ("sid", "0x0")),
    (gdb_disasm, ("sid", "0x0")),
    (pwn_checksec, ("sid", "/tmp/bin")),
    (pwn_cyclic, ("sid", 64)),
    (pwn_cyclic_find, ("sid", "0x61616161")),
    (pwn_rop_gadgets, ("sid", "/tmp/bin")),
    (pwn_shellcraft, ("sid", "amd64", "linux", "sh")),
    (firmware_scan, ("sid", "/tmp/fw.bin")),
    (firmware_extract, ("sid", "/tmp/fw.bin")),
    (firmware_entropy, ("sid", "/tmp/fw.bin")),
    (firmware_triage, ("sid", "/tmp/extracted")),
    (wire_load_pcap, ("sid", "/tmp/cap.pcap")),
    (wire_decode_frame, ("sid", 0)),
    (wire_send, ("sid", "127.0.0.1", 502, {})),
    (wire_replay, ("sid", 0, 1)),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fn,args", _STUBS)
async def test_stub_raises_not_implemented(fn, args):
    assert inspect.iscoroutinefunction(fn), f"{fn.__name__} must be async"
    with pytest.raises(NotImplementedError):
        await fn(*args)


# ── Wired RE tools raise httpx errors (no backend in tests) ──

_RE_WIRED = [
    (re_analyze, ("sid", "/tmp/bin")),
    (re_functions, ("sid",)),
    (re_disasm, ("sid", "main")),
    (re_decompile, ("sid", "main")),
    (re_strings, ("sid",)),
    (re_xrefs, ("sid", "0x401000")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fn,args", _RE_WIRED)
async def test_re_tools_are_wired(fn, args):
    """RE tools are wired to the backend — they raise httpx errors, not NotImplementedError."""
    assert inspect.iscoroutinefunction(fn), f"{fn.__name__} must be async"
    with pytest.raises(Exception) as exc_info:
        await fn(*args)
    assert not isinstance(exc_info.value, NotImplementedError), (
        f"{fn.__name__} should be wired, not a stub"
    )


# ── Session tools are async and have correct parameter names ─


def test_session_create_signature():
    sig = inspect.signature(session_create)
    assert "bridge_type" in sig.parameters
    assert inspect.iscoroutinefunction(session_create)


def test_session_delete_signature():
    sig = inspect.signature(session_delete)
    assert "session_id" in sig.parameters
    assert inspect.iscoroutinefunction(session_delete)


def test_session_list_signature():
    assert inspect.iscoroutinefunction(session_list)


# ── Prompt functions return strings synchronously ────────


def test_exploit_pipeline_returns_string():
    from anvil_mcp.prompts.pipelines import exploit_pipeline

    result = exploit_pipeline("/tmp/vuln")
    assert isinstance(result, str)
    assert "pwn_checksec" in result
    assert "re_analyze" in result


def test_firmware_audit_returns_string():
    from anvil_mcp.prompts.pipelines import firmware_audit

    result = firmware_audit("/tmp/fw.bin")
    assert isinstance(result, str)
    assert "firmware_scan" in result
    assert "firmware_extract" in result


def test_ctf_binary_returns_string():
    from anvil_mcp.prompts.pipelines import ctf_binary

    result = ctf_binary("/tmp/challenge")
    assert isinstance(result, str)
    assert "pwn_checksec" in result
    assert "re_decompile" in result


def test_ctf_binary_with_description():
    from anvil_mcp.prompts.pipelines import ctf_binary

    result = ctf_binary("/tmp/challenge", description="ret2win format string")
    assert "ret2win format string" in result
