"""Binary analysis utilities — comprehensive ELF analysis.

Uses file, readelf, strings, nm, objdump, ldd CLI tools via subprocess.
Covers: checksec, sections, symbols, relocations, GOT/PLT, strings,
imports, exports, dynamic symbols, dependencies, headers, hex dump.
"""

from __future__ import annotations

import logging
import re

from backend.app.core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)


class BinaryAnalyzer:
    """Comprehensive binary analysis via standard Linux tools."""

    def __init__(self, subprocess_manager: SubprocessManager) -> None:
        self._spm = subprocess_manager

    # ── file info ────────────────────────────────────────

    async def file_info(self, binary_path: str) -> dict:
        """Run `file` on binary. Returns {path, type, details}."""
        stdout, stderr, rc = await self._spm.execute(
            ["file", "-b", binary_path]
        )
        return {
            "path": binary_path,
            "type": stdout.strip().split(",")[0] if rc == 0 else "unknown",
            "details": stdout.strip() if rc == 0 else stderr.strip(),
            "success": rc == 0,
        }

    # ── checksec ─────────────────────────────────────────

    async def checksec(self, binary_path: str) -> dict:
        """Check binary security properties using readelf.

        Returns: {relro, canary, nx, pie, rpath, runpath, symbols, fortify}
        """
        result = {
            "path": binary_path,
            "relro": "none",
            "canary": False,
            "nx": False,
            "pie": False,
            "rpath": False,
            "runpath": False,
            "symbols": False,
            "fortify": False,
        }

        # ── readelf -W -l (RELRO, NX) ───────────────────
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-l", binary_path]
        )
        if rc == 0:
            if "GNU_RELRO" in stdout:
                result["relro"] = "partial"
            for line in stdout.splitlines():
                if "GNU_STACK" in line:
                    result["nx"] = "E" not in line.split()[-1] if line.split() else True

        # ── readelf -W -d (BIND_NOW → full RELRO, RPATH, RUNPATH)
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-d", binary_path]
        )
        if rc == 0:
            if "BIND_NOW" in stdout and result["relro"] == "partial":
                result["relro"] = "full"
            result["rpath"] = "RPATH" in stdout
            result["runpath"] = "RUNPATH" in stdout

        # ── readelf -W -s (canary, fortify, symbols) ────
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-s", binary_path]
        )
        if rc == 0:
            result["canary"] = "__stack_chk_fail" in stdout
            result["fortify"] = "__fortify_fail" in stdout or "___chk" in stdout
            result["symbols"] = "Symbol table '.symtab'" in stdout

        # ── readelf -W -h (PIE: Type = DYN) ─────────────
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-h", binary_path]
        )
        if rc == 0:
            result["pie"] = "DYN" in stdout and "Type:" in stdout

        return result

    # ── Sections ─────────────────────────────────────────

    async def sections(self, binary_path: str) -> list[dict]:
        """List ELF sections via readelf -S.

        Returns: [{name, type, address, offset, size, flags}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-S", binary_path]
        )
        if rc != 0:
            return []

        sections = []
        section_re = re.compile(
            r"\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+\S+\s+(\S*)"
        )
        for match in section_re.finditer(stdout):
            sections.append({
                "name": match.group(1),
                "type": match.group(2),
                "address": f"0x{match.group(3)}",
                "offset": f"0x{match.group(4)}",
                "size": int(match.group(5), 16),
                "flags": match.group(6),
            })
        return sections

    # ── ELF header ───────────────────────────────────────

    async def elf_header(self, binary_path: str) -> dict:
        """Parse ELF header via readelf -h.

        Returns: {class, data, type, machine, entry_point, ...}
        """
        stdout, stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-h", binary_path]
        )
        if rc != 0:
            return {"error": stderr.strip()}

        header = {}
        for line in stdout.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
                header[key] = val.strip()
        return header

    # ── Program headers ──────────────────────────────────

    async def program_headers(self, binary_path: str) -> list[dict]:
        """List ELF program headers (segments) via readelf -l.

        Returns: [{type, offset, vaddr, paddr, filesz, memsz, flags, align}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-l", binary_path]
        )
        if rc != 0:
            return []

        headers = []
        # Match: TYPE OFFSET VADDR PADDR FILESZ MEMSZ FLG ALIGN
        phdr_re = re.compile(
            r"^\s+(PHDR|INTERP|LOAD|DYNAMIC|NOTE|GNU_EH_FRAME|GNU_STACK|GNU_RELRO|TLS)\s+"
            r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+"
            r"(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S+)\s+(0x[0-9a-f]+)",
            re.MULTILINE | re.IGNORECASE,
        )
        for match in phdr_re.finditer(stdout):
            headers.append({
                "type": match.group(1),
                "offset": match.group(2),
                "vaddr": match.group(3),
                "paddr": match.group(4),
                "filesz": match.group(5),
                "memsz": match.group(6),
                "flags": match.group(7),
                "align": match.group(8),
            })
        return headers

    # ── Symbols (nm) ─────────────────────────────────────

    async def symbols(self, binary_path: str) -> list[dict]:
        """List symbols via nm. Returns [{address, type, name}]."""
        stdout, _stderr, rc = await self._spm.execute(
            ["nm", "-n", binary_path]
        )
        if rc != 0:
            return []

        symbols = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                symbols.append({
                    "address": f"0x{parts[0]}",
                    "type": parts[1],
                    "name": parts[2],
                })
            elif len(parts) == 2:
                # Undefined symbols (no address)
                symbols.append({
                    "address": "",
                    "type": parts[0],
                    "name": parts[1],
                })
        return symbols

    # ── Dynamic symbols ──────────────────────────────────

    async def dynamic_symbols(self, binary_path: str) -> list[dict]:
        """List dynamic symbols via readelf --dyn-syms.

        Returns: [{num, value, size, type, bind, vis, ndx, name}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "--dyn-syms", binary_path]
        )
        if rc != 0:
            return []

        syms = []
        # Parse: Num: Value Size Type Bind Vis Ndx Name
        sym_re = re.compile(
            r"^\s+(\d+):\s+([0-9a-f]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)[ \t]+([^\n]*)$",
            re.MULTILINE,
        )
        for match in sym_re.finditer(stdout):
            name = match.group(8).strip()
            if name:
                syms.append({
                    "num": int(match.group(1)),
                    "value": f"0x{match.group(2)}",
                    "size": int(match.group(3)),
                    "type": match.group(4),
                    "bind": match.group(5),
                    "visibility": match.group(6),
                    "ndx": match.group(7),
                    "name": name,
                })
        return syms

    # ── Imports & exports ────────────────────────────────

    async def imports(self, binary_path: str) -> list[dict]:
        """List imported functions (UND symbols from dynamic symbols)."""
        dynsyms = await self.dynamic_symbols(binary_path)
        return [s for s in dynsyms if s["ndx"] == "UND" and s["name"]]

    async def exports(self, binary_path: str) -> list[dict]:
        """List exported functions (GLOBAL defined symbols)."""
        dynsyms = await self.dynamic_symbols(binary_path)
        return [
            s for s in dynsyms
            if s["ndx"] != "UND" and s["bind"] == "GLOBAL" and s["name"]
        ]

    # ── Relocations ──────────────────────────────────────

    async def relocations(self, binary_path: str) -> list[dict]:
        """List relocations via readelf -r.

        Returns: [{offset, info, type, value, name}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["readelf", "-W", "-r", binary_path]
        )
        if rc != 0:
            return []

        relocs = []
        # Offset Info Type Sym.Value Sym.Name + Addend
        reloc_re = re.compile(
            r"^([0-9a-f]+)\s+([0-9a-f]+)\s+(\S+)\s+([0-9a-f]+)\s+(.*?)$",
            re.MULTILINE,
        )
        for match in reloc_re.finditer(stdout):
            relocs.append({
                "offset": f"0x{match.group(1)}",
                "info": f"0x{match.group(2)}",
                "type": match.group(3),
                "value": f"0x{match.group(4)}",
                "name": match.group(5).strip(),
            })
        return relocs

    # ── GOT / PLT ────────────────────────────────────────

    async def got_entries(self, binary_path: str) -> list[dict]:
        """Extract GOT entries via objdump.

        Returns: [{address, name}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["objdump", "-R", binary_path]
        )
        if rc != 0:
            return []

        entries = []
        got_re = re.compile(
            r"^([0-9a-f]+)\s+(\S+)\s+(.*)$",
            re.MULTILINE,
        )
        for match in got_re.finditer(stdout):
            entries.append({
                "address": f"0x{match.group(1)}",
                "type": match.group(2),
                "name": match.group(3).strip(),
            })
        return entries

    async def plt_entries(self, binary_path: str) -> list[dict]:
        """Extract PLT entries via objdump -d (filter .plt section).

        Returns: [{address, name}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["objdump", "-d", "-j", ".plt", binary_path]
        )
        if rc != 0:
            return []

        entries = []
        # Match: 0000000000401020 <puts@plt>:
        plt_re = re.compile(r"^([0-9a-f]+)\s+<(.+?)>:", re.MULTILINE)
        for match in plt_re.finditer(stdout):
            entries.append({
                "address": f"0x{match.group(1)}",
                "name": match.group(2),
            })
        return entries

    # ── Strings ──────────────────────────────────────────

    async def strings(self, binary_path: str, min_length: int = 4) -> list[dict]:
        """Extract printable strings via strings command.

        Returns: [{offset, string, section}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["strings", "-a", "-t", "x", f"-n{min_length}", binary_path]
        )
        if rc != 0:
            return []

        result = []
        for line in stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                result.append({
                    "offset": f"0x{parts[0]}",
                    "string": parts[1],
                })
        return result

    # ── Shared library dependencies ──────────────────────

    async def dependencies(self, binary_path: str) -> list[dict]:
        """List shared library dependencies via ldd.

        Returns: [{name, path, address}]
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["ldd", binary_path]
        )
        if rc != 0:
            return []

        deps = []
        # libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007f...)
        ldd_re = re.compile(
            r"^\s+(\S+)\s+=>\s+(\S+)\s+\(([0-9a-fx]+)\)",
            re.MULTILINE,
        )
        for match in ldd_re.finditer(stdout):
            deps.append({
                "name": match.group(1),
                "path": match.group(2),
                "address": match.group(3),
            })
        # Also match: linux-vdso.so.1 (0x00007fff...)
        vdso_re = re.compile(r"^\s+(\S+)\s+\(([0-9a-fx]+)\)", re.MULTILINE)
        for match in vdso_re.finditer(stdout):
            name = match.group(1)
            if not any(d["name"] == name for d in deps):
                deps.append({
                    "name": name,
                    "path": "",
                    "address": match.group(2),
                })
        return deps

    # ── Objdump disassembly ──────────────────────────────

    async def disassemble(
        self,
        binary_path: str,
        *,
        section: str | None = None,
        start_address: str | None = None,
        stop_address: str | None = None,
        intel_syntax: bool = True,
    ) -> str:
        """Disassemble via objdump. Returns raw text.

        More flexible than readelf — supports section filtering, syntax choice.
        """
        cmd = ["objdump", "-d"]
        if intel_syntax:
            cmd += ["-M", "intel"]
        if section:
            cmd += ["-j", section]
        if start_address:
            cmd += [f"--start-address={start_address}"]
        if stop_address:
            cmd += [f"--stop-address={stop_address}"]
        cmd.append(binary_path)

        stdout, _stderr, rc = await self._spm.execute(cmd)
        return stdout if rc == 0 else ""

    # ── Hex dump ─────────────────────────────────────────

    async def hexdump(
        self, binary_path: str, offset: int = 0, length: int = 256
    ) -> str:
        """Hex dump a region of the binary via xxd.

        Returns formatted hex dump string.
        """
        cmd = ["xxd", "-s", str(offset), "-l", str(length), binary_path]
        stdout, _stderr, rc = await self._spm.execute(cmd)
        return stdout if rc == 0 else ""

    # ── Size info ────────────────────────────────────────

    async def size_info(self, binary_path: str) -> dict:
        """Get section sizes via size command.

        Returns: {text, data, bss, total, filename}
        """
        stdout, _stderr, rc = await self._spm.execute(
            ["size", binary_path]
        )
        if rc != 0:
            return {}

        lines = stdout.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                return {
                    "text": int(parts[0]),
                    "data": int(parts[1]),
                    "bss": int(parts[2]),
                    "total": int(parts[3]),
                    "filename": parts[4] if len(parts) > 4 else binary_path,
                }
        return {}
