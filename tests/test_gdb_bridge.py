"""Tests for GDB Bridge (bridges/gdb_bridge.py).

All tests mock pygdbmi.GdbController — no real GDB needed.
This validates:
1. Bridge lifecycle (start, stop, health)
2. Every GDB command (step, continue, breakpoints, registers, memory, stack...)
3. Error handling (timeout, crash, not ready)
4. Data flow: command → GDB/MI → parsed response
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from backend.app.bridges.base import BridgeState
from backend.app.bridges.gdb_bridge import GdbBridge, _merge_register_data
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady, BridgeTimeout


# ── Mock helpers ─────────────────────────────────────────


def make_mock_controller(responses: list[dict] | None = None):
    """Create a mock GdbController that returns given responses on write()."""
    ctrl = MagicMock()
    ctrl.gdb_process = MagicMock()
    ctrl.gdb_process.pid = 12345
    ctrl.gdb_process.poll.return_value = None  # alive
    ctrl.write.return_value = responses or [
        {"type": "result", "message": "done", "payload": None}
    ]
    return ctrl


def gdb_result(payload: Any = None, message: str = "done") -> dict:
    """Helper to build a GDB/MI result response."""
    return {"type": "result", "message": message, "payload": payload}


def gdb_console(text: str) -> dict:
    return {"type": "console", "message": None, "payload": text}


# ── Fixtures ─────────────────────────────────────────────


@pytest_asyncio.fixture
async def gdb_bridge():
    """A GDB bridge with mocked controller (no real GDB)."""
    bridge = GdbBridge()
    with patch("backend.app.bridges.gdb_bridge.GdbBridge.start") as mock_start:
        # Manually set up the bridge state as if start() succeeded
        bridge._controller = make_mock_controller()
        bridge.state = BridgeState.READY
    yield bridge
    bridge._controller = None
    bridge.state = BridgeState.STOPPED


# ── Lifecycle tests ──────────────────────────────────────


class TestGdbLifecycle:
    @pytest.mark.asyncio
    async def test_start_creates_controller(self):
        bridge = GdbBridge()
        mock_ctrl = make_mock_controller()
        with patch("pygdbmi.gdbcontroller.GdbController", return_value=mock_ctrl):
            await bridge.start()
        assert bridge.state == BridgeState.READY
        assert bridge._controller is mock_ctrl

    @pytest.mark.asyncio
    async def test_start_failure_sets_error(self):
        bridge = GdbBridge()
        with patch("pygdbmi.gdbcontroller.GdbController", side_effect=FileNotFoundError("gdb not found")):
            with pytest.raises(BridgeCrash):
                await bridge.start()
        assert bridge.state == BridgeState.ERROR

    @pytest.mark.asyncio
    async def test_stop_exits_controller(self, gdb_bridge: GdbBridge):
        await gdb_bridge.stop()
        assert gdb_bridge.state == BridgeState.STOPPED
        assert gdb_bridge._controller is None

    @pytest.mark.asyncio
    async def test_stop_handles_exit_error(self, gdb_bridge: GdbBridge):
        gdb_bridge._controller.exit.side_effect = Exception("exit failed")
        await gdb_bridge.stop()  # Should not raise
        assert gdb_bridge.state == BridgeState.STOPPED

    @pytest.mark.asyncio
    async def test_health_when_alive(self, gdb_bridge: GdbBridge):
        assert await gdb_bridge.health() is True

    @pytest.mark.asyncio
    async def test_health_when_dead(self, gdb_bridge: GdbBridge):
        gdb_bridge._controller.gdb_process.poll.return_value = 1  # dead
        assert await gdb_bridge.health() is False

    @pytest.mark.asyncio
    async def test_health_when_no_controller(self):
        bridge = GdbBridge()
        assert await bridge.health() is False


# ── Execute tests ────────────────────────────────────────


class TestGdbExecute:
    @pytest.mark.asyncio
    async def test_execute_calls_write(self, gdb_bridge: GdbBridge):
        result = await gdb_bridge.execute("-exec-run")
        gdb_bridge._controller.write.assert_called_once_with(
            "-exec-run", timeout_sec=10, raise_error_on_timeout=True,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_responses(self, gdb_bridge: GdbBridge):
        expected = [gdb_result({"status": "stopped"})]
        gdb_bridge._controller.write.return_value = expected
        result = await gdb_bridge.execute("-exec-run")
        assert result == expected

    @pytest.mark.asyncio
    async def test_execute_timeout_raises(self, gdb_bridge: GdbBridge):
        gdb_bridge._controller.write.side_effect = Exception("GDB timeout")
        with pytest.raises(BridgeTimeout):
            await gdb_bridge.execute("-exec-run", timeout=5)

    @pytest.mark.asyncio
    async def test_execute_not_ready_raises(self):
        bridge = GdbBridge()
        with pytest.raises(BridgeNotReady):
            await bridge.execute("-exec-run")

    @pytest.mark.asyncio
    async def test_execute_custom_timeout(self, gdb_bridge: GdbBridge):
        await gdb_bridge.execute("-exec-run", timeout=30)
        gdb_bridge._controller.write.assert_called_once_with(
            "-exec-run", timeout_sec=30, raise_error_on_timeout=True,
        )


# ── Load binary ──────────────────────────────────────────


class TestGdbLoadBinary:
    @pytest.mark.asyncio
    async def test_load_binary(self, gdb_bridge: GdbBridge):
        gdb_bridge._controller.write.return_value = [gdb_result()]
        await gdb_bridge.load_binary("/tmp/test_binary")
        gdb_bridge._controller.write.assert_called_once()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-file-exec-and-symbols" in cmd
        assert "/tmp/test_binary" in cmd
        assert gdb_bridge.loaded_binary == "/tmp/test_binary"


# ── Execution control ────────────────────────────────────


class TestGdbExecControl:
    @pytest.mark.asyncio
    async def test_run(self, gdb_bridge: GdbBridge):
        await gdb_bridge.run()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-run" in cmd

    @pytest.mark.asyncio
    async def test_run_with_args(self, gdb_bridge: GdbBridge):
        await gdb_bridge.run("arg1 arg2")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-run" in cmd
        assert "arg1 arg2" in cmd

    @pytest.mark.asyncio
    async def test_continue(self, gdb_bridge: GdbBridge):
        await gdb_bridge.continue_exec()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-continue" in cmd

    @pytest.mark.asyncio
    async def test_step_into(self, gdb_bridge: GdbBridge):
        await gdb_bridge.step_into()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-step-instruction" in cmd

    @pytest.mark.asyncio
    async def test_step_over(self, gdb_bridge: GdbBridge):
        await gdb_bridge.step_over()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-next-instruction" in cmd

    @pytest.mark.asyncio
    async def test_step_out(self, gdb_bridge: GdbBridge):
        await gdb_bridge.step_out()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-finish" in cmd

    @pytest.mark.asyncio
    async def test_enable_record(self, gdb_bridge: GdbBridge):
        await gdb_bridge.enable_record()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "record" in cmd

    @pytest.mark.asyncio
    async def test_reverse_step_into(self, gdb_bridge: GdbBridge):
        await gdb_bridge.reverse_step_into()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "reverse-stepi" in cmd


# ── Breakpoints ──────────────────────────────────────────


class TestGdbBreakpoints:
    @pytest.mark.asyncio
    async def test_set_breakpoint_at_function(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_breakpoint("main")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-insert" in cmd
        assert "main" in cmd

    @pytest.mark.asyncio
    async def test_set_breakpoint_at_address(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_breakpoint("*0x401000")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "*0x401000" in cmd

    @pytest.mark.asyncio
    async def test_remove_breakpoint(self, gdb_bridge: GdbBridge):
        await gdb_bridge.remove_breakpoint(1)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-delete" in cmd
        assert "1" in cmd

    @pytest.mark.asyncio
    async def test_list_breakpoints(self, gdb_bridge: GdbBridge):
        await gdb_bridge.list_breakpoints()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-list" in cmd


# ── Registers ────────────────────────────────────────────


class TestGdbRegisters:
    @pytest.mark.asyncio
    async def test_get_registers(self, gdb_bridge: GdbBridge):
        # Mock two calls: register names then values
        gdb_bridge._controller.write.side_effect = [
            [gdb_result({"register-names": ["rax", "rbx", "rcx", "", "rsp"]})],
            [gdb_result({"register-values": [
                {"number": "0", "value": "0x1"},
                {"number": "1", "value": "0x2"},
                {"number": "2", "value": "0x3"},
                {"number": "3", "value": "0x0"},
                {"number": "4", "value": "0x7fffffffde00"},
            ]})],
        ]
        registers = await gdb_bridge.get_registers()
        assert len(registers) == 4  # Empty name at index 3 is skipped
        assert registers[0]["name"] == "rax"
        assert registers[0]["value"] == "0x1"
        assert registers[3]["name"] == "rsp"
        assert registers[3]["value"] == "0x7fffffffde00"


class TestMergeRegisterData:
    def test_merge_basic(self):
        names_resp = [gdb_result({"register-names": ["rax", "rbx"]})]
        values_resp = [gdb_result({"register-values": [
            {"number": "0", "value": "0x1"},
            {"number": "1", "value": "0x2"},
        ]})]
        merged = _merge_register_data(names_resp, values_resp)
        assert len(merged) == 2
        assert merged[0] == {"name": "rax", "number": 0, "value": "0x1"}
        assert merged[1] == {"name": "rbx", "number": 1, "value": "0x2"}

    def test_merge_skips_empty_names(self):
        names_resp = [gdb_result({"register-names": ["rax", "", "rcx"]})]
        values_resp = [gdb_result({"register-values": [
            {"number": "0", "value": "0x1"},
            {"number": "1", "value": "0x0"},
            {"number": "2", "value": "0x3"},
        ]})]
        merged = _merge_register_data(names_resp, values_resp)
        assert len(merged) == 2  # index 1 (empty name) skipped
        assert merged[0]["name"] == "rax"
        assert merged[1]["name"] == "rcx"

    def test_merge_no_results(self):
        merged = _merge_register_data([], [])
        assert merged == []

    def test_merge_missing_payload(self):
        names_resp = [{"type": "console", "payload": "whatever"}]
        values_resp = [{"type": "console", "payload": "whatever"}]
        merged = _merge_register_data(names_resp, values_resp)
        assert merged == []


# ── Memory ───────────────────────────────────────────────


class TestGdbMemory:
    @pytest.mark.asyncio
    async def test_read_memory(self, gdb_bridge: GdbBridge):
        await gdb_bridge.read_memory("0x401000", 64)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-data-read-memory-bytes" in cmd
        assert "0x401000" in cmd
        assert "64" in cmd


# ── Stack ────────────────────────────────────────────────


class TestGdbStack:
    @pytest.mark.asyncio
    async def test_get_stack(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_stack(32)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-stack-list-frames" in cmd
        assert "32" in cmd

    @pytest.mark.asyncio
    async def test_get_stack_default(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_stack()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "64" in cmd  # default max frames

    @pytest.mark.asyncio
    async def test_get_stack_variables(self, gdb_bridge: GdbBridge):
        gdb_bridge._controller.write.side_effect = [
            [gdb_result()],  # stack-select-frame
            [gdb_result({"locals": [{"name": "x", "value": "42"}]})],
        ]
        result = await gdb_bridge.get_stack_variables(frame=0)
        # Should have called -stack-select-frame then -stack-list-locals
        calls = gdb_bridge._controller.write.call_args_list
        assert "-stack-select-frame" in calls[0][0][0]
        assert "-stack-list-locals" in calls[1][0][0]


# ── Disassembly ──────────────────────────────────────────


class TestGdbDisassemble:
    @pytest.mark.asyncio
    async def test_disassemble_function(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disassemble(function="main")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-data-disassemble" in cmd
        assert "main" in cmd

    @pytest.mark.asyncio
    async def test_disassemble_range(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disassemble(start="0x401000", end="0x401040")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "0x401000" in cmd
        assert "0x401040" in cmd

    @pytest.mark.asyncio
    async def test_disassemble_default_pc(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disassemble()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "$pc" in cmd


# ── Evaluate ─────────────────────────────────────────────


class TestGdbEvaluate:
    @pytest.mark.asyncio
    async def test_evaluate(self, gdb_bridge: GdbBridge):
        await gdb_bridge.evaluate("$rax + 1")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-data-evaluate-expression" in cmd
        assert "$rax + 1" in cmd


# ── Info functions ───────────────────────────────────────


class TestGdbInfoFunctions:
    @pytest.mark.asyncio
    async def test_info_functions_no_pattern(self, gdb_bridge: GdbBridge):
        await gdb_bridge.info_functions()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "info functions" in cmd

    @pytest.mark.asyncio
    async def test_info_functions_with_pattern(self, gdb_bridge: GdbBridge):
        await gdb_bridge.info_functions("main")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "info functions main" in cmd


# ── Extended execution control ───────────────────────────


class TestGdbExtendedExecution:
    @pytest.mark.asyncio
    async def test_interrupt(self, gdb_bridge: GdbBridge):
        await gdb_bridge.interrupt()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-interrupt" in cmd

    @pytest.mark.asyncio
    async def test_step_source(self, gdb_bridge: GdbBridge):
        await gdb_bridge.step_source()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert cmd == "-exec-step"

    @pytest.mark.asyncio
    async def test_next_source(self, gdb_bridge: GdbBridge):
        await gdb_bridge.next_source()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert cmd == "-exec-next"

    @pytest.mark.asyncio
    async def test_until(self, gdb_bridge: GdbBridge):
        await gdb_bridge.until("*0x401050")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-exec-until" in cmd
        assert "0x401050" in cmd

    @pytest.mark.asyncio
    async def test_reverse_continue(self, gdb_bridge: GdbBridge):
        await gdb_bridge.reverse_continue()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "--reverse" in cmd
        assert "-exec-continue" in cmd

    @pytest.mark.asyncio
    async def test_reverse_step(self, gdb_bridge: GdbBridge):
        await gdb_bridge.reverse_step()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "--reverse" in cmd


# ── Extended breakpoints ─────────────────────────────────


class TestGdbExtendedBreakpoints:
    @pytest.mark.asyncio
    async def test_enable_breakpoint(self, gdb_bridge: GdbBridge):
        await gdb_bridge.enable_breakpoint(3)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-enable 3" in cmd

    @pytest.mark.asyncio
    async def test_disable_breakpoint(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disable_breakpoint(3)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-disable 3" in cmd

    @pytest.mark.asyncio
    async def test_set_breakpoint_condition(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_breakpoint_condition(1, "$rax == 0x42")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-condition 1" in cmd
        assert "$rax == 0x42" in cmd

    @pytest.mark.asyncio
    async def test_watchpoint_write(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_watchpoint("*0x601000")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-watch" in cmd
        assert "0x601000" in cmd

    @pytest.mark.asyncio
    async def test_watchpoint_read(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_watchpoint("*0x601000", access="read")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-watch -r" in cmd

    @pytest.mark.asyncio
    async def test_watchpoint_access(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_watchpoint("*0x601000", access="access")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-watch -a" in cmd

    @pytest.mark.asyncio
    async def test_hardware_breakpoint(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_hardware_breakpoint("*0x401000")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-insert -h" in cmd

    @pytest.mark.asyncio
    async def test_temporary_breakpoint(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_temporary_breakpoint("main")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-break-insert -t" in cmd


# ── Memory & registers (extended) ────────────────────────


class TestGdbExtendedMemory:
    @pytest.mark.asyncio
    async def test_write_memory(self, gdb_bridge: GdbBridge):
        await gdb_bridge.write_memory("0x601000", "41424344")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-data-write-memory-bytes" in cmd
        assert "0x601000" in cmd
        assert "41424344" in cmd

    @pytest.mark.asyncio
    async def test_set_register(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_register("rax", "0x42")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-data-evaluate-expression" in cmd

    @pytest.mark.asyncio
    async def test_get_register(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_register("rip")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "$rip" in cmd

    @pytest.mark.asyncio
    async def test_get_changed_registers(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_changed_registers()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-data-list-changed-registers" in cmd

    @pytest.mark.asyncio
    async def test_search_memory(self, gdb_bridge: GdbBridge):
        await gdb_bridge.search_memory("0x400000", "0x500000", "0x41414141")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "find" in cmd
        assert "0x400000" in cmd


# ── Stack (extended) ─────────────────────────────────────


class TestGdbExtendedStack:
    @pytest.mark.asyncio
    async def test_get_stack_arguments(self, gdb_bridge: GdbBridge):
        gdb_bridge._controller.write.side_effect = [
            [gdb_result()],  # select frame
            [gdb_result({"stack-args": []})],
        ]
        await gdb_bridge.get_stack_arguments(frame=2)
        calls = gdb_bridge._controller.write.call_args_list
        assert "-stack-select-frame 2" in calls[0][0][0]
        assert "-stack-list-arguments" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_get_stack_depth(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_stack_depth()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-stack-info-depth" in cmd

    @pytest.mark.asyncio
    async def test_select_frame(self, gdb_bridge: GdbBridge):
        await gdb_bridge.select_frame(5)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-stack-select-frame 5" in cmd


# ── Threads ──────────────────────────────────────────────


class TestGdbThreads:
    @pytest.mark.asyncio
    async def test_thread_info(self, gdb_bridge: GdbBridge):
        await gdb_bridge.thread_info()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-thread-info" in cmd

    @pytest.mark.asyncio
    async def test_thread_select(self, gdb_bridge: GdbBridge):
        await gdb_bridge.thread_select(3)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-thread-select 3" in cmd


# ── Process control ──────────────────────────────────────


class TestGdbProcessControl:
    @pytest.mark.asyncio
    async def test_attach(self, gdb_bridge: GdbBridge):
        await gdb_bridge.attach(1234)
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-target-attach 1234" in cmd

    @pytest.mark.asyncio
    async def test_detach(self, gdb_bridge: GdbBridge):
        await gdb_bridge.detach()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-target-detach" in cmd

    @pytest.mark.asyncio
    async def test_get_memory_map(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_memory_map()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "info proc mappings" in cmd

    @pytest.mark.asyncio
    async def test_get_shared_libraries(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_shared_libraries()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "info sharedlibrary" in cmd

    @pytest.mark.asyncio
    async def test_get_signals(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_signals()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "info signals" in cmd

    @pytest.mark.asyncio
    async def test_get_file_info(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_file_info()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "info file" in cmd


# ── Variables & expressions ──────────────────────────────


class TestGdbVariables:
    @pytest.mark.asyncio
    async def test_set_variable(self, gdb_bridge: GdbBridge):
        await gdb_bridge.set_variable("x", "42")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "set x = 42" in cmd

    @pytest.mark.asyncio
    async def test_get_local_variables(self, gdb_bridge: GdbBridge):
        await gdb_bridge.get_local_variables()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-stack-list-locals" in cmd


# ── Record & replay ──────────────────────────────────────


class TestGdbRecord:
    @pytest.mark.asyncio
    async def test_record_start(self, gdb_bridge: GdbBridge):
        await gdb_bridge.record_start()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "record" in cmd

    @pytest.mark.asyncio
    async def test_record_stop(self, gdb_bridge: GdbBridge):
        await gdb_bridge.record_stop()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "record stop" in cmd


# ── Catch events ─────────────────────────────────────────


class TestGdbCatch:
    @pytest.mark.asyncio
    async def test_catch_syscall(self, gdb_bridge: GdbBridge):
        await gdb_bridge.catch_syscall("write")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "catch syscall write" in cmd

    @pytest.mark.asyncio
    async def test_catch_syscall_all(self, gdb_bridge: GdbBridge):
        await gdb_bridge.catch_syscall()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "catch syscall" in cmd

    @pytest.mark.asyncio
    async def test_catch_signal(self, gdb_bridge: GdbBridge):
        await gdb_bridge.catch_signal("SIGSEGV")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "catch signal SIGSEGV" in cmd


# ── Disassembly (extended) ───────────────────────────────


class TestGdbDisassembleExtended:
    @pytest.mark.asyncio
    async def test_disassemble_with_source_function(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disassemble_with_source(function="main")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-- 4" in cmd
        assert "main" in cmd

    @pytest.mark.asyncio
    async def test_disassemble_with_source_range(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disassemble_with_source(start="0x401000", end="0x401100")
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-- 4" in cmd

    @pytest.mark.asyncio
    async def test_disassemble_with_source_default(self, gdb_bridge: GdbBridge):
        await gdb_bridge.disassemble_with_source()
        cmd = gdb_bridge._controller.write.call_args[0][0]
        assert "-- 4" in cmd
        assert "$pc" in cmd
