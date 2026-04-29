"""Rizin Bridge — comprehensive reverse engineering via rzpipe.

Wraps rizin (radare2 fork) with full feature coverage:
- Binary loading & analysis (aaa, aaaa)
- Functions (afl, afij, pdf)
- Disassembly (pd, pD, pi)
- Strings (iz, izz)
- Imports / Exports (ii, iE)
- Symbols (is)
- Sections (iS)
- Segments (iSS)
- Entry points (ie)
- Relocations (ir)
- Cross-references (axt, axf)
- Binary info (i, iI)
- Search (/x, /s, /R for ROP)
- Flags (f)
- Comments (CC)
- Types (t)
- Classes (ic)
- Memory read (px, pxj)
- Patching (wx, w)
- Graph / CFG (agj, agCj)
- Decompiler (pdg via r2ghidra, pdd)
- Hex editor (wv, wz)
- ESIL emulation (aei, aes, aer)
- Zignatures (z)
- Hashing (rahash2)
- Diffing (radiff2)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import bridge_registry
from backend.app.core.exceptions import BridgeCrash
from backend.app.core.sanitization import sanitize_rizin_input, validate_file_path

logger = logging.getLogger(__name__)


class RizinBridge(BaseBridge):
    """Rizin bridge via rzpipe — manages a rizin session for RE analysis."""

    bridge_type = "rizin"

    def __init__(self, binary_path: str | None = None) -> None:
        super().__init__()
        self._binary_path = binary_path
        self._pipe: Any = None  # rzpipe.open() handle
        self._analyzed = False

    async def start(self) -> None:
        """Open rizin on the binary (or empty if no binary)."""
        self.state = BridgeState.STARTING
        try:
            import rzpipe

            target = self._binary_path or ""
            self._pipe = rzpipe.open(target, flags=["-2"])
            self.state = BridgeState.READY
            logger.info("Rizin bridge started: %s", target or "(no binary)")
        except Exception as e:
            self.state = BridgeState.ERROR
            raise BridgeCrash("rizin", exit_code=None) from e

    async def stop(self) -> None:
        """Close the rizin pipe."""
        self.state = BridgeState.STOPPING
        if self._pipe is not None:
            try:
                self._pipe.quit()
            except Exception:
                logger.exception("Error closing rizin")
            finally:
                self._pipe = None
        self.state = BridgeState.STOPPED
        logger.info("Rizin bridge stopped")

    async def health(self) -> bool:
        if self._pipe is None:
            return False
        try:
            self._pipe.cmd("?V")
            return True
        except Exception:
            return False

    async def execute(self, command: str, **kwargs: Any) -> Any:
        """Execute a raw rizin command. Returns string output."""
        self._require_ready()
        sanitize_rizin_input(command, "command")
        return self._pipe.cmd(command)

    def _cmdj(self, command: str) -> Any:
        """Execute a command and parse JSON output."""
        self._require_ready()
        try:
            result = self._pipe.cmdj(command)
            return result if result is not None else []
        except (json.JSONDecodeError, Exception):
            # Fallback: return raw string
            return self._pipe.cmd(command)

    # ── Analysis ─────────────────────────────────────────

    async def analyze(self, level: str = "aaa") -> dict:
        """Run analysis. Levels: aa, aaa, aaaa. Returns structured dict for MCP."""
        self._require_ready()
        if level not in ("aa", "aaa", "aaaa"):
            level = "aaa"
        raw = self._pipe.cmd(level)
        self._analyzed = True
        funcs = self._cmdj("aflj") or []
        return {"status": "ok", "level": level, "functions_found": len(funcs), "raw": raw}

    async def open_binary(self, binary_path: str, *, allowed_dirs: list[str] | None = None) -> str:
        """Open a new binary file in the current session."""
        self._require_ready()
        validate_file_path(binary_path, allowed_dirs=allowed_dirs, field_name="binary_path")
        sanitize_rizin_input(binary_path, "binary_path")
        self._binary_path = binary_path
        self._analyzed = False
        return self._pipe.cmd(f"o {binary_path}")

    # ── Binary info ──────────────────────────────────────

    async def binary_info(self) -> dict:
        """Get binary info (iIj)."""
        self._require_ready()
        return self._cmdj("iIj") or {}

    async def file_info(self) -> dict:
        """Get file info (ij)."""
        self._require_ready()
        return self._cmdj("ij") or {}

    async def entry_points(self) -> list[dict]:
        """List entry points (iej)."""
        self._require_ready()
        return self._cmdj("iej") or []

    # ── Functions ────────────────────────────────────────

    async def functions(self) -> list[dict]:
        """List all functions (aflj)."""
        self._require_ready()
        return self._cmdj("aflj") or []

    async def function_info(self, address: str) -> dict:
        """Get detailed function info (afij @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        result = self._cmdj(f"afij @ {address}")
        if isinstance(result, list) and result:
            return result[0]
        return result if isinstance(result, dict) else {}

    async def function_xrefs_to(self, address: str) -> list[dict]:
        """Get cross-references TO this function (axtj @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"axtj @ {address}") or []

    async def function_xrefs_from(self, address: str) -> list[dict]:
        """Get cross-references FROM this function (axfj @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"axfj @ {address}") or []

    async def function_callgraph(self, address: str) -> list[dict]:
        """Get function call graph (agCj @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"agCj @ {address}") or []

    async def function_cfg(self, address: str) -> list[dict]:
        """Get control flow graph for function (agj @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"agj @ {address}") or []

    async def rename_function(self, address: str, new_name: str) -> str:
        """Rename a function (afn name @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        sanitize_rizin_input(new_name, "new_name")
        return self._pipe.cmd(f"afn {new_name} @ {address}")

    # ── Disassembly ──────────────────────────────────────

    async def disassemble_function(self, address: str) -> list[dict]:
        """Disassemble a function (pdfj @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        result = self._cmdj(f"pdfj @ {address}")
        if isinstance(result, dict):
            return result.get("ops", [])
        return result if isinstance(result, list) else []

    async def disassemble(self, address: str, count: int = 32) -> list[dict]:
        """Disassemble N instructions at address (pdj N @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"pdj {count} @ {address}") or []

    async def disassemble_bytes(self, address: str, nbytes: int = 64) -> list[dict]:
        """Disassemble N bytes at address (pDj N @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"pDj {nbytes} @ {address}") or []

    async def disassemble_text(self, address: str, count: int = 32) -> str:
        """Disassemble as plain text (pi N @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"pi {count} @ {address}")

    # ── Decompiler ───────────────────────────────────────

    async def decompile(self, address: str) -> dict:
        """Decompile function via r2ghidra (pdg @ addr). Returns structured dict for MCP.

        Falls back to pdd if r2ghidra not available.
        """
        self._require_ready()
        sanitize_rizin_input(address, "address")
        result = self._pipe.cmd(f"pdg @ {address}")
        if result and "Cannot" not in result and "error" not in result.lower():
            return {"address": address, "language": "c", "code": result, "source": "rz-ghidra"}
        code = self._pipe.cmd(f"pdd @ {address}")
        return {"address": address, "language": "c", "code": code, "source": "rz-dec"}

    # ── Strings ──────────────────────────────────────────

    async def strings(self) -> list[dict]:
        """List strings in data sections (izj)."""
        self._require_ready()
        return self._cmdj("izj") or []

    async def strings_all(self) -> list[dict]:
        """List ALL strings in entire binary (izzj)."""
        self._require_ready()
        return self._cmdj("izzj") or []

    # ── Imports / Exports ────────────────────────────────

    async def imports(self) -> list[dict]:
        """List imports (iij)."""
        self._require_ready()
        return self._cmdj("iij") or []

    async def exports(self) -> list[dict]:
        """List exports (iEj)."""
        self._require_ready()
        return self._cmdj("iEj") or []

    # ── Symbols ──────────────────────────────────────────

    async def symbols(self) -> list[dict]:
        """List symbols (isj)."""
        self._require_ready()
        return self._cmdj("isj") or []

    # ── Sections & segments ──────────────────────────────

    async def sections(self) -> list[dict]:
        """List sections (iSj)."""
        self._require_ready()
        return self._cmdj("iSj") or []

    async def segments(self) -> list[dict]:
        """List segments (iSSj)."""
        self._require_ready()
        return self._cmdj("iSSj") or []

    # ── Relocations ──────────────────────────────────────

    async def relocations(self) -> list[dict]:
        """List relocations (irj)."""
        self._require_ready()
        return self._cmdj("irj") or []

    # ── Classes ──────────────────────────────────────────

    async def classes(self) -> list[dict]:
        """List classes (icj) — useful for C++/Java binaries."""
        self._require_ready()
        return self._cmdj("icj") or []

    # ── Headers ──────────────────────────────────────────

    async def headers(self) -> list[dict]:
        """List headers (ihj)."""
        self._require_ready()
        return self._cmdj("ihj") or []

    async def libraries(self) -> list[dict]:
        """List linked libraries (ilj)."""
        self._require_ready()
        return self._cmdj("ilj") or []

    # ── Memory / hex ─────────────────────────────────────

    async def read_hex(self, address: str, length: int = 256) -> list[dict]:
        """Read hex bytes at address (pxj N @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._cmdj(f"pxj {length} @ {address}") or []

    async def read_hex_text(self, address: str, length: int = 256) -> str:
        """Read hex dump as text (px N @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"px {length} @ {address}")

    async def print_string(self, address: str) -> str:
        """Print string at address (ps @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"ps @ {address}")

    # ── Write / patch ────────────────────────────────────

    async def write_hex(self, address: str, hex_data: str) -> str:
        """Write hex bytes at address (wx hex @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        sanitize_rizin_input(hex_data, "hex_data")
        return self._pipe.cmd(f"wx {hex_data} @ {address}")

    async def write_string(self, address: str, string: str) -> str:
        """Write string at address (w string @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        sanitize_rizin_input(string, "string")
        return self._pipe.cmd(f"w {string} @ {address}")

    async def write_assembly(self, address: str, instruction: str) -> str:
        """Write assembly instruction at address (wa inst @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        sanitize_rizin_input(instruction, "instruction")
        return self._pipe.cmd(f"wa {instruction} @ {address}")

    async def nop_fill(self, address: str, count: int = 1) -> str:
        """Fill N bytes with NOP at address (wao nop * count)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        # Seek + write NOPs
        nops = "90" * count
        return self._pipe.cmd(f"wx {nops} @ {address}")

    # ── Search ───────────────────────────────────────────

    async def search_hex(self, hex_pattern: str) -> list[dict]:
        """Search for hex pattern (/xj pattern)."""
        self._require_ready()
        sanitize_rizin_input(hex_pattern, "hex_pattern")
        return self._cmdj(f"/xj {hex_pattern}") or []

    async def search_string(self, string: str) -> list[dict]:
        """Search for string (/j string)."""
        self._require_ready()
        sanitize_rizin_input(string, "string")
        return self._cmdj(f"/j {string}") or []

    async def search_rop(self, regex: str = "") -> list[dict]:
        """Search ROP gadgets (/Rj regex).

        If no regex, lists all gadgets. Can filter: /Rj pop rdi
        """
        self._require_ready()
        if regex:
            sanitize_rizin_input(regex, "regex")
        cmd = f"/Rj {regex}" if regex else "/Rj"
        return self._cmdj(cmd) or []

    async def search_crypto(self) -> list[dict]:
        """Search for crypto constants (/caj)."""
        self._require_ready()
        return self._cmdj("/caj") or []

    # ── Flags & comments ─────────────────────────────────

    async def flags(self) -> list[dict]:
        """List all flags (fj)."""
        self._require_ready()
        return self._cmdj("fj") or []

    async def set_flag(self, name: str, address: str, size: int = 1) -> str:
        """Set a flag (f name size @ addr)."""
        self._require_ready()
        sanitize_rizin_input(name, "name")
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"f {name} {size} @ {address}")

    async def add_comment(self, address: str, comment: str) -> str:
        """Add a comment at address (CC comment @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        sanitize_rizin_input(comment, "comment")
        return self._pipe.cmd(f"CC {comment} @ {address}")

    async def get_comments(self) -> list[dict]:
        """List all comments (CCj)."""
        self._require_ready()
        return self._cmdj("CCj") or []

    async def delete_comment(self, address: str) -> str:
        """Delete comment at address (CC- @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"CC- @ {address}")

    # ── Types ────────────────────────────────────────────

    async def types(self) -> list[dict]:
        """List defined types (tj)."""
        self._require_ready()
        return self._cmdj("tj") or []

    # ── Seek ─────────────────────────────────────────────

    async def seek(self, address: str) -> str:
        """Seek to address (s addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"s {address}")

    async def current_seek(self) -> str:
        """Get current seek position (s)."""
        self._require_ready()
        return self._pipe.cmd("s").strip()

    # ── ESIL emulation ───────────────────────────────────

    async def esil_init(self) -> str:
        """Initialize ESIL VM (aei; aeim)."""
        self._require_ready()
        self._pipe.cmd("aei")
        return self._pipe.cmd("aeim")

    async def esil_step(self) -> str:
        """Step one ESIL instruction (aes)."""
        self._require_ready()
        return self._pipe.cmd("aes")

    async def esil_step_over(self) -> str:
        """Step over in ESIL (aeso)."""
        self._require_ready()
        return self._pipe.cmd("aeso")

    async def esil_continue(self) -> str:
        """Continue ESIL until break (aec)."""
        self._require_ready()
        return self._pipe.cmd("aec")

    async def esil_registers(self) -> dict:
        """Get ESIL VM registers (aerj)."""
        self._require_ready()
        return self._cmdj("aerj") or {}

    async def esil_set_register(self, register: str, value: str) -> str:
        """Set ESIL register value (aer reg=val)."""
        self._require_ready()
        sanitize_rizin_input(register, "register")
        sanitize_rizin_input(value, "value")
        return self._pipe.cmd(f"aer {register}={value}")

    # ── Hashing ──────────────────────────────────────────

    async def hash_block(self, address: str, size: int, algo: str = "md5") -> str:
        """Hash a block of data (ph algo size @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        sanitize_rizin_input(algo, "algo")
        return self._pipe.cmd(f"ph {algo} {size} @ {address}").strip()

    # ── Visual / graph ───────────────────────────────────

    async def ascii_graph(self, address: str) -> str:
        """ASCII control flow graph (agf @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"agf @ {address}")

    async def dot_graph(self, address: str) -> str:
        """DOT format call graph (agCd @ addr)."""
        self._require_ready()
        sanitize_rizin_input(address, "address")
        return self._pipe.cmd(f"agCd @ {address}")

    # ── Projects ─────────────────────────────────────────

    async def save_project(self, name: str) -> str:
        """Save current analysis as project (Ps name)."""
        self._require_ready()
        sanitize_rizin_input(name, "name")
        return self._pipe.cmd(f"Ps {name}")

    async def load_project(self, name: str) -> str:
        """Load a saved project (Po name)."""
        self._require_ready()
        sanitize_rizin_input(name, "name")
        return self._pipe.cmd(f"Po {name}")

    # ── Metadata ─────────────────────────────────────────

    @property
    def binary_path(self) -> str | None:
        return self._binary_path

    @property
    def is_analyzed(self) -> bool:
        return self._analyzed


# Auto-register
bridge_registry.register("rizin", RizinBridge)
