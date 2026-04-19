"""Tests for the binary analyzer — checksec, file info, sections."""

from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from backend.app.bridges.binary_analyzer import BinaryAnalyzer
from backend.app.core.subprocess_manager import SubprocessManager


@pytest_asyncio.fixture
async def analyzer():
    spm = SubprocessManager()
    return BinaryAnalyzer(spm)


# ── file_info ────────────────────────────────────────────


class TestFileInfo:
    @pytest.mark.asyncio
    async def test_success(self, analyzer):
        analyzer._spm.execute = AsyncMock(
            return_value=("ELF 64-bit LSB executable, x86-64, version 1", "", 0)
        )
        result = await analyzer.file_info("/tmp/test_bin")
        assert result["success"] is True
        assert result["path"] == "/tmp/test_bin"
        assert "ELF 64-bit LSB executable" in result["type"]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(
            return_value=("", "cannot open", 1)
        )
        result = await analyzer.file_info("/tmp/nonexistent")
        assert result["success"] is False
        assert result["type"] == "unknown"


# ── checksec ─────────────────────────────────────────────


class TestChecksec:
    @pytest.mark.asyncio
    async def test_full_protections(self, analyzer):
        """Binary with all security features enabled."""
        analyzer._spm.execute = AsyncMock(
            side_effect=[
                # readelf -W -l (RELRO, NX)
                (
                    "  GNU_RELRO      0x000000 0x600000 0x600000 0x0200 0x0200 R\n"
                    "  GNU_STACK      0x000000 0x000000 0x000000 0x0000 0x0000 RW\n",
                    "", 0,
                ),
                # readelf -W -d (BIND_NOW)
                ("  0x000000001e (FLAGS)  BIND_NOW\n", "", 0),
                # readelf -W -s (canary, fortify, symbols)
                (
                    "Symbol table '.symtab' contains 50 entries:\n"
                    "   10: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND __stack_chk_fail\n"
                    "   11: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND __fortify_fail\n",
                    "", 0,
                ),
                # readelf -W -h (PIE)
                ("  Type:                              DYN (Position-Independent Executable)\n", "", 0),
            ]
        )
        result = await analyzer.checksec("/tmp/test_bin")
        assert result["relro"] == "full"
        assert result["nx"] is True
        assert result["canary"] is True
        assert result["pie"] is True
        assert result["fortify"] is True
        assert result["symbols"] is True

    @pytest.mark.asyncio
    async def test_no_protections(self, analyzer):
        """Statically linked ASM binary — no protections."""
        analyzer._spm.execute = AsyncMock(
            side_effect=[
                # readelf -W -l: no GNU_RELRO, GNU_STACK with E flag
                ("  GNU_STACK      0x000000 0x000000 0x000000 0x0000 0x0000 RWE\n", "", 0),
                # readelf -W -d: no BIND_NOW
                ("", "", 0),
                # readelf -W -s: no canary, no fortify
                ("Symbol table '.symtab' contains 5 entries:\n", "", 0),
                # readelf -W -h: EXEC (not PIE)
                ("  Type:                              EXEC (Executable file)\n", "", 0),
            ]
        )
        result = await analyzer.checksec("/tmp/test_bin")
        assert result["relro"] == "none"
        assert result["nx"] is False
        assert result["canary"] is False
        assert result["pie"] is False
        assert result["fortify"] is False
        assert result["symbols"] is True  # .symtab present

    @pytest.mark.asyncio
    async def test_partial_relro(self, analyzer):
        analyzer._spm.execute = AsyncMock(
            side_effect=[
                ("  GNU_RELRO      0x000000\n  GNU_STACK      0x0 0x0 0x0 0x0 0x0 RW\n", "", 0),
                ("", "", 0),  # no BIND_NOW
                ("", "", 0),
                ("  Type:                              EXEC\n", "", 0),
            ]
        )
        result = await analyzer.checksec("/tmp/test_bin")
        assert result["relro"] == "partial"

    @pytest.mark.asyncio
    async def test_rpath_runpath(self, analyzer):
        analyzer._spm.execute = AsyncMock(
            side_effect=[
                ("  GNU_STACK      0x0 0x0 0x0 0x0 0x0 RW\n", "", 0),
                ("  (RPATH)  /usr/lib\n  (RUNPATH)  /opt/lib\n", "", 0),
                ("", "", 0),
                ("  Type:                              EXEC\n", "", 0),
            ]
        )
        result = await analyzer.checksec("/tmp/test_bin")
        assert result["rpath"] is True
        assert result["runpath"] is True

    @pytest.mark.asyncio
    async def test_readelf_failure_graceful(self, analyzer):
        """If readelf fails, return safe defaults."""
        analyzer._spm.execute = AsyncMock(return_value=("", "error", 1))
        result = await analyzer.checksec("/tmp/nonexistent")
        assert result["relro"] == "none"
        assert result["canary"] is False
        assert result["nx"] is False
        assert result["pie"] is False


# ── sections ─────────────────────────────────────────────


class TestSections:
    @pytest.mark.asyncio
    async def test_parse_sections(self, analyzer):
        readelf_output = (
            "There are 6 section headers, starting at offset 0x1188:\n"
            "\n"
            "Section Headers:\n"
            "  [Nr] Name              Type            Address          Off    Size   ES Flg Lk Inf Al\n"
            "  [ 0]                   NULL            0000000000000000 000000 000000 00      0   0  0\n"
            "  [ 1] .text             PROGBITS        0000000000401000 001000 000010 00  AX  0   0 16\n"
            "  [ 2] .data             PROGBITS        0000000000402000 002000 000004 00  WA  0   0  4\n"
            "  [ 3] .bss              NOBITS          0000000000402004 002004 000008 00  WA  0   0  4\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(readelf_output, "", 0))
        sections = await analyzer.sections("/tmp/test_bin")
        assert len(sections) >= 3
        text = next(s for s in sections if s["name"] == ".text")
        assert text["type"] == "PROGBITS"
        assert text["size"] == 16  # 0x10

    @pytest.mark.asyncio
    async def test_empty_on_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "error", 1))
        result = await analyzer.sections("/tmp/fail")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_sections(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("No section headers.\n", "", 0))
        result = await analyzer.sections("/tmp/empty")
        assert result == []


# ── ELF header ───────────────────────────────────────────


class TestElfHeader:
    @pytest.mark.asyncio
    async def test_parse_header(self, analyzer):
        output = (
            "ELF Header:\n"
            "  Class:                             ELF64\n"
            "  Data:                              2's complement, little endian\n"
            "  Type:                              EXEC (Executable file)\n"
            "  Machine:                           Advanced Micro Devices X86-64\n"
            "  Entry point address:               0x401000\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        header = await analyzer.elf_header("/tmp/bin")
        assert "class" in header
        assert "ELF64" in header["class"]
        assert "entry_point_address" in header
        assert "0x401000" in header["entry_point_address"]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "error", 1))
        result = await analyzer.elf_header("/tmp/fail")
        assert "error" in result


# ── Program headers ──────────────────────────────────────


class TestProgramHeaders:
    @pytest.mark.asyncio
    async def test_parse_program_headers(self, analyzer):
        output = (
            "Program Headers:\n"
            "  Type           Offset   VirtAddr           PhysAddr           FileSiz  MemSiz   Flg Align\n"
            "  LOAD           0x000000 0x0000000000400000 0x0000000000400000 0x0001a8 0x0001a8 R   0x1000\n"
            "  LOAD           0x001000 0x0000000000401000 0x0000000000401000 0x000010 0x000010 R E 0x1000\n"
            "  GNU_STACK      0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0x10\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        headers = await analyzer.program_headers("/tmp/bin")
        assert len(headers) >= 2
        load = next(h for h in headers if h["type"] == "LOAD")
        assert "0x" in load["vaddr"]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.program_headers("/tmp/fail") == []


# ── Symbols (nm) ─────────────────────────────────────────


class TestSymbols:
    @pytest.mark.asyncio
    async def test_parse_symbols(self, analyzer):
        output = (
            "0000000000401000 T _start\n"
            "0000000000402000 D data_var\n"
            "                 U printf\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        syms = await analyzer.symbols("/tmp/bin")
        assert len(syms) == 3
        assert syms[0]["name"] == "_start"
        assert syms[0]["type"] == "T"
        assert syms[2]["name"] == "printf"
        assert syms[2]["address"] == ""

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.symbols("/tmp/fail") == []


# ── Dynamic symbols ──────────────────────────────────────


class TestDynamicSymbols:
    @pytest.mark.asyncio
    async def test_parse_dynsyms(self, analyzer):
        output = (
            "Symbol table '.dynsym' contains 5 entries:\n"
            "   Num:    Value          Size Type    Bind   Vis      Ndx Name\n"
            "     0: 0000000000000000     0 NOTYPE  LOCAL  DEFAULT  UND \n"
            "     1: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND puts@GLIBC_2.2.5\n"
            "     2: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND __libc_start_main@GLIBC_2.34\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        syms = await analyzer.dynamic_symbols("/tmp/bin")
        assert len(syms) == 2  # empty name skipped
        assert syms[0]["name"] == "puts@GLIBC_2.2.5"
        assert syms[0]["ndx"] == "UND"

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.dynamic_symbols("/tmp/fail") == []


# ── Imports & exports ────────────────────────────────────


class TestImportsExports:
    @pytest.mark.asyncio
    async def test_imports(self, analyzer):
        output = (
            "Symbol table '.dynsym' contains 3 entries:\n"
            "   Num:    Value          Size Type    Bind   Vis      Ndx Name\n"
            "     1: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND puts@GLIBC\n"
            "     2: 0000000000401060    50 FUNC    GLOBAL DEFAULT   14 main\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        imports = await analyzer.imports("/tmp/bin")
        assert len(imports) == 1
        assert imports[0]["name"] == "puts@GLIBC"

    @pytest.mark.asyncio
    async def test_exports(self, analyzer):
        output = (
            "Symbol table '.dynsym' contains 3 entries:\n"
            "   Num:    Value          Size Type    Bind   Vis      Ndx Name\n"
            "     1: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND puts@GLIBC\n"
            "     2: 0000000000401060    50 FUNC    GLOBAL DEFAULT   14 main\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        exports = await analyzer.exports("/tmp/bin")
        assert len(exports) == 1
        assert exports[0]["name"] == "main"


# ── Relocations ──────────────────────────────────────────


class TestRelocations:
    @pytest.mark.asyncio
    async def test_parse_relocations(self, analyzer):
        output = (
            "Relocation section '.rela.plt' at offset 0x3f8 contains 1 entry:\n"
            "  Offset          Info           Type           Sym. Value    Sym. Name + Addend\n"
            "000000404018  000100000007 R_X86_64_JUMP_SL 0000000000000000 puts@GLIBC_2.2.5 + 0\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        relocs = await analyzer.relocations("/tmp/bin")
        assert len(relocs) == 1
        assert "R_X86_64_JUMP_SL" in relocs[0]["type"]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.relocations("/tmp/fail") == []


# ── GOT / PLT ────────────────────────────────────────────


class TestGotPlt:
    @pytest.mark.asyncio
    async def test_got_entries(self, analyzer):
        output = (
            "/tmp/bin:     file format elf64-x86-64\n\n"
            "DYNAMIC RELOCATION RECORDS\n"
            "OFFSET           TYPE              VALUE\n"
            "0000000000404018 R_X86_64_JUMP_SLOT  puts@GLIBC_2.2.5\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        entries = await analyzer.got_entries("/tmp/bin")
        assert len(entries) >= 1
        assert "puts" in entries[0]["name"]

    @pytest.mark.asyncio
    async def test_plt_entries(self, analyzer):
        output = (
            "Disassembly of section .plt:\n\n"
            "0000000000401020 <puts@plt>:\n"
            "  401020:   ff 25 f2 2f 00 00   jmp    *0x2ff2(%rip)\n"
            "0000000000401030 <__libc_start_main@plt>:\n"
            "  401030:   ff 25 ea 2f 00 00   jmp    *0x2fea(%rip)\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        entries = await analyzer.plt_entries("/tmp/bin")
        assert len(entries) == 2
        assert entries[0]["name"] == "puts@plt"
        assert entries[1]["name"] == "__libc_start_main@plt"

    @pytest.mark.asyncio
    async def test_got_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.got_entries("/tmp/fail") == []


# ── Strings ──────────────────────────────────────────────


class TestStrings:
    @pytest.mark.asyncio
    async def test_parse_strings(self, analyzer):
        output = (
            "   318 /lib64/ld-linux-x86-64.so.2\n"
            "   3b0 Hello, World!\n"
            "   3c0 puts\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        strings = await analyzer.strings("/tmp/bin")
        assert len(strings) == 3
        assert strings[1]["string"] == "Hello, World!"
        assert strings[1]["offset"] == "0x3b0"

    @pytest.mark.asyncio
    async def test_custom_min_length(self, analyzer):
        calls = []

        async def mock_exec(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        analyzer._spm.execute = mock_exec
        await analyzer.strings("/tmp/bin", min_length=8)
        assert "-n8" in calls[0]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.strings("/tmp/fail") == []


# ── Dependencies (ldd) ───────────────────────────────────


class TestDependencies:
    @pytest.mark.asyncio
    async def test_parse_dependencies(self, analyzer):
        output = (
            "\tlinux-vdso.so.1 (0x00007ffd5e7d1000)\n"
            "\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f8a94200000)\n"
            "\t/lib64/ld-linux-x86-64.so.2 (0x00007f8a94600000)\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        deps = await analyzer.dependencies("/tmp/bin")
        assert len(deps) >= 2
        libc = next(d for d in deps if d["name"] == "libc.so.6")
        assert "/lib" in libc["path"]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        assert await analyzer.dependencies("/tmp/fail") == []


# ── Disassembly (objdump) ────────────────────────────────


class TestDisassemble:
    @pytest.mark.asyncio
    async def test_basic(self, analyzer):
        analyzer._spm.execute = AsyncMock(
            return_value=("401000: mov eax, 1\n401005: int 0x80\n", "", 0)
        )
        result = await analyzer.disassemble("/tmp/bin")
        assert "mov eax" in result

    @pytest.mark.asyncio
    async def test_with_section(self, analyzer):
        calls = []

        async def mock_exec(cmd, **kw):
            calls.append(cmd)
            return ("disasm output", "", 0)

        analyzer._spm.execute = mock_exec
        await analyzer.disassemble("/tmp/bin", section=".text")
        assert "-j" in calls[0]
        assert ".text" in calls[0]

    @pytest.mark.asyncio
    async def test_att_syntax(self, analyzer):
        calls = []

        async def mock_exec(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        analyzer._spm.execute = mock_exec
        await analyzer.disassemble("/tmp/bin", intel_syntax=False)
        assert "-M" not in calls[0]

    @pytest.mark.asyncio
    async def test_address_range(self, analyzer):
        calls = []

        async def mock_exec(cmd, **kw):
            calls.append(cmd)
            return ("", "", 0)

        analyzer._spm.execute = mock_exec
        await analyzer.disassemble(
            "/tmp/bin",
            start_address="0x401000",
            stop_address="0x401100",
        )
        assert any("--start-address" in c for c in calls[0])

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        result = await analyzer.disassemble("/tmp/fail")
        assert result == ""


# ── Hexdump ──────────────────────────────────────────────


class TestHexdump:
    @pytest.mark.asyncio
    async def test_basic(self, analyzer):
        analyzer._spm.execute = AsyncMock(
            return_value=("00000000: 7f45 4c46 0201 0100  .ELF....\n", "", 0)
        )
        result = await analyzer.hexdump("/tmp/bin")
        assert "ELF" in result

    @pytest.mark.asyncio
    async def test_with_params(self, analyzer):
        calls = []

        async def mock_exec(cmd, **kw):
            calls.append(cmd)
            return ("hex output", "", 0)

        analyzer._spm.execute = mock_exec
        await analyzer.hexdump("/tmp/bin", offset=0x100, length=512)
        assert "256" in calls[0] or "512" in calls[0]

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        result = await analyzer.hexdump("/tmp/fail")
        assert result == ""


# ── Size info ────────────────────────────────────────────


class TestSizeInfo:
    @pytest.mark.asyncio
    async def test_parse_size(self, analyzer):
        output = (
            "   text\t   data\t    bss\t    dec\t    hex\tfilename\n"
            "     16\t      0\t      0\t     16\t     10\t/tmp/bin\n"
        )
        analyzer._spm.execute = AsyncMock(return_value=(output, "", 0))
        result = await analyzer.size_info("/tmp/bin")
        assert result["text"] == 16
        assert result["data"] == 0
        assert result["bss"] == 0
        assert result["total"] == 16

    @pytest.mark.asyncio
    async def test_failure(self, analyzer):
        analyzer._spm.execute = AsyncMock(return_value=("", "err", 1))
        result = await analyzer.size_info("/tmp/fail")
        assert result == {}
