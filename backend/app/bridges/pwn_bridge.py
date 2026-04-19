"""Pwn Bridge — comprehensive exploitation toolkit via pwntools.

Wraps pwntools with full feature coverage:
- Context management (arch, os, bits, endian)
- Cyclic patterns (de Bruijn generation & offset finding)
- Packing/unpacking (p8/p16/p32/p64, u8/u16/u32/u64, flat)
- Assembly/disassembly (asm, disasm, multi-arch)
- Shellcraft (shellcode generation by arch/os)
- ELF analysis (checksec, symbols, GOT, PLT, sections, search)
- ROP chain building (gadgets, calls, chain generation)
- Format string exploitation (payload generation)
- SigreturnFrame (SROP)
- Ret2dlresolve payload
- Encoding (XOR, hex, base64, URL, shellcode encoders)
- Hashing (md5, sha1, sha256, sha512)
- Crypto utilities (xor, xor_key, xor_pair)
- Constants database (syscall numbers)
- Corefile analysis
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import bridge_registry
from backend.app.core.exceptions import BridgeCrash

logger = logging.getLogger(__name__)


class PwnBridge(BaseBridge):
    """Pwntools bridge — stateful exploitation toolkit."""

    bridge_type = "pwn"
    _MAX_CACHE_SIZE = 50

    def __init__(self) -> None:
        super().__init__()
        self._pwn: Any = None       # pwnlib module reference
        self._context: Any = None    # pwnlib.context.context
        self._elf_cache: dict[str, Any] = {}  # path → ELF object
        self._rop_cache: dict[str, Any] = {}  # id → ROP object

    def _evict_cache(self, cache: dict, key: str) -> None:
        """Add key; if cache exceeds limit, evict the oldest entry."""
        if key not in cache and len(cache) >= self._MAX_CACHE_SIZE:
            oldest = next(iter(cache))
            removed = cache.pop(oldest)
            with contextlib.suppress(Exception):
                removed.close()

    def _cache_elf(self, path: str, elf: Any) -> None:
        """Store ELF in cache with eviction."""
        self._evict_cache(self._elf_cache, path)
        self._elf_cache[path] = elf

    def _cache_rop(self, rop_id: str, rop: Any) -> None:
        """Store ROP in cache with eviction."""
        self._evict_cache(self._rop_cache, rop_id)
        self._rop_cache[rop_id] = rop

    async def start(self) -> None:
        """Import pwntools and configure context."""
        self.state = BridgeState.STARTING
        try:
            import pwn as pwnlib
            self._pwn = pwnlib
            self._context = pwnlib.context
            # Default to amd64 linux
            self._context.arch = "amd64"
            self._context.os = "linux"
            self.state = BridgeState.READY
            logger.info("Pwn bridge started (pwntools %s)", getattr(pwnlib, "__version__", "?"))
        except Exception as e:
            self.state = BridgeState.ERROR
            raise BridgeCrash("pwn", exit_code=None) from e

    async def stop(self) -> None:
        """Cleanup loaded ELFs and ROP chains."""
        self.state = BridgeState.STOPPING
        for elf in self._elf_cache.values():
            with contextlib.suppress(Exception):
                elf.close()
        self._elf_cache.clear()
        self._rop_cache.clear()
        self._pwn = None
        self._context = None
        self.state = BridgeState.STOPPED
        logger.info("Pwn bridge stopped")

    async def health(self) -> bool:
        if self._pwn is None:
            return False
        try:
            self._pwn.cyclic(4)
            return True
        except Exception:
            return False

    async def execute(self, command: str, **kwargs: Any) -> Any:
        """Generic execute — dispatches to named method."""
        self._require_ready()
        method = getattr(self, command, None)
        if method and callable(method):
            import inspect
            result = method(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        raise ValueError(f"Unknown command: {command}")

    # ── Context management ───────────────────────────────

    async def set_context(
        self,
        arch: str | None = None,
        os: str | None = None,
        bits: int | None = None,
        endian: str | None = None,
        signed: bool | None = None,
    ) -> dict:
        """Set pwntools context (arch, os, bits, endian)."""
        self._require_ready()
        if arch:
            self._context.arch = arch
        if os:
            self._context.os = os
        if bits:
            self._context.bits = bits
        if endian:
            self._context.endian = endian
        if signed is not None:
            self._context.signed = signed
        return self.get_context()

    def get_context(self) -> dict:
        """Return current context settings."""
        self._require_ready()
        return {
            "arch": self._context.arch,
            "os": self._context.os,
            "bits": self._context.bits,
            "bytes": self._context.bytes,
            "endian": self._context.endian,
            "signed": self._context.signed,
        }

    # ── Cyclic patterns ──────────────────────────────────

    async def cyclic(self, length: int = 200, alphabet: str | None = None, n: int | None = None) -> str:
        """Generate de Bruijn cyclic pattern."""
        self._require_ready()
        kwargs: dict[str, Any] = {}
        if alphabet:
            kwargs["alphabet"] = alphabet.encode() if isinstance(alphabet, str) else alphabet
        if n:
            kwargs["n"] = n
        result = self._pwn.cyclic(length, **kwargs)
        return result.hex() if isinstance(result, bytes) else str(result)

    async def cyclic_find(self, subseq: str, alphabet: str | None = None, n: int | None = None) -> int:
        """Find offset in de Bruijn pattern. subseq can be hex or ASCII."""
        self._require_ready()
        kwargs: dict[str, Any] = {}
        if alphabet:
            kwargs["alphabet"] = alphabet.encode() if isinstance(alphabet, str) else alphabet
        if n:
            kwargs["n"] = n
        # Try hex decode first, fallback to raw bytes
        try:
            data = bytes.fromhex(subseq)
        except ValueError:
            data = subseq.encode()
        return int(self._pwn.cyclic_find(data, **kwargs))

    # ── Packing / unpacking ──────────────────────────────

    async def pack(self, value: int, bits: int = 64, endian: str = "little", signed: bool = False) -> str:
        """Pack integer to hex bytes. bits: 8, 16, 32, 64."""
        self._require_ready()
        packers = {8: self._pwn.p8, 16: self._pwn.p16, 32: self._pwn.p32, 64: self._pwn.p64}
        packer = packers.get(bits)
        if not packer:
            result = self._pwn.pack(value, bits, endian=endian, sign=signed)
        else:
            result = packer(value, endian=endian, sign=signed)
        return result.hex()

    async def unpack(self, hex_data: str, bits: int = 64, endian: str = "little", signed: bool = False) -> int:
        """Unpack hex bytes to integer."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        unpackers = {8: self._pwn.u8, 16: self._pwn.u16, 32: self._pwn.u32, 64: self._pwn.u64}
        unpacker = unpackers.get(bits)
        if not unpacker:
            return int(self._pwn.unpack(data, bits, endian=endian, sign=signed))
        return int(unpacker(data, endian=endian, sign=signed))

    async def flat(self, values: list, word_size: int | None = None) -> str:
        """Flatten list of ints/bytes/strings to payload. Returns hex."""
        self._require_ready()
        # Convert hex strings to bytes, keep ints as-is
        processed = []
        for v in values:
            if isinstance(v, str):
                try:
                    processed.append(bytes.fromhex(v))
                except ValueError:
                    processed.append(v.encode())
            else:
                processed.append(v)
        kwargs = {}
        if word_size:
            kwargs["word_size"] = word_size
        result = self._pwn.flat(processed, **kwargs)
        return result.hex()

    # ── Assembly / disassembly ───────────────────────────

    async def asm(self, source: str, arch: str | None = None, os_name: str | None = None) -> str:
        """Assemble source to bytes (hex). Multi-arch via binutils."""
        self._require_ready()
        kwargs: dict[str, Any] = {}
        if arch:
            kwargs["arch"] = arch
        if os_name:
            kwargs["os"] = os_name
        result = self._pwn.asm(source, **kwargs)
        return result.hex()

    async def disasm(self, hex_data: str, arch: str | None = None) -> str:
        """Disassemble bytes to source. Input as hex string."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        kwargs: dict[str, Any] = {}
        if arch:
            kwargs["arch"] = arch
        return self._pwn.disasm(data, **kwargs)

    async def make_elf(self, hex_data: str) -> str:
        """Wrap shellcode (hex) in minimal ELF. Returns hex of ELF."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        result = self._pwn.make_elf(data)
        return result.hex()

    async def make_elf_from_assembly(self, source: str) -> str:
        """Compile assembly to ELF. Returns hex."""
        self._require_ready()
        result = self._pwn.make_elf_from_assembly(source)
        return result.hex()

    # ── Shellcraft ───────────────────────────────────────

    async def shellcraft(self, name: str, arch: str | None = None, os_name: str | None = None, **kwargs) -> str:
        """Generate shellcode source by name (e.g. 'sh', 'cat', 'connect').

        Returns assembly source string.
        """
        self._require_ready()
        if arch:
            self._context.arch = arch
        if os_name:
            self._context.os = os_name
        sc = self._pwn.shellcraft
        # Navigate to the right shellcode function
        func = getattr(sc, name, None)
        if func is None:
            raise ValueError(f"Unknown shellcraft: {name}")
        return str(func(**kwargs))

    async def shellcraft_asm(self, name: str, arch: str | None = None, os_name: str | None = None, **kwargs) -> str:
        """Generate shellcode and assemble it. Returns hex bytes."""
        self._require_ready()
        source = await self.shellcraft(name, arch=arch, os_name=os_name, **kwargs)
        return await self.asm(source, arch=arch, os_name=os_name)

    async def shellcraft_list(self) -> list[str]:
        """List available shellcraft templates for current arch/os."""
        self._require_ready()
        sc = self._pwn.shellcraft
        return [name for name in dir(sc) if not name.startswith("_") and callable(getattr(sc, name, None))]

    # ── ELF analysis ────────────────────────────────────

    async def elf_load(self, path: str) -> dict:
        """Load an ELF binary. Returns basic info."""
        self._require_ready()
        elf = self._pwn.ELF(path, checksec=False)
        self._cache_elf(path, elf)
        return {
            "path": path,
            "arch": elf.arch,
            "bits": elf.bits,
            "endian": elf.endian,
            "entry": hex(elf.entry),
            "type": elf.elftype,
        }

    async def elf_checksec(self, path: str) -> dict:
        """Run checksec on ELF."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        return {
            "relro": elf.relro or "No RELRO",
            "canary": elf.canary,
            "nx": elf.nx,
            "pie": elf.pie,
            "rpath": bool(elf.rpath),
            "runpath": bool(elf.runpath),
            "fortify": bool(getattr(elf, "fortify", False)),
            "arch": elf.arch,
            "bits": elf.bits,
        }

    async def elf_symbols(self, path: str) -> dict[str, str]:
        """Get all symbols {name: hex_addr}."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        return {name: hex(addr) for name, addr in elf.symbols.items()}

    async def elf_got(self, path: str) -> dict[str, str]:
        """Get GOT entries {name: hex_addr}."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        return {name: hex(addr) for name, addr in elf.got.items()}

    async def elf_plt(self, path: str) -> dict[str, str]:
        """Get PLT entries {name: hex_addr}."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        return {name: hex(addr) for name, addr in elf.plt.items()}

    async def elf_functions(self, path: str) -> list[dict]:
        """List functions with address + size."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        return [
            {"name": name, "address": hex(func.address), "size": func.size}
            for name, func in elf.functions.items()
        ]

    async def elf_sections(self, path: str) -> list[dict]:
        """List sections with address, size, flags."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        result = []
        for name in elf.sections:
            sec = elf.get_section_by_name(name)
            if sec:
                result.append({
                    "name": name,
                    "address": hex(sec.header.sh_addr),
                    "size": sec.header.sh_size,
                    "type": sec.header.sh_type,
                })
        return result

    async def elf_search(self, path: str, needle: str, is_hex: bool = False) -> list[str]:
        """Search for bytes in ELF. Returns list of hex addresses."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        data = bytes.fromhex(needle) if is_hex else needle.encode()
        return [hex(addr) for addr in elf.search(data)]

    async def elf_bss(self, path: str, offset: int = 0) -> str:
        """Get BSS section address + optional offset."""
        self._require_ready()
        elf = self._elf_cache.get(path) or self._pwn.ELF(path, checksec=False)
        if path not in self._elf_cache:
            self._cache_elf(path, elf)
        return hex(elf.bss(offset))

    # ── ROP chain building ──────────────────────────────

    async def rop_create(self, elf_path: str) -> str:
        """Create ROP chain builder from ELF. Returns rop_id."""
        self._require_ready()
        elf = self._elf_cache.get(elf_path) or self._pwn.ELF(elf_path, checksec=False)
        if elf_path not in self._elf_cache:
            self._cache_elf(elf_path, elf)
        rop = self._pwn.ROP(elf)
        rop_id = f"rop_{id(rop)}"
        self._cache_rop(rop_id, rop)
        return rop_id

    async def rop_find_gadget(self, rop_id: str, instructions: list[str]) -> str | None:
        """Find a gadget matching instruction sequence. Returns hex addr or None."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        gadget = rop.find_gadget(instructions)
        if gadget:
            return hex(gadget.address) if hasattr(gadget, "address") else hex(gadget[0])
        return None

    async def rop_call(self, rop_id: str, function: str, args: list | None = None) -> None:
        """Add function call to ROP chain."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        rop.call(function, args or [])

    async def rop_raw(self, rop_id: str, value: int) -> None:
        """Add raw value to ROP chain."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        rop.raw(value)

    async def rop_chain(self, rop_id: str) -> str:
        """Generate the final ROP payload. Returns hex."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        return rop.chain().hex()

    async def rop_dump(self, rop_id: str) -> str:
        """Dump human-readable ROP chain."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        return rop.dump()

    async def rop_migrate(self, rop_id: str, address: int) -> None:
        """Stack pivot to address."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        rop.migrate(address)

    async def rop_set_registers(self, rop_id: str, registers: dict[str, int]) -> None:
        """Set register values via gadgets."""
        self._require_ready()
        rop = self._rop_cache.get(rop_id)
        if not rop:
            raise ValueError(f"Unknown ROP chain: {rop_id}")
        rop.setRegisters(registers)

    # ── Format string ────────────────────────────────────

    async def fmtstr_payload(
        self,
        offset: int,
        writes: dict[str, int],
        numbwritten: int = 0,
        write_size: str = "byte",
    ) -> str:
        """Generate format string payload. writes={hex_addr: value}. Returns hex."""
        self._require_ready()
        # Convert hex string keys to int addresses
        int_writes = {}
        for addr_str, value in writes.items():
            addr = int(addr_str, 16) if isinstance(addr_str, str) else addr_str
            int_writes[addr] = value
        result = self._pwn.fmtstr_payload(
            offset, int_writes,
            numbwritten=numbwritten,
            write_size=write_size,
        )
        return result.hex()

    # ── SROP ─────────────────────────────────────────────

    async def srop_frame(self, registers: dict[str, int], arch: str | None = None) -> str:
        """Build SigreturnFrame. Returns hex payload."""
        self._require_ready()
        if arch:
            self._context.arch = arch
        frame = self._pwn.SigreturnFrame()
        for reg, val in registers.items():
            setattr(frame, reg, val)
        return bytes(frame).hex()

    # ── Ret2dlresolve ────────────────────────────────────

    async def ret2dlresolve(self, elf_path: str, symbol: str, args: list | None = None) -> dict:
        """Build ret2dlresolve payload. Returns {payload_hex, reloc_index}."""
        self._require_ready()
        elf = self._elf_cache.get(elf_path) or self._pwn.ELF(elf_path, checksec=False)
        if elf_path not in self._elf_cache:
            self._cache_elf(elf_path, elf)
        dlresolve = self._pwn.Ret2dlresolvePayload(elf, symbol, args or [])
        return {
            "payload": dlresolve.payload.hex(),
            "reloc_index": dlresolve.reloc_index,
        }

    # ── Encoding / crypto ────────────────────────────────

    async def xor(self, hex_data: str, key: str) -> str:
        """XOR data with key. Both as hex. Returns hex."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        key_bytes = bytes.fromhex(key)
        result = self._pwn.xor(data, key_bytes)
        return result.hex()

    async def xor_key(self, hex_data: str, avoid: str = "00") -> dict:
        """Find XOR key that avoids specified bytes. Returns {key_hex, result_hex}."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        avoid_bytes = bytes.fromhex(avoid)
        key, result = self._pwn.xor_key(data, avoid=avoid_bytes)
        return {"key": key.hex(), "result": result.hex()}

    async def hexdump(self, hex_data: str, width: int = 16) -> str:
        """Pretty hexdump of data."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        return self._pwn.hexdump(data, width=width)

    async def enhex(self, data: str) -> str:
        """String to hex encoding."""
        self._require_ready()
        return self._pwn.enhex(data.encode())

    async def unhex(self, hex_str: str) -> str:
        """Hex to string decoding."""
        self._require_ready()
        return self._pwn.unhex(hex_str).decode(errors="replace")

    async def b64e(self, data: str) -> str:
        """Base64 encode."""
        self._require_ready()
        return self._pwn.b64e(data.encode()).decode()

    async def b64d(self, data: str) -> str:
        """Base64 decode."""
        self._require_ready()
        return self._pwn.b64d(data.encode()).decode(errors="replace")

    async def urlencode(self, data: str) -> str:
        """URL encode."""
        self._require_ready()
        return self._pwn.urlencode(data.encode()).decode()

    async def urldecode(self, data: str) -> str:
        """URL decode."""
        self._require_ready()
        return self._pwn.urldecode(data.encode()).decode(errors="replace")

    # ── Hashing ──────────────────────────────────────────

    async def hash_data(self, hex_data: str, algo: str = "sha256") -> str:
        """Hash data. Algorithms: md5, sha1, sha256, sha512. Returns hex digest."""
        self._require_ready()
        data = bytes.fromhex(hex_data)
        hash_funcs = {
            "md5": self._pwn.md5sumhex,
            "sha1": self._pwn.sha1sumhex,
            "sha256": self._pwn.sha256sumhex,
            "sha512": self._pwn.sha512sumhex,
        }
        func = hash_funcs.get(algo)
        if not func:
            raise ValueError(f"Unknown algo: {algo}. Use: {list(hash_funcs)}")
        return func(data)

    # ── Shellcode encoding ───────────────────────────────

    async def encode_shellcode(
        self,
        hex_shellcode: str,
        avoid: str = "00",
        encoder: str | None = None,
    ) -> str:
        """Encode shellcode to avoid bad bytes. Returns hex."""
        self._require_ready()
        data = bytes.fromhex(hex_shellcode)
        avoid_bytes = bytes.fromhex(avoid)
        kwargs: dict[str, Any] = {"avoid": avoid_bytes}
        if encoder:
            kwargs["force"] = True
        from pwnlib.encoders import encode
        result = encode(data, **kwargs)
        return result.hex()

    # ── Constants ────────────────────────────────────────

    async def get_constant(self, name: str) -> int | None:
        """Get a named constant (e.g. SYS_write, PROT_READ). Context-aware."""
        self._require_ready()
        try:
            return int(self._pwn.constants[name])
        except (KeyError, TypeError):
            return None

    async def list_constants(self, prefix: str = "SYS_") -> dict[str, int]:
        """List constants matching prefix. Returns {name: value}."""
        self._require_ready()
        result = {}
        for attr in dir(self._pwn.constants):
            if attr.startswith(prefix):
                with contextlib.suppress(TypeError, ValueError):
                    result[attr] = int(getattr(self._pwn.constants, attr))
        return result

    # ── Corefile analysis ────────────────────────────────

    async def corefile_load(self, path: str) -> dict:
        """Parse a core dump file."""
        self._require_ready()
        core = self._pwn.Corefile(path)
        regs = {}
        for reg in ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rsp", "rbp", "rip",
                     "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"):
            val = getattr(core, reg, None)
            if val is not None:
                regs[reg] = hex(val)
        return {
            "signal": core.signal,
            "fault_addr": hex(core.fault_addr) if core.fault_addr else None,
            "registers": regs,
            "mappings": [
                {"name": str(m.name), "start": hex(m.start), "end": hex(m.stop), "size": m.stop - m.start}
                for m in core.mappings
            ],
        }

    # ── Misc utilities ───────────────────────────────────

    async def bits_to_str(self, value: int, width: int = 32) -> str:
        """Integer to bit string representation."""
        self._require_ready()
        return format(value, f"0{width}b")

    async def rol(self, value: int, count: int, bits: int = 32) -> int:
        """Rotate left."""
        self._require_ready()
        return int(self._pwn.rol(value, count, bits))

    async def ror(self, value: int, count: int, bits: int = 32) -> int:
        """Rotate right."""
        self._require_ready()
        return int(self._pwn.ror(value, count, bits))

    # ── Properties ───────────────────────────────────────

    @property
    def loaded_elfs(self) -> list[str]:
        """List of loaded ELF paths."""
        return list(self._elf_cache.keys())

    @property
    def rop_chains(self) -> list[str]:
        """List of active ROP chain IDs."""
        return list(self._rop_cache.keys())


# Auto-register
bridge_registry.register("pwn", PwnBridge)
