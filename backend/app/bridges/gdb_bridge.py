"""GDB Bridge — wrapper around pygdbmi for GDB/MI interaction.

This is the reference bridge implementation. All other bridges (RE, Pwn, etc.)
follow the same pattern: inherit BaseBridge, manage subprocess lifecycle,
expose typed commands.

GDB/MI commands reference: https://sourceware.org/gdb/current/onlinedocs/gdb.html/GDB_002fMI.html
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import bridge_registry
from backend.app.core.exceptions import BridgeCrash, BridgeTimeout
from backend.app.core.sanitization import sanitize_gdb_input, validate_file_path

logger = logging.getLogger(__name__)

# GDB/MI response message types
GDB_RESULT = "result"
GDB_CONSOLE = "console"
GDB_NOTIFY = "notify"
GDB_LOG = "log"
GDB_OUTPUT = "output"
GDB_TARGET = "target"


class GdbBridge(BaseBridge):
    """GDB bridge via pygdbmi — manages a GDB subprocess and provides
    structured commands for debugging binaries."""

    bridge_type = "gdb"

    def __init__(self, gdb_command: list[str] | None = None) -> None:
        super().__init__()
        self._gdb_command = gdb_command or ["gdb", "--nx", "--quiet", "--interpreter=mi3"]
        self._controller: Any = None  # pygdbmi.GdbController
        self._loaded_binary: str | None = None
        self._lock = asyncio.Lock()  # Serialize GDB/MI commands

    async def start(self) -> None:
        """Start the GDB subprocess."""
        self.state = BridgeState.STARTING
        try:
            from pygdbmi.gdbcontroller import GdbController
            self._controller = GdbController(command=self._gdb_command)
            self.state = BridgeState.READY
            logger.info("GDB bridge started (pid=%s)", self._controller.gdb_process.pid)
        except Exception as e:
            self.state = BridgeState.ERROR
            raise BridgeCrash("gdb", exit_code=None) from e

    async def stop(self) -> None:
        """Stop the GDB subprocess."""
        self.state = BridgeState.STOPPING
        if self._controller is not None:
            try:
                self._controller.exit()
            except Exception:
                logger.exception("Error exiting GDB")
            finally:
                self._controller = None
        self.state = BridgeState.STOPPED
        logger.info("GDB bridge stopped")

    async def health(self) -> bool:
        """Check if GDB process is alive."""
        if self._controller is None:
            return False
        proc = self._controller.gdb_process
        return proc is not None and proc.poll() is None

    async def execute(self, command: str, **kwargs: Any) -> Any:
        """Execute a raw GDB/MI command and return parsed responses."""
        self._require_ready()
        timeout = kwargs.get("timeout", 10)
        async with self._lock:
            try:
                responses = self._controller.write(
                    command,
                    timeout_sec=timeout,
                    raise_error_on_timeout=True,
                )
                return responses
            except Exception as e:
                if "timeout" in str(e).lower():
                    raise BridgeTimeout("gdb", timeout) from e
                raise

    # ── High-level commands ──────────────────────────────

    async def load_binary(self, binary_path: str, *, allowed_dirs: list[str] | None = None) -> list[dict]:
        """Load a binary into GDB (file command)."""
        self._require_ready()
        validate_file_path(binary_path, allowed_dirs=allowed_dirs, field_name="binary_path")
        sanitize_gdb_input(binary_path, "binary_path")
        responses = await self.execute(f"-file-exec-and-symbols {binary_path}")
        self._loaded_binary = binary_path
        return responses

    async def run(self, args: str = "") -> list[dict]:
        """Start program execution. Stops at first breakpoint or entry."""
        self._require_ready()
        if args:
            sanitize_gdb_input(args, "args")
        cmd = f"-exec-run {args}".strip()
        return await self.execute(cmd)

    async def continue_exec(self) -> list[dict]:
        """Continue execution."""
        self._require_ready()
        return await self.execute("-exec-continue")

    async def step_into(self) -> list[dict]:
        """Step into (si/stepi — instruction-level)."""
        self._require_ready()
        return await self.execute("-exec-step-instruction")

    async def step_over(self) -> list[dict]:
        """Step over (ni/nexti — instruction-level)."""
        self._require_ready()
        return await self.execute("-exec-next-instruction")

    async def step_out(self) -> list[dict]:
        """Step out of current function (finish)."""
        self._require_ready()
        return await self.execute("-exec-finish")

    async def set_breakpoint(self, location: str) -> list[dict]:
        """Set a breakpoint. Location can be address, function, or file:line."""
        self._require_ready()
        sanitize_gdb_input(location, "location")
        return await self.execute(f"-break-insert {location}")

    async def remove_breakpoint(self, bp_number: int) -> list[dict]:
        """Remove a breakpoint by its number."""
        self._require_ready()
        return await self.execute(f"-break-delete {bp_number}")

    async def list_breakpoints(self) -> list[dict]:
        """List all breakpoints."""
        self._require_ready()
        return await self.execute("-break-list")

    async def get_registers(self) -> list[dict]:
        """Read all register values."""
        self._require_ready()
        # First get register names, then values
        names_resp = await self.execute("-data-list-register-names")
        values_resp = await self.execute("-data-list-register-values x")
        return _merge_register_data(names_resp, values_resp)

    async def read_memory(self, address: str, size: int) -> list[dict]:
        """Read memory bytes at address. Returns hex data."""
        self._require_ready()
        sanitize_gdb_input(address, "address")
        return await self.execute(
            f"-data-read-memory-bytes {address} {size}"
        )

    async def get_stack(self, max_frames: int = 64) -> list[dict]:
        """Get stack frames."""
        self._require_ready()
        return await self.execute(f"-stack-list-frames 0 {max_frames}")

    async def get_stack_variables(self, frame: int = 0) -> list[dict]:
        """Get local variables for a given stack frame."""
        self._require_ready()
        await self.execute(f"-stack-select-frame {frame}")
        return await self.execute("-stack-list-locals --all-values")

    async def disassemble(
        self, start: str | None = None, end: str | None = None, function: str | None = None
    ) -> list[dict]:
        """Disassemble a range or function."""
        self._require_ready()
        if function:
            sanitize_gdb_input(function, "function")
            return await self.execute(f'-data-disassemble -a {function} -- 0')
        elif start and end:
            sanitize_gdb_input(start, "start")
            sanitize_gdb_input(end, "end")
            return await self.execute(f'-data-disassemble -s {start} -e {end} -- 0')
        else:
            # Disassemble around $pc
            return await self.execute('-data-disassemble -s "$pc" -e "$pc+64" -- 0')

    async def evaluate(self, expression: str) -> list[dict]:
        """Evaluate an expression in GDB."""
        self._require_ready()
        sanitize_gdb_input(expression, "expression")
        return await self.execute(f"-data-evaluate-expression {expression}")

    async def info_functions(self, pattern: str = "") -> list[dict]:
        """List functions matching pattern (uses console command)."""
        self._require_ready()
        if pattern:
            sanitize_gdb_input(pattern, "pattern")
        cmd = f"info functions {pattern}" if pattern else "info functions"
        return await self.execute(f"-interpreter-exec console \"{cmd}\"")

    # ── Execution control (extended) ─────────────────────

    async def interrupt(self) -> list[dict]:
        """Interrupt a running program (SIGINT)."""
        self._require_ready()
        return await self.execute("-exec-interrupt")

    async def step_source(self) -> list[dict]:
        """Step into (source-level, si the function has debug info)."""
        self._require_ready()
        return await self.execute("-exec-step")

    async def next_source(self) -> list[dict]:
        """Step over (source-level)."""
        self._require_ready()
        return await self.execute("-exec-next")

    async def until(self, location: str) -> list[dict]:
        """Continue until a specific location."""
        self._require_ready()
        sanitize_gdb_input(location, "location")
        return await self.execute(f"-exec-until {location}")

    async def reverse_continue(self) -> list[dict]:
        """Reverse continue (requires record mode)."""
        self._require_ready()
        return await self.execute("-exec-continue --reverse")

    async def reverse_step(self) -> list[dict]:
        """Reverse step instruction."""
        self._require_ready()
        return await self.execute("-exec-step-instruction --reverse")

    # ── Breakpoints (extended) ───────────────────────────

    async def enable_breakpoint(self, bp_number: int) -> list[dict]:
        """Enable a breakpoint."""
        self._require_ready()
        return await self.execute(f"-break-enable {bp_number}")

    async def disable_breakpoint(self, bp_number: int) -> list[dict]:
        """Disable a breakpoint without removing it."""
        self._require_ready()
        return await self.execute(f"-break-disable {bp_number}")

    async def set_breakpoint_condition(self, bp_number: int, condition: str) -> list[dict]:
        """Set a condition on a breakpoint."""
        self._require_ready()
        sanitize_gdb_input(condition, "condition")
        return await self.execute(f"-break-condition {bp_number} {condition}")

    async def set_watchpoint(self, expression: str, access: str = "write") -> list[dict]:
        """Set a watchpoint (data breakpoint).

        access: "write" (-break-watch), "read" (-break-watch -r), "access" (-break-watch -a)
        """
        self._require_ready()
        sanitize_gdb_input(expression, "expression")
        flag = {"read": " -r", "access": " -a", "write": ""}.get(access, "")
        return await self.execute(f"-break-watch{flag} {expression}")

    async def set_hardware_breakpoint(self, location: str) -> list[dict]:
        """Set a hardware breakpoint."""
        self._require_ready()
        sanitize_gdb_input(location, "location")
        return await self.execute(f"-break-insert -h {location}")

    async def set_temporary_breakpoint(self, location: str) -> list[dict]:
        """Set a temporary breakpoint (auto-deleted after first hit)."""
        self._require_ready()
        sanitize_gdb_input(location, "location")
        return await self.execute(f"-break-insert -t {location}")

    # ── Memory & registers (extended) ────────────────────

    async def write_memory(self, address: str, hex_data: str) -> list[dict]:
        """Write bytes to memory. hex_data = hex string (e.g. '41424344')."""
        self._require_ready()
        sanitize_gdb_input(address, "address")
        sanitize_gdb_input(hex_data, "hex_data")
        return await self.execute(f"-data-write-memory-bytes {address} {hex_data}")

    async def set_register(self, register: str, value: str) -> list[dict]:
        """Set a register value (e.g. register='rax', value='0x42')."""
        self._require_ready()
        sanitize_gdb_input(register, "register")
        sanitize_gdb_input(value, "value")
        return await self.execute(f'-data-evaluate-expression "${register} = {value}"')

    async def get_register(self, register: str) -> list[dict]:
        """Get a single register value."""
        self._require_ready()
        sanitize_gdb_input(register, "register")
        return await self.execute(f'-data-evaluate-expression ${register}')

    async def get_changed_registers(self) -> list[dict]:
        """Get list of registers changed since last stop."""
        self._require_ready()
        return await self.execute("-data-list-changed-registers")

    # ── Stack (extended) ─────────────────────────────────

    async def get_stack_arguments(self, frame: int = 0) -> list[dict]:
        """Get function arguments for a stack frame."""
        self._require_ready()
        await self.execute(f"-stack-select-frame {frame}")
        return await self.execute("-stack-list-arguments --all-values 0 0")

    async def get_stack_depth(self) -> list[dict]:
        """Get total stack depth."""
        self._require_ready()
        return await self.execute("-stack-info-depth")

    async def select_frame(self, frame: int) -> list[dict]:
        """Select active stack frame."""
        self._require_ready()
        return await self.execute(f"-stack-select-frame {frame}")

    # ── Threads ──────────────────────────────────────────

    async def thread_info(self) -> list[dict]:
        """List all threads."""
        self._require_ready()
        return await self.execute("-thread-info")

    async def thread_select(self, thread_id: int) -> list[dict]:
        """Switch to a specific thread."""
        self._require_ready()
        return await self.execute(f"-thread-select {thread_id}")

    # ── Process control ──────────────────────────────────

    async def attach(self, pid: int) -> list[dict]:
        """Attach to a running process by PID."""
        self._require_ready()
        return await self.execute(f"-target-attach {pid}")

    async def detach(self) -> list[dict]:
        """Detach from the current process."""
        self._require_ready()
        return await self.execute("-target-detach")

    # ── Process info (security toolkit essentials) ───────

    async def get_memory_map(self) -> list[dict]:
        """Get process memory map (vmmap equivalent)."""
        self._require_ready()
        return await self.execute(
            '-interpreter-exec console "info proc mappings"'
        )

    async def get_shared_libraries(self) -> list[dict]:
        """List loaded shared libraries."""
        self._require_ready()
        return await self.execute(
            '-interpreter-exec console "info sharedlibrary"'
        )

    async def get_signals(self) -> list[dict]:
        """Show signal handling table."""
        self._require_ready()
        return await self.execute(
            '-interpreter-exec console "info signals"'
        )

    async def handle_signal(
        self, signal: str, stop: bool = False, print_: bool = True, pass_: bool = True,
    ) -> list[dict]:
        """Configure signal handling."""
        self._require_ready()
        sanitize_gdb_input(signal, "signal")
        flags = []
        flags.append("stop" if stop else "nostop")
        flags.append("print" if print_ else "noprint")
        flags.append("pass" if pass_ else "nopass")
        return await self.execute(
            f'-interpreter-exec console "handle {signal} {" ".join(flags)}"'
        )

    async def get_file_info(self) -> list[dict]:
        """Get info about loaded file (entry point, sections, etc.)."""
        self._require_ready()
        return await self.execute(
            '-interpreter-exec console "info file"'
        )

    # ── Variables & expressions ──────────────────────────

    async def set_variable(self, variable: str, value: str) -> list[dict]:
        """Set a variable or memory value (e.g. 'x = 42' or '*0x601000 = 0x41')."""
        self._require_ready()
        sanitize_gdb_input(variable, "variable")
        sanitize_gdb_input(value, "value")
        return await self.execute(
            f'-interpreter-exec console "set {variable} = {value}"'
        )

    async def print_variable(self, variable: str, fmt: str = "") -> list[dict]:
        """Print a variable with optional format (/x, /s, /d, etc.)."""
        self._require_ready()
        if fmt:
            return await self.execute(f'-data-evaluate-expression (void*){variable}')
        return await self.execute(f"-data-evaluate-expression {variable}")

    async def get_local_variables(self) -> list[dict]:
        """Get all local variables in current frame."""
        self._require_ready()
        return await self.execute("-stack-list-locals --all-values")

    # ── Search ───────────────────────────────────────────

    async def search_memory(self, start: str, end: str, pattern: str) -> list[dict]:
        """Search memory for a pattern (hex bytes or string)."""
        self._require_ready()
        sanitize_gdb_input(start, "start")
        sanitize_gdb_input(end, "end")
        sanitize_gdb_input(pattern, "pattern")
        return await self.execute(
            f'-interpreter-exec console "find {start}, {end}, {pattern}"'
        )

    # ── Record & replay ─────────────────────────────────

    async def record_start(self) -> list[dict]:
        """Start recording execution for reverse debugging."""
        self._require_ready()
        return await self.execute(
            '-interpreter-exec console "record"'
        )

    async def record_stop(self) -> list[dict]:
        """Stop recording."""
        self._require_ready()
        return await self.execute(
            '-interpreter-exec console "record stop"'
        )

    # ── Catch events ─────────────────────────────────────

    async def catch_syscall(self, syscall: str = "") -> list[dict]:
        """Catch a syscall (all if no name given)."""
        self._require_ready()
        if syscall:
            sanitize_gdb_input(syscall, "syscall")
        cmd = f"catch syscall {syscall}" if syscall else "catch syscall"
        return await self.execute(f'-interpreter-exec console "{cmd}"')

    async def catch_signal(self, signal: str = "") -> list[dict]:
        """Catch a signal."""
        self._require_ready()
        if signal:
            sanitize_gdb_input(signal, "signal")
        cmd = f"catch signal {signal}" if signal else "catch signal"
        return await self.execute(f'-interpreter-exec console "{cmd}"')

    # ── Disassembly (extended) ───────────────────────────

    async def disassemble_with_source(
        self, start: str | None = None, end: str | None = None, function: str | None = None
    ) -> list[dict]:
        """Disassemble with interleaved source (mode 4)."""
        self._require_ready()
        if function:
            sanitize_gdb_input(function, "function")
            return await self.execute(f'-data-disassemble -a {function} -- 4')
        elif start and end:
            sanitize_gdb_input(start, "start")
            sanitize_gdb_input(end, "end")
            return await self.execute(f'-data-disassemble -s {start} -e {end} -- 4')
        else:
            return await self.execute('-data-disassemble -s "$pc" -e "$pc+64" -- 4')

    @property
    def loaded_binary(self) -> str | None:
        return self._loaded_binary


def _merge_register_data(
    names_resp: list[dict], values_resp: list[dict]
) -> list[dict]:
    """Merge register names and values into a single list."""
    names: list[str] = []
    values: list[dict] = []

    for r in names_resp:
        if r.get("type") == GDB_RESULT and "payload" in r:
            payload = r["payload"]
            if isinstance(payload, dict) and "register-names" in payload:
                names = payload["register-names"]
                break

    for r in values_resp:
        if r.get("type") == GDB_RESULT and "payload" in r:
            payload = r["payload"]
            if isinstance(payload, dict) and "register-values" in payload:
                values = payload["register-values"]
                break

    # Merge: zip names with values
    merged = []
    for val in values:
        num = int(val.get("number", -1))
        name = names[num] if 0 <= num < len(names) else f"reg{num}"
        if name:  # Skip empty-named registers
            merged.append({
                "name": name,
                "number": num,
                "value": val.get("value", ""),
            })

    return merged


# Auto-register in the global bridge registry
bridge_registry.register("gdb", GdbBridge)
