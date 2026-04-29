"""Pwn tools — stubs, wired per-sprint when the Pwn module is ready."""

from __future__ import annotations

_STUB = "Pwn MCP tool not yet wired — implement in the Pwn sprint."


async def pwn_checksec(session_id: str, binary_path: str) -> dict:
    """Run checksec on a binary.

    Returns: {nx, pie, canary, relro, fortify}
    """
    raise NotImplementedError(_STUB)


async def pwn_cyclic(session_id: str, length: int) -> dict:
    """Generate a De Bruijn cyclic pattern.

    Returns: {pattern: str}
    """
    raise NotImplementedError(_STUB)


async def pwn_cyclic_find(session_id: str, value: str) -> dict:
    """Find the offset of a value in a cyclic pattern.

    Args:
        value: Hex string or integer representation of crashed register value.

    Returns: {offset: int}
    """
    raise NotImplementedError(_STUB)


async def pwn_rop_gadgets(
    session_id: str, binary_path: str, pattern: str | None = None
) -> list[dict]:
    """Search for ROP gadgets in a binary.

    Args:
        pattern: Optional instruction pattern to filter (e.g. "pop rdi").

    Returns: list of {addr, gadget}
    """
    raise NotImplementedError(_STUB)


async def pwn_shellcraft(
    session_id: str, arch: str, os: str, shellcode_type: str
) -> dict:
    """Generate shellcode via pwntools shellcraft.

    Args:
        arch: e.g. "amd64", "i386", "arm"
        os: e.g. "linux", "freebsd"
        shellcode_type: e.g. "sh", "execve", "connect"

    Returns: {asm: str, bytes: str}
    """
    raise NotImplementedError(_STUB)
