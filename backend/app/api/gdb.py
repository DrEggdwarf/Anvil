"""GDB REST API routes.

All routes require an active GDB session. The session_id maps to a
SessionManager session which owns a GdbBridge instance.
"""

from __future__ import annotations

from backend.app.api.deps import get_session_manager
from backend.app.bridges.gdb_bridge import GdbBridge
from backend.app.core.exceptions import ValidationError
from backend.app.models.gdb import (
    GdbAttachRequest,
    GdbBreakpointConditionRequest,
    GdbBreakpointRequest,
    GdbCatchSignalRequest,
    GdbCatchSyscallRequest,
    GdbDisassembleRequest,
    GdbEvaluateRequest,
    GdbLoadRequest,
    GdbMemoryRequest,
    GdbRawResponse,
    GdbRunRequest,
    GdbSearchMemoryRequest,
    GdbSetRegisterRequest,
    GdbSetVariableRequest,
    GdbUntilRequest,
    GdbWatchpointRequest,
    GdbWriteMemoryRequest,
)
from backend.app.sessions.manager import SessionManager
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/gdb", tags=["gdb"])


def _get_gdb_bridge(session_id: str, sm: SessionManager) -> GdbBridge:
    """Get the GDB bridge for a session. Raises if wrong bridge type."""
    session = sm.get(session_id)
    if not isinstance(session.bridge, GdbBridge):
        raise ValidationError(
            f"Session '{session_id}' is not a GDB session",
            code="WRONG_SESSION_TYPE",
        )
    return session.bridge


# ── Binary loading ───────────────────────────────────────


@router.post("/{session_id}/load", response_model=GdbRawResponse)
async def load_binary(
    session_id: str,
    body: GdbLoadRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Load a binary into the GDB session."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.load_binary(body.binary_path)
    return GdbRawResponse(responses=responses)


# ── Execution control ────────────────────────────────────


@router.post("/{session_id}/run", response_model=GdbRawResponse)
async def run_program(
    session_id: str,
    body: GdbRunRequest = GdbRunRequest(),
    sm: SessionManager = Depends(get_session_manager),
):
    """Start program execution."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.run(body.args)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/continue", response_model=GdbRawResponse)
async def continue_exec(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Continue execution."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.continue_exec()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/step/into", response_model=GdbRawResponse)
async def step_into(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Step into (instruction-level)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.step_into()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/step/over", response_model=GdbRawResponse)
async def step_over(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Step over (instruction-level)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.step_over()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/step/out", response_model=GdbRawResponse)
async def step_out(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Step out of current function."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.step_out()
    return GdbRawResponse(responses=responses)


# ── Breakpoints ──────────────────────────────────────────


@router.post("/{session_id}/breakpoints", response_model=GdbRawResponse)
async def set_breakpoint(
    session_id: str,
    body: GdbBreakpointRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set a breakpoint."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_breakpoint(body.location)
    return GdbRawResponse(responses=responses)


@router.delete("/{session_id}/breakpoints/{bp_number}", response_model=GdbRawResponse)
async def remove_breakpoint(
    session_id: str,
    bp_number: int,
    sm: SessionManager = Depends(get_session_manager),
):
    """Remove a breakpoint by number."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.remove_breakpoint(bp_number)
    return GdbRawResponse(responses=responses)


@router.get("/{session_id}/breakpoints", response_model=GdbRawResponse)
async def list_breakpoints(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List all breakpoints."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.list_breakpoints()
    return GdbRawResponse(responses=responses)


# ── Inspection ───────────────────────────────────────────


@router.get("/{session_id}/registers")
async def get_registers(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Read all register values."""
    bridge = _get_gdb_bridge(session_id, sm)
    registers = await bridge.get_registers()
    return {"registers": registers}


@router.get("/{session_id}/stack")
async def get_stack(
    session_id: str,
    max_frames: int = 64,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get stack frames."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.get_stack(max_frames)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/memory", response_model=GdbRawResponse)
async def read_memory(
    session_id: str,
    body: GdbMemoryRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Read memory at address."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.read_memory(body.address, body.size)
    return GdbRawResponse(responses=responses)


# ── Disassembly & evaluation ─────────────────────────────


@router.post("/{session_id}/disassemble", response_model=GdbRawResponse)
async def disassemble(
    session_id: str,
    body: GdbDisassembleRequest = GdbDisassembleRequest(),
    sm: SessionManager = Depends(get_session_manager),
):
    """Disassemble a function or address range."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.disassemble(
        start=body.start, end=body.end, function=body.function,
    )
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/evaluate", response_model=GdbRawResponse)
async def evaluate(
    session_id: str,
    body: GdbEvaluateRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Evaluate an expression."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.evaluate(body.expression)
    return GdbRawResponse(responses=responses)


# ── Execution control (extended) ─────────────────────────


@router.post("/{session_id}/interrupt", response_model=GdbRawResponse)
async def interrupt(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Interrupt running program."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.interrupt()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/step/source/into", response_model=GdbRawResponse)
async def step_source_into(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Step into (source-level)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.step_source()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/step/source/over", response_model=GdbRawResponse)
async def step_source_over(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Step over (source-level)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.next_source()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/until", response_model=GdbRawResponse)
async def until(
    session_id: str,
    body: GdbUntilRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Continue until a specific location."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.until(body.location)
    return GdbRawResponse(responses=responses)


# ── Breakpoints (extended) ───────────────────────────────


@router.post("/{session_id}/breakpoints/{bp_number}/enable", response_model=GdbRawResponse)
async def enable_breakpoint(
    session_id: str,
    bp_number: int,
    sm: SessionManager = Depends(get_session_manager),
):
    """Enable a breakpoint."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.enable_breakpoint(bp_number)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/breakpoints/{bp_number}/disable", response_model=GdbRawResponse)
async def disable_breakpoint(
    session_id: str,
    bp_number: int,
    sm: SessionManager = Depends(get_session_manager),
):
    """Disable a breakpoint."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.disable_breakpoint(bp_number)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/breakpoints/{bp_number}/condition", response_model=GdbRawResponse)
async def set_breakpoint_condition(
    session_id: str,
    bp_number: int,
    body: GdbBreakpointConditionRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set condition on a breakpoint."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_breakpoint_condition(bp_number, body.condition)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/watchpoints", response_model=GdbRawResponse)
async def set_watchpoint(
    session_id: str,
    body: GdbWatchpointRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set a watchpoint (data breakpoint)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_watchpoint(body.expression, body.access)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/breakpoints/hardware", response_model=GdbRawResponse)
async def set_hardware_breakpoint(
    session_id: str,
    body: GdbBreakpointRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set a hardware breakpoint."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_hardware_breakpoint(body.location)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/breakpoints/temporary", response_model=GdbRawResponse)
async def set_temporary_breakpoint(
    session_id: str,
    body: GdbBreakpointRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set a temporary breakpoint (auto-removed after hit)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_temporary_breakpoint(body.location)
    return GdbRawResponse(responses=responses)


# ── Memory write ─────────────────────────────────────────


@router.post("/{session_id}/memory/write", response_model=GdbRawResponse)
async def write_memory(
    session_id: str,
    body: GdbWriteMemoryRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Write bytes to memory."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.write_memory(body.address, body.hex_data)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/registers/set", response_model=GdbRawResponse)
async def set_register(
    session_id: str,
    body: GdbSetRegisterRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set a register value."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_register(body.register, body.value)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/variables/set", response_model=GdbRawResponse)
async def set_variable(
    session_id: str,
    body: GdbSetVariableRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Set a variable value."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.set_variable(body.variable, body.value)
    return GdbRawResponse(responses=responses)


# ── Search memory ────────────────────────────────────────


@router.post("/{session_id}/memory/search", response_model=GdbRawResponse)
async def search_memory(
    session_id: str,
    body: GdbSearchMemoryRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Search memory for a pattern."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.search_memory(body.start, body.end, body.pattern)
    return GdbRawResponse(responses=responses)


# ── Threads ──────────────────────────────────────────────


@router.get("/{session_id}/threads", response_model=GdbRawResponse)
async def thread_info(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List all threads."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.thread_info()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/threads/{thread_id}", response_model=GdbRawResponse)
async def thread_select(
    session_id: str,
    thread_id: int,
    sm: SessionManager = Depends(get_session_manager),
):
    """Switch to a thread."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.thread_select(thread_id)
    return GdbRawResponse(responses=responses)


# ── Process control ──────────────────────────────────────


@router.post("/{session_id}/attach", response_model=GdbRawResponse)
async def attach(
    session_id: str,
    body: GdbAttachRequest,
    sm: SessionManager = Depends(get_session_manager),
):
    """Attach to a running process."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.attach(body.pid)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/detach", response_model=GdbRawResponse)
async def detach(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Detach from the current process."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.detach()
    return GdbRawResponse(responses=responses)


# ── Process info ─────────────────────────────────────────


@router.get("/{session_id}/memory-map", response_model=GdbRawResponse)
async def memory_map(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get process memory map (vmmap)."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.get_memory_map()
    return GdbRawResponse(responses=responses)


@router.get("/{session_id}/libraries", response_model=GdbRawResponse)
async def shared_libraries(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """List loaded shared libraries."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.get_shared_libraries()
    return GdbRawResponse(responses=responses)


# ── Stack (extended) ─────────────────────────────────────


@router.get("/{session_id}/stack/arguments", response_model=GdbRawResponse)
async def stack_arguments(
    session_id: str,
    frame: int = 0,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get function arguments for a stack frame."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.get_stack_arguments(frame)
    return GdbRawResponse(responses=responses)


@router.get("/{session_id}/stack/variables", response_model=GdbRawResponse)
async def stack_variables(
    session_id: str,
    frame: int = 0,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get local variables for a stack frame."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.get_stack_variables(frame)
    return GdbRawResponse(responses=responses)


# ── Catch events ─────────────────────────────────────────


@router.post("/{session_id}/catch/syscall", response_model=GdbRawResponse)
async def catch_syscall(
    session_id: str,
    body: GdbCatchSyscallRequest = GdbCatchSyscallRequest(),
    sm: SessionManager = Depends(get_session_manager),
):
    """Catch a syscall."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.catch_syscall(body.syscall)
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/catch/signal", response_model=GdbRawResponse)
async def catch_signal(
    session_id: str,
    body: GdbCatchSignalRequest = GdbCatchSignalRequest(),
    sm: SessionManager = Depends(get_session_manager),
):
    """Catch a signal."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.catch_signal(body.signal)
    return GdbRawResponse(responses=responses)


# ── Record & replay ──────────────────────────────────────


@router.post("/{session_id}/record/start", response_model=GdbRawResponse)
async def record_start(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Start recording for reverse debugging."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.record_start()
    return GdbRawResponse(responses=responses)


@router.post("/{session_id}/record/stop", response_model=GdbRawResponse)
async def record_stop(
    session_id: str,
    sm: SessionManager = Depends(get_session_manager),
):
    """Stop recording."""
    bridge = _get_gdb_bridge(session_id, sm)
    responses = await bridge.record_stop()
    return GdbRawResponse(responses=responses)
