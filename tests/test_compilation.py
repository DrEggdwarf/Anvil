"""Tests for the compilation bridge — ASM (nasm+ld) and C (gcc)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from backend.app.bridges.compilation import (
    CompilationBridge,
    parse_gcc_errors,
    parse_nasm_errors,
    SECURITY_FLAGS,
)
from backend.app.core.subprocess_manager import SubprocessManager


# ── Error parser tests ───────────────────────────────────


class TestParseNasmErrors:
    def test_single_error(self):
        stderr = "program.asm:5: error: instruction not supported in 64-bit mode"
        errors = parse_nasm_errors(stderr)
        assert len(errors) == 1
        assert errors[0] == {
            "file": "program.asm",
            "line": 5,
            "severity": "error",
            "message": "instruction not supported in 64-bit mode",
        }

    def test_warning(self):
        stderr = "program.asm:10: warning: label alone on a line without a colon might be in error"
        errors = parse_nasm_errors(stderr)
        assert len(errors) == 1
        assert errors[0]["severity"] == "warning"

    def test_multiple_errors(self):
        stderr = (
            "prog.asm:3: error: symbol `foo' undefined\n"
            "prog.asm:8: error: invalid combination of opcode and operands\n"
            "prog.asm:12: warning: label alone\n"
        )
        errors = parse_nasm_errors(stderr)
        assert len(errors) == 3
        assert errors[0]["line"] == 3
        assert errors[1]["line"] == 8
        assert errors[2]["severity"] == "warning"

    def test_empty_stderr(self):
        assert parse_nasm_errors("") == []

    def test_no_match(self):
        assert parse_nasm_errors("some random output") == []


class TestParseGccErrors:
    def test_single_error(self):
        stderr = "program.c:10:5: error: expected ';' before '}' token"
        errors = parse_gcc_errors(stderr)
        assert len(errors) == 1
        assert errors[0] == {
            "file": "program.c",
            "line": 10,
            "column": 5,
            "severity": "error",
            "message": "expected ';' before '}' token",
        }

    def test_warning(self):
        stderr = "prog.c:3:10: warning: implicit declaration of function 'foo'"
        errors = parse_gcc_errors(stderr)
        assert len(errors) == 1
        assert errors[0]["severity"] == "warning"
        assert errors[0]["column"] == 10

    def test_note(self):
        stderr = "prog.c:5:1: note: expected 'int' but got 'char'"
        errors = parse_gcc_errors(stderr)
        assert len(errors) == 1
        assert errors[0]["severity"] == "note"

    def test_multiple(self):
        stderr = (
            "a.c:1:1: error: unknown type name 'foo'\n"
            "a.c:2:5: warning: unused variable 'x'\n"
            "a.c:3:1: error: expected declaration\n"
        )
        errors = parse_gcc_errors(stderr)
        assert len(errors) == 3

    def test_empty(self):
        assert parse_gcc_errors("") == []


# ── CompilationBridge tests ──────────────────────────────


class TestCompileAsm:
    @pytest_asyncio.fixture
    async def bridge(self, tmp_path):
        spm = SubprocessManager()
        return CompilationBridge(spm), str(tmp_path)

    @pytest.mark.asyncio
    async def test_compile_success(self, bridge):
        cb, workspace = bridge
        cb._spm.execute = AsyncMock(
            side_effect=[
                # nasm succeeds
                ("", "", 0),
                # ld succeeds
                ("", "", 0),
            ]
        )
        result = await cb.compile_asm(
            "section .text\nglobal _start\n_start: mov eax, 1\n",
            workspace=workspace,
        )
        assert result["success"] is True
        assert result["stage"] == "link"
        assert result["binary_path"] is not None
        assert result["object_path"] is not None
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_nasm_error(self, bridge):
        cb, workspace = bridge
        cb._spm.execute = AsyncMock(
            return_value=("", "program.asm:5: error: bad instruction", 1)
        )
        result = await cb.compile_asm("bad code", workspace=workspace)
        assert result["success"] is False
        assert result["stage"] == "assemble"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["line"] == 5

    @pytest.mark.asyncio
    async def test_link_error(self, bridge):
        cb, workspace = bridge
        cb._spm.execute = AsyncMock(
            side_effect=[
                ("", "", 0),  # nasm ok
                ("", "undefined reference to `printf'", 1),  # ld fails
            ]
        )
        result = await cb.compile_asm("code", workspace=workspace)
        assert result["success"] is False
        assert result["stage"] == "link"
        assert result["object_path"] is not None

    @pytest.mark.asyncio
    async def test_assemble_only_no_link(self, bridge):
        cb, workspace = bridge
        cb._spm.execute = AsyncMock(return_value=("", "", 0))
        result = await cb.compile_asm("code", workspace=workspace, link=False)
        assert result["success"] is True
        assert result["stage"] == "assemble"
        assert result["binary_path"] is None
        assert result["object_path"] is not None

    @pytest.mark.asyncio
    async def test_use_libc_flag(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_asm("code", workspace=workspace, use_libc=True)
        # Second call should be gcc, not ld
        assert "gcc" in calls[1]

    @pytest.mark.asyncio
    async def test_debug_flags(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_asm("code", workspace=workspace, debug=True)
        nasm_cmd = calls[0]
        assert "-g" in nasm_cmd
        assert "-F" in nasm_cmd

    @pytest.mark.asyncio
    async def test_no_debug(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_asm("code", workspace=workspace, debug=False)
        nasm_cmd = calls[0]
        assert "-g" not in nasm_cmd

    @pytest.mark.asyncio
    async def test_custom_format(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_asm("code", workspace=workspace, fmt="elf32", link=False)
        assert "-felf32" in calls[0]


class TestCompileC:
    @pytest_asyncio.fixture
    async def bridge(self, tmp_path):
        spm = SubprocessManager()
        return CompilationBridge(spm), str(tmp_path)

    @pytest.mark.asyncio
    async def test_compile_success(self, bridge):
        cb, workspace = bridge
        cb._spm.execute = AsyncMock(return_value=("", "", 0))
        result = await cb.compile_c(
            '#include <stdio.h>\nint main() { return 0; }\n',
            workspace=workspace,
        )
        assert result["success"] is True
        assert result["binary_path"] is not None

    @pytest.mark.asyncio
    async def test_compile_error(self, bridge):
        cb, workspace = bridge
        cb._spm.execute = AsyncMock(
            return_value=("", "prog.c:1:1: error: expected ';'\nprog.c:2:5: warning: unused var", 1)
        )
        result = await cb.compile_c("bad code", workspace=workspace)
        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert len(result["warnings"]) == 1

    @pytest.mark.asyncio
    async def test_security_flags(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_c(
            "code",
            workspace=workspace,
            security_flags=["no_pie", "no_canary", "no_nx"],
        )
        gcc_cmd = calls[0]
        assert "-no-pie" in gcc_cmd
        assert "-fno-stack-protector" in gcc_cmd
        assert "execstack" in gcc_cmd

    @pytest.mark.asyncio
    async def test_extra_flags(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_c(
            "code",
            workspace=workspace,
            extra_flags=["-Wall", "-Werror"],
        )
        assert "-Wall" in calls[0]
        assert "-Werror" in calls[0]

    @pytest.mark.asyncio
    async def test_custom_output_name(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_c("code", workspace=workspace, output_name="mybin")
        # output path should end with /mybin
        assert calls[0][-1].endswith("/mybin")

    @pytest.mark.asyncio
    async def test_debug_flags(self, bridge):
        cb, workspace = bridge
        calls = []

        async def mock_execute(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        cb._spm.execute = mock_execute
        await cb.compile_c("code", workspace=workspace, debug=True)
        assert "-g" in calls[0]
        assert "-ggdb" in calls[0]


class TestSecurityFlagsMapping:
    def test_all_keys_exist(self):
        expected = {
            "relro_full", "relro_partial", "nx", "pie", "canary",
            "fortify", "no_pie", "no_canary", "no_nx",
        }
        assert set(SECURITY_FLAGS.keys()) == expected

    def test_no_pie_flag(self):
        assert "-no-pie" in SECURITY_FLAGS["no_pie"]

    def test_pie_flags(self):
        assert "-pie" in SECURITY_FLAGS["pie"]
        assert "-fPIE" in SECURITY_FLAGS["pie"]
