"""Firmware Bridge — firmware analysis via binwalk (v3 CLI + v2 Python fallback).

Wraps binwalk with full feature coverage:
- Signature scan (identify embedded files, firmware headers, crypto, filesystems)
- Extraction (automatic, recursive, carve)
- Entropy analysis (Shannon entropy blocks + PNG graph)
- Filtered scans (crypto-only, filesystem-only, compression-only)
- String extraction
- Architecture detection (opcode scan)
- Raw byte search
- Secret scanning (keys, certificates, passwords)
- Filesystem listing of extracted contents
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from backend.app.bridges.base import BaseBridge, BridgeState
from backend.app.bridges.registry import bridge_registry
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady

logger = logging.getLogger(__name__)

# Signature filter groups
CRYPTO_SIGS = (
    "aes_sbox,aes_forward_table,aes_reverse_table,aes_rcon,"
    "aes_acceleration_table,rsa,pem_certificate,pem_public_key,"
    "pem_private_key,openssl,luks,dpapi,gpg_signed"
)
FILESYSTEM_SIGS = (
    "squashfs,cramfs,jffs2,ubifs,ubi,ext,fat,ntfs,romfs,yaffs,apfs,btrfs,logfs"
)
COMPRESSION_SIGS = (
    "gzip,bzip2,lzma,xz,lz4,lzop,lzfse,zstd,zlib,compressd"
)

# Secret scanning patterns
SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key"),
    (r"-----BEGIN CERTIFICATE-----", "certificate"),
    (r"-----BEGIN PUBLIC KEY-----", "public_key"),
    (r"(?:password|passwd|pwd)\s*[=:]\s*\S+", "password"),
    (r"(?:api[_-]?key|apikey|token)\s*[=:]\s*\S+", "api_key"),
    (r"(?:secret|aws_secret)\s*[=:]\s*\S+", "secret"),
    (r"[A-Za-z0-9+/]{40,}={0,2}", "base64_blob"),
    (r"(?:ssh-rsa|ssh-ed25519|ecdsa-sha2)\s+\S+", "ssh_key"),
]
_SECRET_RE = [(re.compile(p, re.IGNORECASE), label) for p, label in SECRET_PATTERNS]


class FirmwareBridge(BaseBridge):
    """Firmware analysis bridge via binwalk."""

    bridge_type = "firmware"

    def __init__(self, workspace_dir: str | None = None) -> None:
        super().__init__()
        self._workspace = workspace_dir or tempfile.mkdtemp(prefix="anvil_fw_")
        self._binwalk_version: str | None = None
        self._use_v3_cli = False   # v3 Rust CLI with JSON
        self._use_v2_python = False  # v2 Python module
        self._spm: Any = None  # SubprocessManager reference

    async def start(self, subprocess_manager: Any = None) -> None:
        """Detect binwalk version and capabilities."""
        self.state = BridgeState.STARTING
        self._spm = subprocess_manager
        try:
            # Try binwalk CLI
            if self._spm:
                stdout, _stderr, rc = await self._spm.execute(["binwalk", "--help"])
                if rc == 0:
                    # v3 has --log, v2 doesn't
                    if "--log" in stdout:
                        self._use_v3_cli = True
                        self._binwalk_version = "3.x"
                    else:
                        self._use_v3_cli = False
                        self._binwalk_version = "2.x"
            # Try Python module as fallback
            if not self._use_v3_cli:
                try:
                    import binwalk
                    self._use_v2_python = True
                    self._binwalk_version = getattr(binwalk, "__version__", "2.x")
                except ImportError:
                    pass

            if not self._use_v3_cli and not self._use_v2_python:
                raise RuntimeError("binwalk not found (neither CLI nor Python module)")

            self.state = BridgeState.READY
            mode = "v3 CLI" if self._use_v3_cli else "v2 Python"
            logger.info("Firmware bridge started (%s, binwalk %s)", mode, self._binwalk_version)
        except Exception as e:
            self.state = BridgeState.ERROR
            raise BridgeCrash("firmware", exit_code=None) from e

    async def stop(self) -> None:
        """Cleanup workspace."""
        self.state = BridgeState.STOPPING
        self._spm = None
        self.state = BridgeState.STOPPED
        logger.info("Firmware bridge stopped")

    async def health(self) -> bool:
        return self._use_v3_cli or self._use_v2_python

    async def execute(self, command: str, **kwargs: Any) -> Any:
        """Generic execute."""
        self._require_ready()
        method = getattr(self, command, None)
        if method and callable(method):
            import inspect
            result = method(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        raise ValueError(f"Unknown command: {command}")

    # ── Internal helpers ─────────────────────────────────

    async def _run_binwalk_cli(self, args: list[str], binary_path: str) -> tuple[str, str, int]:
        """Run binwalk CLI command."""
        if not self._spm:
            raise BridgeNotReady("firmware")
        cmd = ["binwalk", *args, binary_path]
        return await self._spm.execute(cmd)

    async def _run_binwalk_v3_json(self, args: list[str], binary_path: str) -> list[dict]:
        """Run binwalk v3 with JSON output (--log=-)."""
        stdout, stderr, rc = await self._run_binwalk_cli(["--log=-", *args], binary_path)
        if rc != 0:
            logger.warning("binwalk failed: %s", stderr)
            return []
        try:
            return json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            logger.warning("binwalk JSON parse error: %s", stdout[:200])
            return []

    async def _run_binwalk_v2(self, binary_path: str, **kwargs) -> list[dict]:
        """Run binwalk v2 Python module."""
        import binwalk
        results = []
        for module in binwalk.scan(binary_path, quiet=True, **kwargs):
            for result in module.results:
                entry: dict[str, Any] = {
                    "offset": result.offset,
                    "description": result.description,
                    "module": getattr(result, "module", ""),
                }
                if hasattr(result, "value"):
                    entry["entropy"] = result.value
                results.append(entry)
        return results

    # ── Signature scan ───────────────────────────────────

    async def scan(self, binary_path: str) -> list[dict]:
        """Signature scan — identify embedded files, headers, crypto."""
        self._require_ready()
        if self._use_v3_cli:
            data = await self._run_binwalk_v3_json([], binary_path)
            return self._parse_v3_analysis(data)
        return await self._run_binwalk_v2(binary_path, signature=True)

    async def scan_filtered(
        self,
        binary_path: str,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> list[dict]:
        """Scan with include/exclude signature filters."""
        self._require_ready()
        if self._use_v3_cli:
            args = []
            if include:
                args.extend(["-y", ",".join(include)])
            if exclude:
                args.extend(["-x", ",".join(exclude)])
            data = await self._run_binwalk_v3_json(args, binary_path)
            return self._parse_v3_analysis(data)
        # v2: use include/exclude regex
        kwargs: dict[str, Any] = {"signature": True}
        if include:
            kwargs["include"] = "|".join(include)
        if exclude:
            kwargs["exclude"] = "|".join(exclude)
        return await self._run_binwalk_v2(binary_path, **kwargs)

    async def scan_crypto(self, binary_path: str) -> list[dict]:
        """Scan for crypto signatures only (AES S-boxes, RSA keys, certs)."""
        self._require_ready()
        return await self.scan_filtered(binary_path, include=CRYPTO_SIGS.split(","))

    async def scan_filesystems(self, binary_path: str) -> list[dict]:
        """Scan for filesystem signatures only."""
        self._require_ready()
        return await self.scan_filtered(binary_path, include=FILESYSTEM_SIGS.split(","))

    async def scan_compression(self, binary_path: str) -> list[dict]:
        """Scan for compression signatures only."""
        self._require_ready()
        return await self.scan_filtered(binary_path, include=COMPRESSION_SIGS.split(","))

    # ── Extraction ───────────────────────────────────────

    async def extract(self, binary_path: str, output_dir: str | None = None) -> dict:
        """Extract identified files."""
        self._require_ready()
        out_dir = output_dir or os.path.join(self._workspace, "extracted")
        os.makedirs(out_dir, exist_ok=True)

        if self._use_v3_cli:
            data = await self._run_binwalk_v3_json(["-e", "-d", out_dir], binary_path)
            return {
                "output_dir": out_dir,
                "results": self._parse_v3_analysis(data),
                "extractions": self._parse_v3_extractions(data),
            }
        await self._run_binwalk_v2(binary_path, extract=True, directory=out_dir)
        return {
            "output_dir": out_dir,
            "files": self._list_extracted(out_dir),
        }

    async def extract_recursive(self, binary_path: str, output_dir: str | None = None) -> dict:
        """Recursive extraction (matryoshka mode)."""
        self._require_ready()
        out_dir = output_dir or os.path.join(self._workspace, "extracted")
        os.makedirs(out_dir, exist_ok=True)

        if self._use_v3_cli:
            data = await self._run_binwalk_v3_json(["-Me", "-d", out_dir], binary_path)
            return {
                "output_dir": out_dir,
                "results": self._parse_v3_analysis(data),
            }
        await self._run_binwalk_v2(binary_path, extract=True, matryoshka=True, directory=out_dir)
        return {
            "output_dir": out_dir,
            "files": self._list_extracted(out_dir),
        }

    async def carve(self, binary_path: str, output_dir: str | None = None) -> dict:
        """Carve all sections (known + unknown) to disk."""
        self._require_ready()
        out_dir = output_dir or os.path.join(self._workspace, "carved")
        os.makedirs(out_dir, exist_ok=True)

        if self._use_v3_cli:
            data = await self._run_binwalk_v3_json(["--carve", "-d", out_dir], binary_path)
            return {"output_dir": out_dir, "results": self._parse_v3_analysis(data)}
        # v2 doesn't have direct carve — use extract
        await self._run_binwalk_v2(binary_path, extract=True, directory=out_dir)
        return {"output_dir": out_dir, "files": self._list_extracted(out_dir)}

    # ── Entropy analysis ─────────────────────────────────

    async def entropy(self, binary_path: str) -> list[dict]:
        """Calculate Shannon entropy blocks. Returns [{start, end, entropy}]."""
        self._require_ready()
        if self._use_v3_cli:
            data = await self._run_binwalk_v3_json(["-E"], binary_path)
            return self._parse_v3_entropy(data)
        # v2 returns entropy per block
        results = await self._run_binwalk_v2(binary_path, entropy=True)
        return [
            {"offset": r["offset"], "entropy": r.get("entropy", 0.0)}
            for r in results if "entropy" in r
        ]

    async def entropy_graph(self, binary_path: str, output_path: str | None = None) -> str:
        """Generate entropy PNG graph. Returns path to PNG."""
        self._require_ready()
        out_path = output_path or os.path.join(self._workspace, "entropy.png")
        if self._use_v3_cli:
            await self._run_binwalk_cli(["-E", "--png=" + out_path], binary_path)
        else:
            import binwalk
            for _module in binwalk.scan(binary_path, entropy=True, quiet=True, nplot=False):
                pass
            # v2 saves to current directory
        return out_path

    # ── Strings ──────────────────────────────────────────

    async def strings(self, binary_path: str, min_length: int = 4) -> list[dict]:
        """Extract printable strings with offsets."""
        self._require_ready()
        # Use system `strings` command for reliability
        if self._spm:
            stdout, _, rc = await self._spm.execute(
                ["strings", "-a", "-t", "x", f"-n{min_length}", binary_path]
            )
            if rc == 0:
                result = []
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.strip().split(None, 1)
                        if len(parts) == 2:
                            try:
                                offset = int(parts[0], 16)
                                result.append({"offset": offset, "string": parts[1]})
                            except ValueError:
                                pass
                return result
        # Fallback to v2
        if self._use_v2_python:
            return await self._run_binwalk_v2(binary_path, string=True)
        return []

    # ── Architecture detection ───────────────────────────

    async def opcodes(self, binary_path: str) -> list[dict]:
        """Identify CPU architecture via opcode pattern scanning."""
        self._require_ready()
        if self._use_v2_python:
            return await self._run_binwalk_v2(binary_path, opcodes=True)
        # v3 CLI doesn't have opcode scan — fall back to file command
        if self._spm:
            stdout, _, rc = await self._spm.execute(["file", "-b", binary_path])
            if rc == 0:
                return [{"offset": 0, "description": stdout.strip()}]
        return []

    # ── Raw byte search ──────────────────────────────────

    async def search_raw(self, binary_path: str, hex_pattern: str) -> list[dict]:
        """Search for raw byte pattern in firmware."""
        self._require_ready()
        pattern = bytes.fromhex(hex_pattern)
        if self._spm:
            # Use grep -P for binary search
            stdout, _, rc = await self._spm.execute(
                ["grep", "-b", "-o", "-a", "-P", pattern.decode("latin-1"), binary_path]
            )
            if rc == 0:
                results = []
                for line in stdout.strip().split("\n"):
                    if ":" in line:
                        offset_str = line.split(":")[0]
                        with contextlib.suppress(ValueError):
                            results.append({"offset": int(offset_str), "pattern": hex_pattern})
                return results
        return []

    # ── Secret scanning ──────────────────────────────────

    async def scan_secrets(self, binary_path: str) -> list[dict]:
        """Scan for hardcoded secrets (keys, passwords, tokens, certs)."""
        self._require_ready()
        # First extract strings
        string_results = await self.strings(binary_path, min_length=6)
        secrets = []
        for s in string_results:
            text = s.get("string", "")
            for pattern, label in _SECRET_RE:
                if pattern.search(text):
                    secrets.append({
                        "offset": s.get("offset", 0),
                        "type": label,
                        "value": text[:200],  # Truncate long matches
                    })
                    break
        return secrets

    # ── File info ────────────────────────────────────────

    async def file_info(self, binary_path: str) -> dict:
        """Get file type information."""
        self._require_ready()
        result: dict[str, Any] = {"path": binary_path}
        if self._spm:
            stdout, _, rc = await self._spm.execute(["file", "-b", binary_path])
            if rc == 0:
                result["type"] = stdout.strip()
            stdout, _, rc = await self._spm.execute(["stat", "-c", "%s", binary_path])
            if rc == 0:
                result["size"] = int(stdout.strip())
        return result

    # ── Filesystem listing ───────────────────────────────

    async def list_extracted(self, output_dir: str | None = None) -> list[dict]:
        """List files in extraction output directory."""
        self._require_ready()
        target = output_dir or os.path.join(self._workspace, "extracted")
        return self._list_extracted(target)

    # ── Signatures list ──────────────────────────────────

    async def list_signatures(self) -> list[str]:
        """List all supported binwalk signatures."""
        self._require_ready()
        if self._use_v3_cli and self._spm:
            stdout, _, rc = await self._spm.execute(["binwalk", "-L"])
            if rc == 0:
                return [line.strip() for line in stdout.strip().split("\n") if line.strip()]
        return []

    # ── Internal parsing helpers ─────────────────────────

    def _parse_v3_analysis(self, data: list[dict]) -> list[dict]:
        """Parse v3 JSON Analysis results."""
        results = []
        for item in data:
            analysis = item.get("Analysis", {})
            for entry in analysis.get("file_map", []):
                results.append({
                    "offset": entry.get("offset", 0),
                    "size": entry.get("size", 0),
                    "name": entry.get("name", ""),
                    "description": entry.get("description", ""),
                    "confidence": entry.get("confidence", 0),
                })
        return results

    def _parse_v3_extractions(self, data: list[dict]) -> list[dict]:
        """Parse v3 JSON extraction results."""
        results = []
        for item in data:
            analysis = item.get("Analysis", {})
            for uid, ext in analysis.get("extractions", {}).items():
                results.append({
                    "id": uid,
                    "size": ext.get("size", 0),
                    "success": ext.get("success", False),
                    "extractor": ext.get("extractor", ""),
                    "output_dir": ext.get("output_directory", ""),
                })
        return results

    def _parse_v3_entropy(self, data: list[dict]) -> list[dict]:
        """Parse v3 JSON entropy blocks."""
        results = []
        for item in data:
            entropy_data = item.get("Entropy", {})
            for block in entropy_data.get("blocks", []):
                results.append({
                    "start": block.get("start", 0),
                    "end": block.get("end", 0),
                    "entropy": block.get("entropy", 0.0),
                })
        return results

    def _list_extracted(self, directory: str) -> list[dict]:
        """Recursively list files in directory."""
        result = []
        base = Path(directory)
        if not base.exists():
            return result
        for path in sorted(base.rglob("*")):
            if path.is_file():
                rel = str(path.relative_to(base))
                result.append({
                    "path": rel,
                    "size": path.stat().st_size,
                    "type": path.suffix or "unknown",
                })
        return result

    # ── Properties ───────────────────────────────────────

    @property
    def binwalk_version(self) -> str | None:
        return self._binwalk_version

    @property
    def workspace(self) -> str:
        return self._workspace


# Auto-register
bridge_registry.register("firmware", FirmwareBridge)
