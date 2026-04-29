"""GDB WebSocket handlers — real-time debug interaction.

Registers handlers on the global ws_dispatcher for session_type="gdb".
Messages flow: Client → WS → Dispatcher → GdbBridge → WS → Client.
"""

from __future__ import annotations

import logging

from backend.app.api.ws import ws_dispatcher
from backend.app.bridges.gdb_bridge import GdbBridge
from backend.app.core.exceptions import ValidationError
from backend.app.core.sanitization import sanitize_gdb_input
from backend.app.models.ws import WSMessage
from backend.app.sessions.manager import SessionManager
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Will be set during app lifespan setup
_session_manager: SessionManager | None = None


def init_gdb_ws_handlers(session_manager: SessionManager) -> None:
    """Register all GDB WebSocket handlers. Called during app startup."""
    global _session_manager
    _session_manager = session_manager

    ws_dispatcher.register("gdb.step_into", _handle_step_into)
    ws_dispatcher.register("gdb.step_over", _handle_step_over)
    ws_dispatcher.register("gdb.step_out", _handle_step_out)
    ws_dispatcher.register("gdb.continue", _handle_continue)
    ws_dispatcher.register("gdb.run", _handle_run)
    ws_dispatcher.register("gdb.load", _handle_load)
    ws_dispatcher.register("gdb.breakpoint_set", _handle_breakpoint_set)
    ws_dispatcher.register("gdb.breakpoint_remove", _handle_breakpoint_remove)
    ws_dispatcher.register("gdb.registers", _handle_registers)
    ws_dispatcher.register("gdb.stack", _handle_stack)
    ws_dispatcher.register("gdb.memory", _handle_memory)
    ws_dispatcher.register("gdb.disassemble", _handle_disassemble)
    ws_dispatcher.register("gdb.evaluate", _handle_evaluate)
    ws_dispatcher.register("gdb.execute", _handle_raw_execute)

    logger.info("GDB WebSocket handlers registered (%d commands)", 14)


def _get_bridge(session_id: str) -> GdbBridge:
    """Get GDB bridge for a session from the session manager."""
    if _session_manager is None:
        raise RuntimeError("GDB WS handlers not initialized")
    session = _session_manager.get(session_id)
    if not isinstance(session.bridge, GdbBridge):
        raise ValidationError(f"Session '{session_id}' is not a GDB session")
    return session.bridge


# ── Handlers ─────────────────────────────────────────────


async def _handle_step_into(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    responses = await bridge.step_into()
    return {"action": "step_into", "gdb_responses": responses}


async def _handle_step_over(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    responses = await bridge.step_over()
    return {"action": "step_over", "gdb_responses": responses}


async def _handle_step_out(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    responses = await bridge.step_out()
    return {"action": "step_out", "gdb_responses": responses}


async def _handle_continue(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    responses = await bridge.continue_exec()
    return {"action": "continue", "gdb_responses": responses}


async def _handle_run(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    args = msg.payload.get("args", "")
    responses = await bridge.run(args)
    return {"action": "run", "gdb_responses": responses}


async def _handle_load(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    binary_path = msg.payload.get("binary_path", "")
    if not binary_path:
        raise ValidationError("binary_path is required")
    responses = await bridge.load_binary(binary_path)
    return {"action": "load", "binary_path": binary_path, "gdb_responses": responses}


async def _handle_breakpoint_set(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    location = msg.payload.get("location", "")
    if not location:
        raise ValidationError("location is required")
    responses = await bridge.set_breakpoint(location)
    return {"action": "breakpoint_set", "location": location, "gdb_responses": responses}


async def _handle_breakpoint_remove(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    bp_number = msg.payload.get("bp_number")
    if bp_number is None:
        raise ValidationError("bp_number is required")
    responses = await bridge.remove_breakpoint(int(bp_number))
    return {"action": "breakpoint_remove", "bp_number": bp_number, "gdb_responses": responses}


async def _handle_registers(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    registers = await bridge.get_registers()
    return {"action": "registers", "registers": registers}


async def _handle_stack(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    max_frames = msg.payload.get("max_frames", 64)
    responses = await bridge.get_stack(max_frames)
    return {"action": "stack", "gdb_responses": responses}


async def _handle_memory(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    address = msg.payload.get("address", "")
    size = msg.payload.get("size", 256)
    if not address:
        raise ValidationError("address is required")
    responses = await bridge.read_memory(address, size)
    return {"action": "memory", "address": address, "size": size, "gdb_responses": responses}


async def _handle_disassemble(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    responses = await bridge.disassemble(
        start=msg.payload.get("start"),
        end=msg.payload.get("end"),
        function=msg.payload.get("function"),
    )
    return {"action": "disassemble", "gdb_responses": responses}


async def _handle_evaluate(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    expression = msg.payload.get("expression", "")
    if not expression:
        raise ValidationError("expression is required")
    responses = await bridge.evaluate(expression)
    return {"action": "evaluate", "expression": expression, "gdb_responses": responses}


async def _handle_raw_execute(ws: WebSocket, msg: WSMessage, session_id: str) -> dict:
    bridge = _get_bridge(session_id)
    command = msg.payload.get("command_str", "")
    if not command:
        raise ValidationError("command_str is required")
    command = sanitize_gdb_input(command, "command_str")
    responses = await bridge.execute(command)
    return {"action": "execute", "command": command, "gdb_responses": responses}
