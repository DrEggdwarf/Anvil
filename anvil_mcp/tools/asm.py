"""ASM/GDB tools — stubs, wired per-sprint when the GDB module is ready."""

from __future__ import annotations

_STUB = "GDB MCP tool not yet wired — implement in the ASM sprint."


async def gdb_load(session_id: str, binary_path: str) -> dict:
    """Load a binary into a GDB session.

    Returns: {ok, arch, entry_point, size}
    """
    raise NotImplementedError(_STUB)


async def gdb_run(session_id: str) -> dict:
    """Run (or continue) the loaded binary under GDB.

    Returns: {ok, stopped_at, reason}
    """
    raise NotImplementedError(_STUB)


async def gdb_step(session_id: str, mode: str = "into") -> dict:
    """Step the debugged process.

    Args:
        mode: "into" | "over" | "out" | "back"

    Returns: {ok, line, file, addr}
    """
    raise NotImplementedError(_STUB)


async def gdb_breakpoint(session_id: str, addr_or_line: str, action: str = "set") -> dict:
    """Set or delete a breakpoint.

    Args:
        action: "set" | "delete"

    Returns: {ok, bp_id}
    """
    raise NotImplementedError(_STUB)


async def gdb_registers(session_id: str) -> list[dict]:
    """Get all CPU register values.

    Returns: list of {name, value, hex}
    """
    raise NotImplementedError(_STUB)


async def gdb_memory(session_id: str, addr: str, length: int = 64) -> dict:
    """Read memory at address.

    Returns: {addr, hex, ascii}
    """
    raise NotImplementedError(_STUB)


async def gdb_disasm(session_id: str, addr: str, count: int = 16) -> list[dict]:
    """Disassemble N instructions at address.

    Returns: list of {addr, opcode, operands}
    """
    raise NotImplementedError(_STUB)
