"""Tests for Rizin Bridge — comprehensive RE via rzpipe.

All tests mock rzpipe — no real rizin needed.
Validates: lifecycle, analysis, functions, disassembly, strings,
imports/exports, xrefs, search, write/patch, ESIL, graphs, comments, flags.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from backend.app.bridges.base import BridgeState
from backend.app.bridges.rizin_bridge import RizinBridge
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady


# ── Mock helpers ─────────────────────────────────────────


def make_mock_pipe():
    """Create a mock rzpipe handle — plain MagicMock, no side_effect."""
    pipe = MagicMock()
    pipe.cmd = MagicMock(return_value="")
    pipe.cmdj = MagicMock(return_value=[])
    pipe.quit = MagicMock()
    return pipe


@pytest_asyncio.fixture
async def rizin():
    """Rizin bridge with mocked rzpipe (no real rizin)."""
    bridge = RizinBridge(binary_path="/tmp/test_bin")
    bridge._pipe = make_mock_pipe()
    bridge.state = BridgeState.READY
    yield bridge
    bridge._pipe = None
    bridge.state = BridgeState.STOPPED


# ── Lifecycle ────────────────────────────────────────────


class TestRizinLifecycle:
    @pytest.mark.asyncio
    async def test_start_opens_pipe(self):
        bridge = RizinBridge(binary_path="/tmp/test")
        mock_pipe = make_mock_pipe()
        mock_rz = MagicMock()
        mock_rz.open.return_value = mock_pipe
        with patch.dict("sys.modules", {"rzpipe": mock_rz}):
            await bridge.start()
        assert bridge.state == BridgeState.READY
        assert bridge._pipe is mock_pipe

    @pytest.mark.asyncio
    async def test_start_failure(self):
        bridge = RizinBridge()
        mock_rz = MagicMock()
        mock_rz.open.side_effect = FileNotFoundError("rizin not found")
        with patch.dict("sys.modules", {"rzpipe": mock_rz}):
            with pytest.raises(BridgeCrash):
                await bridge.start()
        assert bridge.state == BridgeState.ERROR

    @pytest.mark.asyncio
    async def test_stop_quits_pipe(self, rizin: RizinBridge):
        await rizin.stop()
        assert rizin.state == BridgeState.STOPPED
        assert rizin._pipe is None

    @pytest.mark.asyncio
    async def test_stop_handles_error(self, rizin: RizinBridge):
        rizin._pipe.quit.side_effect = Exception("quit failed")
        await rizin.stop()  # Should not raise
        assert rizin.state == BridgeState.STOPPED

    @pytest.mark.asyncio
    async def test_health_when_alive(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "5.8.0"
        assert await rizin.health() is True

    @pytest.mark.asyncio
    async def test_health_no_pipe(self):
        bridge = RizinBridge()
        assert await bridge.health() is False

    @pytest.mark.asyncio
    async def test_execute_requires_ready(self):
        bridge = RizinBridge()
        with pytest.raises(BridgeNotReady):
            await bridge.execute("?V")


# ── Analysis ─────────────────────────────────────────────


class TestRizinAnalysis:
    @pytest.mark.asyncio
    async def test_analyze_default(self, rizin: RizinBridge):
        await rizin.analyze()
        rizin._pipe.cmd.assert_called_with("aaa")
        assert rizin.is_analyzed is True

    @pytest.mark.asyncio
    async def test_analyze_levels(self, rizin: RizinBridge):
        for level in ("aa", "aaa", "aaaa"):
            await rizin.analyze(level)
            rizin._pipe.cmd.assert_called_with(level)

    @pytest.mark.asyncio
    async def test_analyze_invalid_level_defaults(self, rizin: RizinBridge):
        await rizin.analyze("invalid")
        rizin._pipe.cmd.assert_called_with("aaa")

    @pytest.mark.asyncio
    async def test_open_binary(self, rizin: RizinBridge):
        await rizin.open_binary("/tmp/new_bin")
        rizin._pipe.cmd.assert_called_with("o /tmp/new_bin")
        assert rizin.binary_path == "/tmp/new_bin"
        assert rizin.is_analyzed is False


# ── Binary info ──────────────────────────────────────────


class TestRizinBinaryInfo:
    @pytest.mark.asyncio
    async def test_binary_info(self, rizin: RizinBridge):
        expected = {"arch": "x86", "bits": 64, "os": "linux"}
        rizin._pipe.cmdj.return_value = expected
        result = await rizin.binary_info()
        rizin._pipe.cmdj.assert_called_with("iIj")
        assert result == expected

    @pytest.mark.asyncio
    async def test_file_info(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = {"core": {}, "bin": {}}
        await rizin.file_info()
        rizin._pipe.cmdj.assert_called_with("ij")

    @pytest.mark.asyncio
    async def test_entry_points(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"vaddr": 0x401000}]
        result = await rizin.entry_points()
        rizin._pipe.cmdj.assert_called_with("iej")
        assert len(result) == 1


# ── Functions ────────────────────────────────────────────


class TestRizinFunctions:
    @pytest.mark.asyncio
    async def test_list_functions(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"offset": 0x401000, "name": "main", "size": 50},
            {"offset": 0x401050, "name": "_start", "size": 20},
        ]
        result = await rizin.functions()
        assert len(result) == 2
        assert result[0]["name"] == "main"

    @pytest.mark.asyncio
    async def test_function_info(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"offset": 0x401000, "name": "main", "nargs": 2}]
        result = await rizin.function_info("0x401000")
        rizin._pipe.cmdj.assert_called_with("afij @ 0x401000")
        assert result["name"] == "main"

    @pytest.mark.asyncio
    async def test_function_info_empty(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = []
        result = await rizin.function_info("0xbadaddr")
        assert result == {}

    @pytest.mark.asyncio
    async def test_xrefs_to(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"from": 0x401050, "type": "CALL"}]
        result = await rizin.function_xrefs_to("0x401000")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_xrefs_from(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"to": 0x401000, "type": "CALL"}]
        result = await rizin.function_xrefs_from("0x401050")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_rename_function(self, rizin: RizinBridge):
        await rizin.rename_function("0x401000", "my_main")
        rizin._pipe.cmd.assert_called_with("afn my_main @ 0x401000")


# ── Disassembly ──────────────────────────────────────────


class TestRizinDisassembly:
    @pytest.mark.asyncio
    async def test_disassemble_function(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = {
            "ops": [
                {"offset": 0x401000, "opcode": "push rbp"},
                {"offset": 0x401001, "opcode": "mov rbp, rsp"},
            ]
        }
        result = await rizin.disassemble_function("0x401000")
        assert len(result) == 2
        assert result[0]["opcode"] == "push rbp"

    @pytest.mark.asyncio
    async def test_disassemble_n_instructions(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"offset": 0x401000, "opcode": "nop"},
        ]
        await rizin.disassemble("0x401000", count=10)
        rizin._pipe.cmdj.assert_called_with("pdj 10 @ 0x401000")

    @pytest.mark.asyncio
    async def test_disassemble_bytes(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"offset": 0x401000, "opcode": "nop"}]
        await rizin.disassemble_bytes("0x401000", nbytes=128)
        rizin._pipe.cmdj.assert_called_with("pDj 128 @ 0x401000")

    @pytest.mark.asyncio
    async def test_disassemble_text(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "push rbp\nmov rbp, rsp\n"
        result = await rizin.disassemble_text("0x401000", count=5)
        rizin._pipe.cmd.assert_called_with("pi 5 @ 0x401000")
        assert "push rbp" in result


# ── Decompiler ───────────────────────────────────────────


class TestRizinDecompile:
    @pytest.mark.asyncio
    async def test_decompile_with_ghidra(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "int main(void) {\n  return 0;\n}\n"
        result = await rizin.decompile("0x401000")
        rizin._pipe.cmd.assert_called_with("pdg @ 0x401000")
        assert "main" in result

    @pytest.mark.asyncio
    async def test_decompile_fallback_to_pdd(self, rizin: RizinBridge):
        calls = []

        def mock_cmd(cmd):
            calls.append(cmd)
            if cmd.startswith("pdg"):
                return "Cannot find function"
            return "decompiled output"

        rizin._pipe.cmd.side_effect = mock_cmd
        await rizin.decompile("0x401000")
        assert len(calls) == 2
        assert calls[1].startswith("pdd")


# ── Strings ──────────────────────────────────────────────


class TestRizinStrings:
    @pytest.mark.asyncio
    async def test_strings(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"vaddr": 0x402000, "string": "Hello, World!", "size": 14},
        ]
        result = await rizin.strings()
        assert len(result) == 1
        assert result[0]["string"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_strings_all(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"vaddr": 0x200, "string": "/lib64/ld-linux"},
        ]
        result = await rizin.strings_all()
        rizin._pipe.cmdj.assert_called_with("izzj")
        assert len(result) == 1


# ── Imports / exports / symbols ──────────────────────────


class TestRizinImportsExports:
    @pytest.mark.asyncio
    async def test_imports(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"name": "puts", "bind": "GLOBAL", "type": "FUNC", "plt": 0x401020},
        ]
        result = await rizin.imports()
        rizin._pipe.cmdj.assert_called_with("iij")
        assert result[0]["name"] == "puts"

    @pytest.mark.asyncio
    async def test_exports(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"name": "main", "vaddr": 0x401060},
        ]
        await rizin.exports()
        rizin._pipe.cmdj.assert_called_with("iEj")

    @pytest.mark.asyncio
    async def test_symbols(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"name": "_start", "vaddr": 0x401000}]
        await rizin.symbols()
        rizin._pipe.cmdj.assert_called_with("isj")


# ── Sections / segments / relocations ────────────────────


class TestRizinSections:
    @pytest.mark.asyncio
    async def test_sections(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"name": ".text", "size": 16, "vaddr": 0x401000, "perm": "r-x"},
        ]
        result = await rizin.sections()
        rizin._pipe.cmdj.assert_called_with("iSj")
        assert result[0]["name"] == ".text"

    @pytest.mark.asyncio
    async def test_segments(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"name": "LOAD0", "size": 0x1000}]
        await rizin.segments()
        rizin._pipe.cmdj.assert_called_with("iSSj")

    @pytest.mark.asyncio
    async def test_relocations(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"name": "puts", "type": "SET_64"}]
        await rizin.relocations()
        rizin._pipe.cmdj.assert_called_with("irj")


# ── Classes / headers / libraries ────────────────────────


class TestRizinMetadata:
    @pytest.mark.asyncio
    async def test_classes(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = []
        await rizin.classes()
        rizin._pipe.cmdj.assert_called_with("icj")

    @pytest.mark.asyncio
    async def test_headers(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = []
        await rizin.headers()
        rizin._pipe.cmdj.assert_called_with("ihj")

    @pytest.mark.asyncio
    async def test_libraries(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = ["libc.so.6"]
        await rizin.libraries()
        rizin._pipe.cmdj.assert_called_with("ilj")


# ── Memory / hex ─────────────────────────────────────────


class TestRizinMemory:
    @pytest.mark.asyncio
    async def test_read_hex(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [0x41, 0x42, 0x43, 0x44]
        result = await rizin.read_hex("0x401000", 4)
        rizin._pipe.cmdj.assert_called_with("pxj 4 @ 0x401000")
        assert result == [0x41, 0x42, 0x43, 0x44]

    @pytest.mark.asyncio
    async def test_read_hex_text(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "0x401000  4142 4344  ABCD\n"
        result = await rizin.read_hex_text("0x401000", 4)
        assert "ABCD" in result

    @pytest.mark.asyncio
    async def test_print_string(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "Hello, World!\n"
        await rizin.print_string("0x402000")
        rizin._pipe.cmd.assert_called_with("ps @ 0x402000")


# ── Write / patch ────────────────────────────────────────


class TestRizinWrite:
    @pytest.mark.asyncio
    async def test_write_hex(self, rizin: RizinBridge):
        await rizin.write_hex("0x401000", "90909090")
        rizin._pipe.cmd.assert_called_with("wx 90909090 @ 0x401000")

    @pytest.mark.asyncio
    async def test_write_string(self, rizin: RizinBridge):
        await rizin.write_string("0x402000", "pwned")
        rizin._pipe.cmd.assert_called_with("w pwned @ 0x402000")

    @pytest.mark.asyncio
    async def test_write_assembly(self, rizin: RizinBridge):
        await rizin.write_assembly("0x401000", "nop")
        rizin._pipe.cmd.assert_called_with("wa nop @ 0x401000")

    @pytest.mark.asyncio
    async def test_nop_fill(self, rizin: RizinBridge):
        await rizin.nop_fill("0x401000", count=4)
        rizin._pipe.cmd.assert_called_with("wx 90909090 @ 0x401000")


# ── Search ───────────────────────────────────────────────


class TestRizinSearch:
    @pytest.mark.asyncio
    async def test_search_hex(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"offset": 0x401010}]
        result = await rizin.search_hex("9090")
        rizin._pipe.cmdj.assert_called_with("/xj 9090")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_string(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"offset": 0x402000}]
        await rizin.search_string("password")
        rizin._pipe.cmdj.assert_called_with("/j password")

    @pytest.mark.asyncio
    async def test_search_rop(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [
            {"opcode": "pop rdi; ret", "offset": 0x401234},
        ]
        await rizin.search_rop("pop rdi")
        rizin._pipe.cmdj.assert_called_with("/Rj pop rdi")

    @pytest.mark.asyncio
    async def test_search_rop_all(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = []
        await rizin.search_rop()
        rizin._pipe.cmdj.assert_called_with("/Rj")

    @pytest.mark.asyncio
    async def test_search_crypto(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = []
        await rizin.search_crypto()
        rizin._pipe.cmdj.assert_called_with("/caj")


# ── Flags & comments ─────────────────────────────────────


class TestRizinFlagsComments:
    @pytest.mark.asyncio
    async def test_flags(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"name": "sym.main", "offset": 0x401000}]
        result = await rizin.flags()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_set_flag(self, rizin: RizinBridge):
        await rizin.set_flag("vuln", "0x401000", size=10)
        rizin._pipe.cmd.assert_called_with("f vuln 10 @ 0x401000")

    @pytest.mark.asyncio
    async def test_add_comment(self, rizin: RizinBridge):
        await rizin.add_comment("0x401000", "buffer overflow here")
        rizin._pipe.cmd.assert_called_with("CC buffer overflow here @ 0x401000")

    @pytest.mark.asyncio
    async def test_get_comments(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"offset": 0x401000, "name": "test"}]
        await rizin.get_comments()
        rizin._pipe.cmdj.assert_called_with("CCj")

    @pytest.mark.asyncio
    async def test_delete_comment(self, rizin: RizinBridge):
        await rizin.delete_comment("0x401000")
        rizin._pipe.cmd.assert_called_with("CC- @ 0x401000")


# ── Types ────────────────────────────────────────────────


class TestRizinTypes:
    @pytest.mark.asyncio
    async def test_types(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = []
        await rizin.types()
        rizin._pipe.cmdj.assert_called_with("tj")


# ── Seek ─────────────────────────────────────────────────


class TestRizinSeek:
    @pytest.mark.asyncio
    async def test_seek(self, rizin: RizinBridge):
        await rizin.seek("0x401000")
        rizin._pipe.cmd.assert_called_with("s 0x401000")

    @pytest.mark.asyncio
    async def test_current_seek(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "0x401000\n"
        result = await rizin.current_seek()
        assert result == "0x401000"


# ── ESIL emulation ───────────────────────────────────────


class TestRizinESIL:
    @pytest.mark.asyncio
    async def test_esil_init(self, rizin: RizinBridge):
        await rizin.esil_init()
        calls = [c[0][0] for c in rizin._pipe.cmd.call_args_list]
        assert "aei" in calls
        assert "aeim" in calls

    @pytest.mark.asyncio
    async def test_esil_step(self, rizin: RizinBridge):
        await rizin.esil_step()
        rizin._pipe.cmd.assert_called_with("aes")

    @pytest.mark.asyncio
    async def test_esil_step_over(self, rizin: RizinBridge):
        await rizin.esil_step_over()
        rizin._pipe.cmd.assert_called_with("aeso")

    @pytest.mark.asyncio
    async def test_esil_continue(self, rizin: RizinBridge):
        await rizin.esil_continue()
        rizin._pipe.cmd.assert_called_with("aec")

    @pytest.mark.asyncio
    async def test_esil_registers(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = {"rax": 0, "rbx": 0, "rip": 0x401000}
        result = await rizin.esil_registers()
        assert "rip" in result

    @pytest.mark.asyncio
    async def test_esil_set_register(self, rizin: RizinBridge):
        await rizin.esil_set_register("rax", "0x42")
        rizin._pipe.cmd.assert_called_with("aer rax=0x42")


# ── Hashing ──────────────────────────────────────────────


class TestRizinHash:
    @pytest.mark.asyncio
    async def test_hash_block(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "d41d8cd98f00b204e9800998ecf8427e\n"
        result = await rizin.hash_block("0x401000", 16, algo="md5")
        rizin._pipe.cmd.assert_called_with("ph md5 16 @ 0x401000")
        assert "d41d8cd9" in result

    @pytest.mark.asyncio
    async def test_hash_sha256(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "abcdef\n"
        await rizin.hash_block("0x401000", 32, algo="sha256")
        rizin._pipe.cmd.assert_called_with("ph sha256 32 @ 0x401000")


# ── Graphs ───────────────────────────────────────────────


class TestRizinGraphs:
    @pytest.mark.asyncio
    async def test_function_callgraph(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"name": "main", "imports": ["puts"]}]
        await rizin.function_callgraph("0x401000")
        rizin._pipe.cmdj.assert_called_with("agCj @ 0x401000")

    @pytest.mark.asyncio
    async def test_function_cfg(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = [{"offset": 0x401000, "blocks": []}]
        await rizin.function_cfg("0x401000")
        rizin._pipe.cmdj.assert_called_with("agj @ 0x401000")

    @pytest.mark.asyncio
    async def test_ascii_graph(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "[ main ]\n  |---> [ puts ]\n"
        result = await rizin.ascii_graph("0x401000")
        assert "main" in result

    @pytest.mark.asyncio
    async def test_dot_graph(self, rizin: RizinBridge):
        rizin._pipe.cmd.return_value = "digraph { main -> puts; }\n"
        result = await rizin.dot_graph("0x401000")
        assert "digraph" in result


# ── Projects ─────────────────────────────────────────────


class TestRizinProjects:
    @pytest.mark.asyncio
    async def test_save_project(self, rizin: RizinBridge):
        await rizin.save_project("my_analysis")
        rizin._pipe.cmd.assert_called_with("Ps my_analysis")

    @pytest.mark.asyncio
    async def test_load_project(self, rizin: RizinBridge):
        await rizin.load_project("my_analysis")
        rizin._pipe.cmd.assert_called_with("Po my_analysis")


# ── Properties ───────────────────────────────────────────


class TestRizinProperties:
    @pytest.mark.asyncio
    async def test_binary_path(self, rizin: RizinBridge):
        assert rizin.binary_path == "/tmp/test_bin"

    @pytest.mark.asyncio
    async def test_is_analyzed_default(self, rizin: RizinBridge):
        assert rizin.is_analyzed is False

    def test_cmdj_none_returns_empty(self, rizin: RizinBridge):
        rizin._pipe.cmdj.return_value = None
        result = rizin._cmdj("ij")
        assert result == []

    def test_cmdj_exception_fallback(self, rizin: RizinBridge):
        rizin._pipe.cmdj = MagicMock(side_effect=Exception("parse error"))
        rizin._pipe.cmd.return_value = "raw output"
        result = rizin._cmdj("bad_cmd")
        assert result == "raw output"
