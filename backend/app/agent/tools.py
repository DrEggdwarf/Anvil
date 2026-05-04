"""Agent tool registry & dispatcher (ADR-023).

Tools are thin wrappers around existing bridge methods, looked up via the
session manager. Each tool declares:

* ``name``        — exposed to the LLM (snake_case, namespaced)
* ``description`` — short LLM-facing doc
* ``parameters``  — JSON Schema (Anthropic / OpenAI tool-call format)
* ``bridge_type`` — required Anvil session bridge type (or ``None`` for meta)
* ``modules``     — module categories the tool belongs to (RE / Pwn / …)
* ``destructive`` — when True, requires inline approval before exec
* ``handler``     — async callable ``(session, **args) -> Any``

The dispatcher resolves an Anvil session from ``session_id`` (per-tool param)
or from the active module's session passed by the runtime.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from backend.app.agent.audit import record_tool_call
from backend.app.core.exceptions import AnvilError, SessionNotFound
from backend.app.sessions.manager import Session

logger = logging.getLogger(__name__)


ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    bridge_type: str | None
    modules: tuple[str, ...]
    destructive: bool
    handler: ToolHandler
    category: str = "read"  # "read" | "exec" | "write"
    tags: tuple[str, ...] = field(default_factory=tuple)


# ── Handlers (thin shims onto bridge methods) ────────────
async def _rizin_open(session: Session, *, binary_path: str) -> dict:
    out = await session.bridge.open_binary(binary_path)  # type: ignore[attr-defined]
    return {"summary": f"Opened {binary_path}", "result": out}


async def _rizin_functions(session: Session) -> dict:
    fns = await session.bridge.functions()  # type: ignore[attr-defined]
    return {"summary": f"{len(fns)} functions", "functions": fns[:200]}


async def _rizin_disasm(session: Session, *, address: str, count: int = 32) -> dict:
    rows = await session.bridge.disassemble(address, count)  # type: ignore[attr-defined]
    return {"summary": f"{len(rows)} instructions @ {address}", "instructions": rows}


async def _rizin_decompile(session: Session, *, address: str) -> dict:
    return await session.bridge.decompile(address)  # type: ignore[attr-defined]


async def _rizin_strings(session: Session, *, min_len: int = 4) -> dict:
    s = await session.bridge.strings(min_len)  # type: ignore[attr-defined]
    return {"summary": f"{len(s)} strings", "strings": s[:300]}


async def _rizin_xrefs_to(session: Session, *, address: str) -> dict:
    refs = await session.bridge.function_xrefs_to(address)  # type: ignore[attr-defined]
    return {"summary": f"{len(refs)} xrefs to {address}", "xrefs": refs}


async def _rizin_xrefs_from(session: Session, *, address: str) -> dict:
    refs = await session.bridge.function_xrefs_from(address)  # type: ignore[attr-defined]
    return {"summary": f"{len(refs)} xrefs from {address}", "xrefs": refs}


async def _rizin_read_hex(session: Session, *, address: str, size: int = 256) -> dict:
    if hasattr(session.bridge, "read_hex_text"):
        text = await session.bridge.read_hex_text(address, size)  # type: ignore[attr-defined]
        return {"summary": f"Hex dump {address} ({size} bytes)", "hex": text}
    raise AnvilError("Bridge does not support read_hex_text", code="TOOL_NOT_FOUND")


async def _pwn_checksec(session: Session) -> dict:
    return await session.bridge.checksec()  # type: ignore[attr-defined]


async def _pwn_cyclic(session: Session, *, length: int = 64) -> dict:
    pat = await session.bridge.cyclic(length)  # type: ignore[attr-defined]
    return {"summary": f"Cyclic pattern len={length}", "pattern": pat}


async def _pwn_rop(session: Session, *, query: str = "ret") -> dict:
    gadgets = await session.bridge.rop_search(query)  # type: ignore[attr-defined]
    return {"summary": f"{len(gadgets)} gadgets matching {query!r}", "gadgets": gadgets[:50]}


async def _gdb_run(session: Session) -> dict:
    return await session.bridge.run()  # type: ignore[attr-defined]


async def _gdb_registers(session: Session) -> dict:
    regs = await session.bridge.registers()  # type: ignore[attr-defined]
    return {"summary": "Registers snapshot", "registers": regs}


async def _gdb_breakpoint(session: Session, *, location: str) -> dict:
    bp = await session.bridge.breakpoint_set(location)  # type: ignore[attr-defined]
    return {"summary": f"Breakpoint at {location}", "breakpoint": bp}


async def _firmware_scan(session: Session, *, file_path: str) -> dict:
    out = await session.bridge.scan(file_path)  # type: ignore[attr-defined]
    return {"summary": "binwalk scan complete", "result": out}


# ── Registry ─────────────────────────────────────────────
def _build_registry() -> dict[str, ToolSpec]:
    schema_addr = {"type": "string", "description": "Hex address (e.g. 0x401260) or function name"}
    return {
        s.name: s
        for s in [
            ToolSpec(
                name="rizin_open_binary",
                description="Open and analyze a binary in the rizin session.",
                parameters={
                    "type": "object",
                    "properties": {"binary_path": {"type": "string"}},
                    "required": ["binary_path"],
                },
                bridge_type="rizin",
                modules=("re", "pwn"),
                destructive=False,
                handler=_rizin_open,
                category="read",
            ),
            ToolSpec(
                name="rizin_functions",
                description="List all analyzed functions in the loaded binary.",
                parameters={"type": "object", "properties": {}},
                bridge_type="rizin",
                modules=("re", "pwn"),
                destructive=False,
                handler=_rizin_functions,
            ),
            ToolSpec(
                name="rizin_disasm",
                description="Disassemble N instructions at an address.",
                parameters={
                    "type": "object",
                    "properties": {"address": schema_addr, "count": {"type": "integer", "default": 32}},
                    "required": ["address"],
                },
                bridge_type="rizin",
                modules=("re", "pwn"),
                destructive=False,
                handler=_rizin_disasm,
            ),
            ToolSpec(
                name="rizin_decompile",
                description="Decompile a function via r2ghidra (pdg) with fallback to pdd.",
                parameters={
                    "type": "object",
                    "properties": {"address": schema_addr},
                    "required": ["address"],
                },
                bridge_type="rizin",
                modules=("re",),
                destructive=False,
                handler=_rizin_decompile,
            ),
            ToolSpec(
                name="rizin_strings",
                description="List printable strings in the loaded binary.",
                parameters={
                    "type": "object",
                    "properties": {"min_len": {"type": "integer", "default": 4}},
                },
                bridge_type="rizin",
                modules=("re",),
                destructive=False,
                handler=_rizin_strings,
            ),
            ToolSpec(
                name="rizin_xrefs_to",
                description="Cross-references pointing to an address (callers).",
                parameters={
                    "type": "object",
                    "properties": {"address": schema_addr},
                    "required": ["address"],
                },
                bridge_type="rizin",
                modules=("re",),
                destructive=False,
                handler=_rizin_xrefs_to,
            ),
            ToolSpec(
                name="rizin_xrefs_from",
                description="Cross-references emitted from an address (callees).",
                parameters={
                    "type": "object",
                    "properties": {"address": schema_addr},
                    "required": ["address"],
                },
                bridge_type="rizin",
                modules=("re",),
                destructive=False,
                handler=_rizin_xrefs_from,
            ),
            ToolSpec(
                name="rizin_read_hex",
                description="Read N bytes at an address as a hex dump.",
                parameters={
                    "type": "object",
                    "properties": {
                        "address": schema_addr,
                        "size": {"type": "integer", "default": 256, "maximum": 4096},
                    },
                    "required": ["address"],
                },
                bridge_type="rizin",
                modules=("re",),
                destructive=False,
                handler=_rizin_read_hex,
            ),
            ToolSpec(
                name="pwn_checksec",
                description="Run checksec (RELRO/NX/PIE/Canary) on the loaded ELF.",
                parameters={"type": "object", "properties": {}},
                bridge_type="pwn",
                modules=("pwn",),
                destructive=False,
                handler=_pwn_checksec,
            ),
            ToolSpec(
                name="pwn_cyclic",
                description="Generate a De Bruijn cyclic pattern of given length.",
                parameters={
                    "type": "object",
                    "properties": {"length": {"type": "integer", "default": 64, "maximum": 4096}},
                },
                bridge_type="pwn",
                modules=("pwn",),
                destructive=False,
                handler=_pwn_cyclic,
            ),
            ToolSpec(
                name="pwn_rop_search",
                description="Search ROP gadgets matching a textual pattern.",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string", "default": "ret"}},
                    "required": ["query"],
                },
                bridge_type="pwn",
                modules=("pwn",),
                destructive=False,
                handler=_pwn_rop,
            ),
            ToolSpec(
                name="gdb_registers",
                description="Read all CPU registers of the inferior.",
                parameters={"type": "object", "properties": {}},
                bridge_type="gdb",
                modules=("asm",),
                destructive=False,
                handler=_gdb_registers,
            ),
            ToolSpec(
                name="gdb_breakpoint",
                description="Set a breakpoint at a function name or address.",
                parameters={
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
                bridge_type="gdb",
                modules=("asm",),
                destructive=False,
                handler=_gdb_breakpoint,
            ),
            ToolSpec(
                name="gdb_run",
                description="Run/continue the inferior. DESTRUCTIVE — executes code.",
                parameters={"type": "object", "properties": {}},
                bridge_type="gdb",
                modules=("asm",),
                destructive=True,
                handler=_gdb_run,
                category="exec",
            ),
            ToolSpec(
                name="firmware_scan",
                description="Run binwalk magic scan on a firmware blob.",
                parameters={
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
                bridge_type="firmware",
                modules=("firmware",),
                destructive=False,
                handler=_firmware_scan,
            ),
        ]
    }


_REGISTRY: dict[str, ToolSpec] = _build_registry()


def list_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def tools_for_modules(modules: list[str], *, strict: bool = False) -> list[ToolSpec]:
    """Filter tools by allowed modules (Strict mode)."""
    if not strict:
        return list_tools()
    allowed = set(modules)
    return [t for t in list_tools() if any(m in allowed for m in t.modules)]


def to_anthropic_schema(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]


def to_openai_schema(tools: list[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


# ── Dispatcher ───────────────────────────────────────────
async def dispatch(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    anvil_session_ids: dict[str, str],
    agent_session_id: str,
    session_manager: Any,
) -> dict[str, Any]:
    """Resolve and execute a tool call.

    Raises ``AnvilError`` if the tool is unknown or the matching Anvil session
    doesn't exist. The runtime handles the safeguard layer (destructive
    approval) before calling here.
    """
    spec = get_tool(tool_name)
    if spec is None:
        raise AnvilError(f"Unknown tool {tool_name}", code="TOOL_NOT_FOUND")

    started = time.perf_counter()
    error: str | None = None
    result: Any = None
    try:
        if spec.bridge_type is None:
            result = await spec.handler(**arguments)  # type: ignore[arg-type]
        else:
            anvil_sid = arguments.pop("session_id", None) or _resolve_session_id(spec, anvil_session_ids)
            if not anvil_sid:
                raise AnvilError(
                    f"Tool {tool_name} requires a {spec.bridge_type} session — none active",
                    code="SESSION_NOT_FOUND",
                )
            try:
                session = session_manager.get(anvil_sid)
            except SessionNotFound as exc:
                raise AnvilError(str(exc), code="SESSION_NOT_FOUND") from exc
            if session.bridge_type != spec.bridge_type:
                raise AnvilError(
                    f"Session {anvil_sid} is {session.bridge_type}, expected {spec.bridge_type}",
                    code="WRONG_SESSION_TYPE",
                )
            result = await spec.handler(session, **arguments)
    except AnvilError as exc:
        error = exc.message
        raise
    except Exception as exc:  # pragma: no cover — defensive
        error = str(exc)
        logger.exception("Tool %s raised", tool_name)
        raise AnvilError(str(exc), code="BRIDGE_CRASH") from exc
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        size = len(repr(result)) if result is not None else 0
        record_tool_call(
            session_id=agent_session_id,
            tool_name=tool_name,
            arguments=arguments,
            result_size=size,
            duration_ms=duration_ms,
            error=error,
        )
    return {"result": result, "duration_ms": duration_ms}


def _resolve_session_id(spec: ToolSpec, anvil_session_ids: dict[str, str]) -> str | None:
    """Pick an Anvil session_id matching this tool's bridge type."""
    # Direct mapping by bridge type
    by_type = anvil_session_ids.get(spec.bridge_type or "")
    if by_type:
        return by_type
    # Fall back: any of the tool's declared modules → look up "asm","re",etc.
    for module in spec.modules:
        sid = anvil_session_ids.get(module)
        if sid:
            return sid
    return None
