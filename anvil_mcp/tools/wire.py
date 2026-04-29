"""Wire/ICS protocol tools — stubs, wired per-sprint when the Wire module is ready."""

from __future__ import annotations

_STUB = "Wire MCP tool not yet wired — implement in the Wire/ICS sprint."


async def wire_load_pcap(
    session_id: str, pcap_path: str, protocol: str = "modbus"
) -> dict:
    """Load and parse a protocol capture file.

    Args:
        protocol: "modbus" | "dnp3" | "iec104"

    Returns: {ok, frame_count, protocols}
    """
    raise NotImplementedError(_STUB)


async def wire_decode_frame(session_id: str, frame_index: int) -> dict:
    """Decode a single captured frame into human-readable fields.

    Returns: {raw_hex, fields: dict, human: str, notes: list[str]}
    """
    raise NotImplementedError(_STUB)


async def wire_send(session_id: str, host: str, port: int, frame_dict: dict) -> dict:
    """Craft and send a protocol frame to a target device.

    Returns: {ok, response_hex, response_fields}
    """
    raise NotImplementedError(_STUB)


async def wire_replay(
    session_id: str,
    frame_index: int,
    count: int,
    interval_ms: int = 0,
) -> list[dict]:
    """Replay a captured frame N times against the current target.

    Returns: list of {attempt, ok, response}
    """
    raise NotImplementedError(_STUB)
