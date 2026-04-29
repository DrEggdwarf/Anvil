"""RE tools — stubs, wired per-sprint when the RE module is ready."""

from __future__ import annotations

_STUB = "RE MCP tool not yet wired — implement in the RE sprint."


async def re_analyze(session_id: str, binary_path: str) -> dict:
    """Load and analyze a binary with rizin.

    Returns: {ok, functions_found, strings_found, summary}
    """
    raise NotImplementedError(_STUB)


async def re_functions(session_id: str) -> list[dict]:
    """List all functions identified in the binary.

    Returns: list of {addr, name, size, calls}
    """
    raise NotImplementedError(_STUB)


async def re_disasm(session_id: str, addr_or_name: str) -> list[dict]:
    """Disassemble a function or address range.

    Returns: list of {addr, opcode, operands}
    """
    raise NotImplementedError(_STUB)


async def re_decompile(session_id: str, addr_or_name: str) -> dict:
    """Decompile a function to C via r2ghidra (falls back to rz-dec).

    Returns: {addr, code: str, language: "c", source: str}
    """
    raise NotImplementedError(_STUB)


async def re_strings(session_id: str, min_len: int = 4) -> list[dict]:
    """List strings found in the binary.

    Args:
        min_len: Minimum string length to include.

    Returns: list of {addr, value, encoding}
    """
    raise NotImplementedError(_STUB)


async def re_xrefs(session_id: str, addr: str) -> dict:
    """Get cross-references to and from an address.

    Returns: {to: list[str], from: list[str]}
    """
    raise NotImplementedError(_STUB)
