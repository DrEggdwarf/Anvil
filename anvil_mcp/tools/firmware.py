"""Firmware tools — stubs, wired per-sprint when the Firmware module is ready."""

from __future__ import annotations

_STUB = "Firmware MCP tool not yet wired — implement in the Firmware sprint."


async def firmware_scan(session_id: str, blob_path: str) -> list[dict]:
    """Scan a firmware blob for known signatures (binwalk).

    Returns: list of {offset, description, module, entropy}
    """
    raise NotImplementedError(_STUB)


async def firmware_extract(session_id: str, blob_path: str) -> dict:
    """Extract embedded filesystems and components from a firmware blob.

    Returns: {ok, output_dir, file_tree: list[str]}
    """
    raise NotImplementedError(_STUB)


async def firmware_entropy(session_id: str, blob_path: str) -> dict:
    """Compute block-level entropy across the firmware blob.

    High entropy regions indicate encryption or compression.

    Returns: {chart: list[{offset, entropy}]}
    """
    raise NotImplementedError(_STUB)


async def firmware_triage(session_id: str, extracted_dir: str) -> list[dict]:
    """Triage extracted firmware contents for security findings.

    Looks for hardcoded credentials, known-vulnerable binaries,
    world-writable files, SUID binaries, etc.

    Returns: list of {file, severity, finding_type, snippet}
    """
    raise NotImplementedError(_STUB)
