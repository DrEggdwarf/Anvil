"""Tests for Pwn Bridge — comprehensive pwntools wrapper.

All tests mock pwntools — no real pwntools installation needed.
Validates: lifecycle, context, cyclic, packing, asm, shellcraft, ELF, ROP,
fmtstr, SROP, ret2dlresolve, encoding, hashing, constants, corefile, misc.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from backend.app.bridges.base import BridgeState
from backend.app.bridges.pwn_bridge import PwnBridge
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady


# ── Mock helpers ─────────────────────────────────────────


def make_mock_pwn():
    """Create a mock pwntools module."""
    mock = MagicMock()
    mock.__version__ = "4.12.0"
    mock.context = MagicMock()
    mock.context.arch = "amd64"
    mock.context.os = "linux"
    mock.context.bits = 64
    mock.context.bytes = 8
    mock.context.endian = "little"
    mock.context.signed = False
    mock.cyclic.return_value = b"aaaabaaacaaa"
    mock.cyclic_find.return_value = 44
    mock.p64.return_value = b"\x41\x00\x00\x00\x00\x00\x00\x00"
    mock.p32.return_value = b"\x41\x00\x00\x00"
    mock.p16.return_value = b"\x41\x00"
    mock.p8.return_value = b"\x41"
    mock.u64.return_value = 0x41
    mock.u32.return_value = 0x41
    mock.u16.return_value = 0x41
    mock.u8.return_value = 0x41
    mock.flat.return_value = b"\x41\x42\x43\x44"
    mock.asm.return_value = b"\x90\x90"
    mock.disasm.return_value = "   0:   90    nop"
    mock.make_elf.return_value = b"\x7fELF"
    mock.make_elf_from_assembly.return_value = b"\x7fELF"
    mock.shellcraft = MagicMock()
    mock.shellcraft.sh.return_value = "shellcode_source"
    mock.ELF = MagicMock()
    mock.ROP = MagicMock()
    mock.SigreturnFrame = MagicMock()
    mock.Ret2dlresolvePayload = MagicMock()
    mock.fmtstr_payload.return_value = b"%n%n%n"
    mock.xor.return_value = b"\x00\x01"
    mock.xor_key.return_value = (b"\xff", b"\x00\x01")
    mock.hexdump.return_value = "00000000  41 42 43 44"
    mock.enhex.return_value = "41424344"
    mock.unhex.return_value = b"ABCD"
    mock.b64e.return_value = b"QUJDRA=="
    mock.b64d.return_value = b"ABCD"
    mock.urlencode.return_value = b"%41%42%43"
    mock.urldecode.return_value = b"ABC"
    mock.md5sumhex.return_value = "d41d8cd98f00b204e9800998ecf8427e"
    mock.sha1sumhex.return_value = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    mock.sha256sumhex.return_value = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    mock.sha512sumhex.return_value = "cf83e1357eefb8bdf1542850d66d8007"
    mock.rol.return_value = 0x200
    mock.ror.return_value = 0x80000000
    mock.constants = MagicMock()
    mock.constants.__getitem__ = MagicMock(return_value=1)
    mock.Corefile = MagicMock()
    return mock


@pytest_asyncio.fixture
async def pwn():
    """Pwn bridge with mocked pwntools."""
    bridge = PwnBridge()
    mock_pwn = make_mock_pwn()
    bridge._pwn = mock_pwn
    bridge._context = mock_pwn.context
    bridge.state = BridgeState.READY
    yield bridge
    bridge.state = BridgeState.STOPPED


# ── Lifecycle ────────────────────────────────────────────


class TestPwnLifecycle:
    @pytest.mark.asyncio
    async def test_start_imports_pwntools(self):
        bridge = PwnBridge()
        mock_pwn = make_mock_pwn()
        with patch.dict("sys.modules", {"pwn": mock_pwn}):
            await bridge.start()
        assert bridge.state == BridgeState.READY
        assert bridge._pwn is mock_pwn

    @pytest.mark.asyncio
    async def test_start_failure_without_pwntools(self):
        bridge = PwnBridge()
        with patch.dict("sys.modules", {"pwn": None}):
            with patch("builtins.__import__", side_effect=ImportError("no pwntools")):
                with pytest.raises(BridgeCrash):
                    await bridge.start()
        assert bridge.state == BridgeState.ERROR

    @pytest.mark.asyncio
    async def test_stop_clears_state(self, pwn: PwnBridge):
        pwn._elf_cache["test"] = MagicMock()
        pwn._rop_cache["test"] = MagicMock()
        await pwn.stop()
        assert pwn.state == BridgeState.STOPPED
        assert pwn._pwn is None
        assert len(pwn._elf_cache) == 0
        assert len(pwn._rop_cache) == 0

    @pytest.mark.asyncio
    async def test_health_ok(self, pwn: PwnBridge):
        assert await pwn.health() is True

    @pytest.mark.asyncio
    async def test_health_fails_without_pwn(self):
        bridge = PwnBridge()
        assert await bridge.health() is False

    @pytest.mark.asyncio
    async def test_execute_dispatches(self, pwn: PwnBridge):
        result = await pwn.execute("get_context")
        assert "arch" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown command"):
            await pwn.execute("nonexistent_method")


# ── Context ──────────────────────────────────────────────


class TestPwnContext:
    @pytest.mark.asyncio
    async def test_get_context(self, pwn: PwnBridge):
        ctx = pwn.get_context()
        assert ctx["arch"] == "amd64"
        assert ctx["os"] == "linux"
        assert ctx["bits"] == 64

    @pytest.mark.asyncio
    async def test_set_context(self, pwn: PwnBridge):
        await pwn.set_context(arch="i386", bits=32)
        assert pwn._context.arch == "i386"
        assert pwn._context.bits == 32

    @pytest.mark.asyncio
    async def test_set_context_partial(self, pwn: PwnBridge):
        await pwn.set_context(endian="big")
        assert pwn._context.endian == "big"

    @pytest.mark.asyncio
    async def test_set_context_signed(self, pwn: PwnBridge):
        await pwn.set_context(signed=True)
        assert pwn._context.signed is True


# ── Cyclic ───────────────────────────────────────────────


class TestPwnCyclic:
    @pytest.mark.asyncio
    async def test_cyclic_default(self, pwn: PwnBridge):
        result = await pwn.cyclic()
        assert isinstance(result, str)
        pwn._pwn.cyclic.assert_called_once()

    @pytest.mark.asyncio
    async def test_cyclic_with_params(self, pwn: PwnBridge):
        await pwn.cyclic(length=100, alphabet="ABCD", n=4)
        pwn._pwn.cyclic.assert_called_once()

    @pytest.mark.asyncio
    async def test_cyclic_find(self, pwn: PwnBridge):
        result = await pwn.cyclic_find("61616162")
        assert result == 44

    @pytest.mark.asyncio
    async def test_cyclic_find_ascii(self, pwn: PwnBridge):
        result = await pwn.cyclic_find("aaab")
        assert result == 44


# ── Packing ──────────────────────────────────────────────


class TestPwnPacking:
    @pytest.mark.asyncio
    async def test_pack64(self, pwn: PwnBridge):
        result = await pwn.pack(0x41, bits=64)
        assert isinstance(result, str)
        pwn._pwn.p64.assert_called_once()

    @pytest.mark.asyncio
    async def test_pack32(self, pwn: PwnBridge):
        await pwn.pack(0x41, bits=32)
        pwn._pwn.p32.assert_called_once()

    @pytest.mark.asyncio
    async def test_pack16(self, pwn: PwnBridge):
        await pwn.pack(0x41, bits=16)
        pwn._pwn.p16.assert_called_once()

    @pytest.mark.asyncio
    async def test_pack8(self, pwn: PwnBridge):
        await pwn.pack(0x41, bits=8)
        pwn._pwn.p8.assert_called_once()

    @pytest.mark.asyncio
    async def test_unpack64(self, pwn: PwnBridge):
        result = await pwn.unpack("4100000000000000", bits=64)
        assert result == 0x41

    @pytest.mark.asyncio
    async def test_unpack32(self, pwn: PwnBridge):
        result = await pwn.unpack("41000000", bits=32)
        assert result == 0x41

    @pytest.mark.asyncio
    async def test_flat(self, pwn: PwnBridge):
        result = await pwn.flat([0x41, 0x42])
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_flat_with_hex_strings(self, pwn: PwnBridge):
        result = await pwn.flat(["41424344"])
        assert isinstance(result, str)


# ── Assembly ─────────────────────────────────────────────


class TestPwnAssembly:
    @pytest.mark.asyncio
    async def test_asm(self, pwn: PwnBridge):
        result = await pwn.asm("nop; nop")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_asm_with_arch(self, pwn: PwnBridge):
        await pwn.asm("nop", arch="i386")
        pwn._pwn.asm.assert_called_with("nop", arch="i386")

    @pytest.mark.asyncio
    async def test_disasm(self, pwn: PwnBridge):
        result = await pwn.disasm("9090")
        assert "nop" in result

    @pytest.mark.asyncio
    async def test_make_elf(self, pwn: PwnBridge):
        result = await pwn.make_elf("9090")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_make_elf_from_assembly(self, pwn: PwnBridge):
        result = await pwn.make_elf_from_assembly("nop; nop; ret")
        assert isinstance(result, str)


# ── Shellcraft ───────────────────────────────────────────


class TestPwnShellcraft:
    @pytest.mark.asyncio
    async def test_shellcraft(self, pwn: PwnBridge):
        result = await pwn.shellcraft("sh")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_shellcraft_unknown(self, pwn: PwnBridge):
        pwn._pwn.shellcraft.nonexistent = None
        with pytest.raises(ValueError, match="Unknown shellcraft"):
            await pwn.shellcraft("nonexistent")

    @pytest.mark.asyncio
    async def test_shellcraft_asm(self, pwn: PwnBridge):
        result = await pwn.shellcraft_asm("sh")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_shellcraft_list(self, pwn: PwnBridge):
        # Mock dir() on shellcraft
        result = await pwn.shellcraft_list()
        assert isinstance(result, list)


# ── ELF analysis ────────────────────────────────────────


class TestPwnELF:
    @pytest.mark.asyncio
    async def test_elf_load(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.arch = "amd64"
        mock_elf.bits = 64
        mock_elf.endian = "little"
        mock_elf.entry = 0x401000
        mock_elf.elftype = "EXEC"
        pwn._pwn.ELF.return_value = mock_elf
        result = await pwn.elf_load("/tmp/test")
        assert result["arch"] == "amd64"
        assert result["bits"] == 64
        assert "/tmp/test" in pwn._elf_cache

    @pytest.mark.asyncio
    async def test_elf_checksec(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.relro = "Full"
        mock_elf.canary = True
        mock_elf.nx = True
        mock_elf.pie = True
        mock_elf.rpath = False
        mock_elf.runpath = False
        mock_elf.fortify = True
        mock_elf.arch = "amd64"
        mock_elf.bits = 64
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_checksec("/tmp/test")
        assert result["relro"] == "Full"
        assert result["canary"] is True
        assert result["nx"] is True

    @pytest.mark.asyncio
    async def test_elf_symbols(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.symbols = {"main": 0x401000, "puts": 0x401050}
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_symbols("/tmp/test")
        assert "main" in result
        assert result["main"] == "0x401000"

    @pytest.mark.asyncio
    async def test_elf_got(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.got = {"puts": 0x601020}
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_got("/tmp/test")
        assert result["puts"] == "0x601020"

    @pytest.mark.asyncio
    async def test_elf_plt(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.plt = {"puts": 0x401030}
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_plt("/tmp/test")
        assert result["puts"] == "0x401030"

    @pytest.mark.asyncio
    async def test_elf_functions(self, pwn: PwnBridge):
        mock_func = MagicMock()
        mock_func.address = 0x401000
        mock_func.size = 42
        mock_elf = MagicMock()
        mock_elf.functions = {"main": mock_func}
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_functions("/tmp/test")
        assert len(result) == 1
        assert result[0]["name"] == "main"
        assert result[0]["size"] == 42

    @pytest.mark.asyncio
    async def test_elf_sections(self, pwn: PwnBridge):
        mock_sec = MagicMock()
        mock_sec.header.sh_addr = 0x401000
        mock_sec.header.sh_size = 0x1000
        mock_sec.header.sh_type = "SHT_PROGBITS"
        mock_elf = MagicMock()
        mock_elf.sections = [".text"]
        mock_elf.get_section_by_name.return_value = mock_sec
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_sections("/tmp/test")
        assert len(result) == 1
        assert result[0]["name"] == ".text"

    @pytest.mark.asyncio
    async def test_elf_search(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.search.return_value = [0x401000, 0x401010]
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_search("/tmp/test", "/bin/sh")
        assert len(result) == 2
        assert result[0] == "0x401000"

    @pytest.mark.asyncio
    async def test_elf_search_hex(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.search.return_value = [0x401020]
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_search("/tmp/test", "9090", is_hex=True)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_elf_bss(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        mock_elf.bss.return_value = 0x602000
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.elf_bss("/tmp/test", offset=0x10)
        assert result == "0x602000"

    @pytest.mark.asyncio
    async def test_elf_load_cache(self, pwn: PwnBridge):
        """Verify ELF is cached after first load."""
        mock_elf = MagicMock()
        mock_elf.arch = "amd64"
        mock_elf.bits = 64
        mock_elf.endian = "little"
        mock_elf.entry = 0x401000
        mock_elf.elftype = "EXEC"
        pwn._pwn.ELF.return_value = mock_elf
        await pwn.elf_load("/tmp/cached")
        assert "/tmp/cached" in pwn._elf_cache
        # Second call for checksec uses cache
        mock_elf.relro = "Partial"
        mock_elf.canary = False
        mock_elf.nx = True
        mock_elf.pie = False
        mock_elf.rpath = False
        mock_elf.runpath = False
        await pwn.elf_checksec("/tmp/cached")
        # ELF() should only have been called once
        assert pwn._pwn.ELF.call_count == 1


# ── ROP ──────────────────────────────────────────────────


class TestPwnROP:
    @pytest.mark.asyncio
    async def test_rop_create(self, pwn: PwnBridge):
        mock_elf = MagicMock()
        pwn._elf_cache["/tmp/test"] = mock_elf
        mock_rop = MagicMock()
        pwn._pwn.ROP.return_value = mock_rop
        rop_id = await pwn.rop_create("/tmp/test")
        assert rop_id.startswith("rop_")
        assert rop_id in pwn._rop_cache

    @pytest.mark.asyncio
    async def test_rop_find_gadget(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        mock_gadget = MagicMock()
        mock_gadget.__getitem__ = MagicMock(return_value=0x401234)
        mock_gadget.address = 0x401234
        mock_rop.find_gadget.return_value = mock_gadget
        pwn._rop_cache["rop_test"] = mock_rop
        result = await pwn.rop_find_gadget("rop_test", ["pop rdi", "ret"])
        assert result is not None

    @pytest.mark.asyncio
    async def test_rop_find_gadget_not_found(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        mock_rop.find_gadget.return_value = None
        pwn._rop_cache["rop_test"] = mock_rop
        result = await pwn.rop_find_gadget("rop_test", ["nonexistent"])
        assert result is None

    @pytest.mark.asyncio
    async def test_rop_call(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        pwn._rop_cache["rop_test"] = mock_rop
        await pwn.rop_call("rop_test", "puts", [0x601020])
        mock_rop.call.assert_called_once_with("puts", [0x601020])

    @pytest.mark.asyncio
    async def test_rop_raw(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        pwn._rop_cache["rop_test"] = mock_rop
        await pwn.rop_raw("rop_test", 0xdeadbeef)
        mock_rop.raw.assert_called_once_with(0xdeadbeef)

    @pytest.mark.asyncio
    async def test_rop_chain(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        mock_rop.chain.return_value = b"\x00\x10\x40\x00"
        pwn._rop_cache["rop_test"] = mock_rop
        result = await pwn.rop_chain("rop_test")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_rop_dump(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        mock_rop.dump.return_value = "0x0000: 0x401000 (pop rdi; ret)"
        pwn._rop_cache["rop_test"] = mock_rop
        result = await pwn.rop_dump("rop_test")
        assert "pop rdi" in result

    @pytest.mark.asyncio
    async def test_rop_migrate(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        pwn._rop_cache["rop_test"] = mock_rop
        await pwn.rop_migrate("rop_test", 0x602000)
        mock_rop.migrate.assert_called_once_with(0x602000)

    @pytest.mark.asyncio
    async def test_rop_set_registers(self, pwn: PwnBridge):
        mock_rop = MagicMock()
        pwn._rop_cache["rop_test"] = mock_rop
        await pwn.rop_set_registers("rop_test", {"rdi": 0x41, "rsi": 0x42})
        mock_rop.setRegisters.assert_called_once()

    @pytest.mark.asyncio
    async def test_rop_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_find_gadget("nonexistent", ["ret"])

    @pytest.mark.asyncio
    async def test_rop_call_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_call("nonexistent", "puts")

    @pytest.mark.asyncio
    async def test_rop_raw_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_raw("nonexistent", 0x41)

    @pytest.mark.asyncio
    async def test_rop_chain_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_chain("nonexistent")

    @pytest.mark.asyncio
    async def test_rop_dump_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_dump("nonexistent")

    @pytest.mark.asyncio
    async def test_rop_migrate_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_migrate("nonexistent", 0x41)

    @pytest.mark.asyncio
    async def test_rop_set_registers_unknown_id(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown ROP chain"):
            await pwn.rop_set_registers("nonexistent", {"rdi": 0})


# ── Format string ────────────────────────────────────────


class TestPwnFmtstr:
    @pytest.mark.asyncio
    async def test_fmtstr_payload(self, pwn: PwnBridge):
        result = await pwn.fmtstr_payload(
            offset=6,
            writes={"0x601020": 0xdeadbeef},
        )
        assert isinstance(result, str)
        pwn._pwn.fmtstr_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_fmtstr_payload_with_params(self, pwn: PwnBridge):
        await pwn.fmtstr_payload(
            offset=10,
            writes={"0x601020": 0x41, "0x601028": 0x42},
            numbwritten=8,
            write_size="short",
        )
        call_args = pwn._pwn.fmtstr_payload.call_args
        assert call_args[0][0] == 10  # offset
        assert call_args[1]["numbwritten"] == 8
        assert call_args[1]["write_size"] == "short"


# ── SROP ─────────────────────────────────────────────────


class TestPwnSROP:
    @pytest.mark.asyncio
    async def test_srop_frame(self, pwn: PwnBridge):
        mock_frame = MagicMock()
        mock_frame.__bytes__ = MagicMock(return_value=b"\x00" * 248)
        pwn._pwn.SigreturnFrame.return_value = mock_frame
        result = await pwn.srop_frame({"rax": 59, "rdi": 0x601000, "rip": 0x401000})
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_srop_frame_with_arch(self, pwn: PwnBridge):
        mock_frame = MagicMock()
        mock_frame.__bytes__ = MagicMock(return_value=b"\x00" * 128)
        pwn._pwn.SigreturnFrame.return_value = mock_frame
        await pwn.srop_frame({"eax": 11}, arch="i386")
        assert pwn._context.arch == "i386"


# ── Ret2dlresolve ────────────────────────────────────────


class TestPwnRet2dl:
    @pytest.mark.asyncio
    async def test_ret2dlresolve(self, pwn: PwnBridge):
        mock_dl = MagicMock()
        mock_dl.payload = b"\x00" * 64
        mock_dl.reloc_index = 42
        pwn._pwn.Ret2dlresolvePayload.return_value = mock_dl
        mock_elf = MagicMock()
        pwn._elf_cache["/tmp/test"] = mock_elf
        result = await pwn.ret2dlresolve("/tmp/test", "system", ["/bin/sh"])
        assert result["reloc_index"] == 42
        assert isinstance(result["payload"], str)


# ── Encoding / crypto ───────────────────────────────────


class TestPwnEncoding:
    @pytest.mark.asyncio
    async def test_xor(self, pwn: PwnBridge):
        result = await pwn.xor("4142", "ff")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_xor_key(self, pwn: PwnBridge):
        result = await pwn.xor_key("4142", "00")
        assert "key" in result
        assert "result" in result

    @pytest.mark.asyncio
    async def test_hexdump(self, pwn: PwnBridge):
        result = await pwn.hexdump("41424344")
        assert "41 42 43 44" in result

    @pytest.mark.asyncio
    async def test_enhex(self, pwn: PwnBridge):
        result = await pwn.enhex("ABCD")
        assert result == "41424344"

    @pytest.mark.asyncio
    async def test_unhex(self, pwn: PwnBridge):
        result = await pwn.unhex("41424344")
        assert result == "ABCD"

    @pytest.mark.asyncio
    async def test_b64e(self, pwn: PwnBridge):
        result = await pwn.b64e("ABCD")
        assert result == "QUJDRA=="

    @pytest.mark.asyncio
    async def test_b64d(self, pwn: PwnBridge):
        result = await pwn.b64d("QUJDRA==")
        assert result == "ABCD"

    @pytest.mark.asyncio
    async def test_urlencode(self, pwn: PwnBridge):
        result = await pwn.urlencode("ABC")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_urldecode(self, pwn: PwnBridge):
        result = await pwn.urldecode("%41%42%43")
        assert isinstance(result, str)


# ── Hashing ──────────────────────────────────────────────


class TestPwnHashing:
    @pytest.mark.asyncio
    async def test_hash_sha256(self, pwn: PwnBridge):
        result = await pwn.hash_data("41424344", "sha256")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_hash_md5(self, pwn: PwnBridge):
        await pwn.hash_data("41424344", "md5")
        pwn._pwn.md5sumhex.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_sha1(self, pwn: PwnBridge):
        await pwn.hash_data("41424344", "sha1")
        pwn._pwn.sha1sumhex.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_sha512(self, pwn: PwnBridge):
        await pwn.hash_data("41424344", "sha512")
        pwn._pwn.sha512sumhex.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_unknown_algo(self, pwn: PwnBridge):
        with pytest.raises(ValueError, match="Unknown algo"):
            await pwn.hash_data("41", "blake2")


# ── Shellcode encoding ──────────────────────────────────


class TestPwnShellcodeEncode:
    @pytest.mark.asyncio
    async def test_encode_shellcode(self, pwn: PwnBridge):
        mock_encode = MagicMock(return_value=b"\x90\x90")
        with patch.dict("sys.modules", {"pwnlib": MagicMock(), "pwnlib.encoders": MagicMock(encode=mock_encode)}):
            result = await pwn.encode_shellcode("9090", "00")
            assert isinstance(result, str)


# ── Constants ────────────────────────────────────────────


class TestPwnConstants:
    @pytest.mark.asyncio
    async def test_get_constant(self, pwn: PwnBridge):
        result = await pwn.get_constant("SYS_write")
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_constant_missing(self, pwn: PwnBridge):
        pwn._pwn.constants.__getitem__.side_effect = KeyError("not found")
        result = await pwn.get_constant("NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_constants(self, pwn: PwnBridge):
        result = await pwn.list_constants("SYS_")
        assert isinstance(result, dict)


# ── Corefile ─────────────────────────────────────────────


class TestPwnCorefile:
    @pytest.mark.asyncio
    async def test_corefile_load(self, pwn: PwnBridge):
        mock_core = MagicMock()
        mock_core.signal = 11
        mock_core.fault_addr = 0x41414141
        mock_core.rax = 0
        mock_core.rbx = 0
        mock_core.rcx = 0
        mock_core.rdx = 0
        mock_core.rsi = 0
        mock_core.rdi = 0
        mock_core.rsp = 0x7fffffffe000
        mock_core.rbp = 0x7fffffffe010
        mock_core.rip = 0x41414141
        mock_core.r8 = 0
        mock_core.r9 = 0
        mock_core.r10 = 0
        mock_core.r11 = 0
        mock_core.r12 = 0
        mock_core.r13 = 0
        mock_core.r14 = 0
        mock_core.r15 = 0
        mock_mapping = MagicMock()
        mock_mapping.name = "[stack]"
        mock_mapping.start = 0x7ffffffde000
        mock_mapping.stop = 0x7ffffffff000
        mock_core.mappings = [mock_mapping]
        pwn._pwn.Corefile.return_value = mock_core
        result = await pwn.corefile_load("/tmp/core")
        assert result["signal"] == 11
        assert result["fault_addr"] == "0x41414141"
        assert "registers" in result
        assert "mappings" in result


# ── Misc ─────────────────────────────────────────────────


class TestPwnMisc:
    @pytest.mark.asyncio
    async def test_bits_to_str(self, pwn: PwnBridge):
        result = await pwn.bits_to_str(0xFF, 8)
        assert result == "11111111"

    @pytest.mark.asyncio
    async def test_rol(self, pwn: PwnBridge):
        result = await pwn.rol(1, 9, 32)
        assert result == 0x200

    @pytest.mark.asyncio
    async def test_ror(self, pwn: PwnBridge):
        result = await pwn.ror(1, 1, 32)
        assert result == 0x80000000

    @pytest.mark.asyncio
    async def test_properties(self, pwn: PwnBridge):
        pwn._elf_cache["/tmp/a"] = MagicMock()
        pwn._rop_cache["rop_1"] = MagicMock()
        assert "/tmp/a" in pwn.loaded_elfs
        assert "rop_1" in pwn.rop_chains


# ── Not ready guard ──────────────────────────────────────


class TestPwnGuards:
    @pytest.mark.asyncio
    async def test_methods_fail_when_not_ready(self):
        bridge = PwnBridge()
        with pytest.raises(BridgeNotReady):
            await bridge.cyclic()
        with pytest.raises(BridgeNotReady):
            await bridge.pack(0x41)
        with pytest.raises(BridgeNotReady):
            await bridge.asm("nop")
        with pytest.raises(BridgeNotReady):
            await bridge.elf_load("/tmp/test")
