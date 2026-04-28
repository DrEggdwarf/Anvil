"""Tests for Firmware Bridge — firmware analysis via binwalk.

All tests mock binwalk + subprocess — no real binwalk needed.
Validates: lifecycle, scan, filtered scans, extraction, entropy,
strings, opcodes, raw search, secrets, file info, signatures.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from backend.app.bridges.base import BridgeState
from backend.app.bridges.firmware_bridge import FirmwareBridge
from backend.app.core.exceptions import BridgeCrash, BridgeNotReady


# ── Mock helpers ─────────────────────────────────────────


def make_mock_spm(stdout: str = "", stderr: str = "", rc: int = 0):
    """Create a mock SubprocessManager."""
    spm = MagicMock()
    spm.execute = AsyncMock(return_value=(stdout, stderr, rc))
    return spm


@pytest_asyncio.fixture
async def fw():
    """Firmware bridge with mocked binwalk v3 CLI."""
    bridge = FirmwareBridge(workspace_dir="/tmp/anvil_fw_test")
    bridge._use_v3_cli = True
    bridge._use_v2_python = False
    bridge._binwalk_version = "3.x"
    bridge._spm = make_mock_spm()
    bridge.state = BridgeState.READY
    yield bridge
    bridge.state = BridgeState.STOPPED


@pytest_asyncio.fixture
async def fw_v2():
    """Firmware bridge with mocked binwalk v2 Python."""
    bridge = FirmwareBridge(workspace_dir="/tmp/anvil_fw_test")
    bridge._use_v3_cli = False
    bridge._use_v2_python = True
    bridge._binwalk_version = "2.x"
    bridge._spm = make_mock_spm()
    bridge.state = BridgeState.READY
    yield bridge
    bridge.state = BridgeState.STOPPED


# ── Lifecycle ────────────────────────────────────────────


class TestFirmwareLifecycle:
    @pytest.mark.asyncio
    async def test_start_with_v3_cli(self):
        bridge = FirmwareBridge()
        spm = make_mock_spm(stdout="--log  Enable JSON output")
        await bridge.start(subprocess_manager=spm)
        assert bridge.state == BridgeState.READY
        assert bridge._use_v3_cli is True

    @pytest.mark.asyncio
    async def test_start_with_v2_python(self):
        bridge = FirmwareBridge()
        spm = make_mock_spm(stdout="Usage: binwalk [OPTIONS]")
        mock_binwalk = MagicMock()
        mock_binwalk.__version__ = "2.3.3"
        with patch.dict("sys.modules", {"binwalk": mock_binwalk}):
            await bridge.start(subprocess_manager=spm)
        assert bridge.state == BridgeState.READY

    @pytest.mark.asyncio
    async def test_start_no_binwalk(self):
        bridge = FirmwareBridge()
        spm = make_mock_spm(rc=1)
        # Also make Python import fail
        with patch.dict("sys.modules", {"binwalk": None}):
            with patch("builtins.__import__", side_effect=ImportError("no binwalk")):
                with pytest.raises(BridgeCrash):
                    await bridge.start(subprocess_manager=spm)
        assert bridge.state == BridgeState.ERROR

    @pytest.mark.asyncio
    async def test_stop(self, fw: FirmwareBridge):
        await fw.stop()
        assert fw.state == BridgeState.STOPPED
        assert fw._spm is None

    @pytest.mark.asyncio
    async def test_health_v3(self, fw: FirmwareBridge):
        assert await fw.health() is True

    @pytest.mark.asyncio
    async def test_health_v2(self, fw_v2: FirmwareBridge):
        assert await fw_v2.health() is True

    @pytest.mark.asyncio
    async def test_health_no_binwalk(self):
        bridge = FirmwareBridge()
        assert await bridge.health() is False

    @pytest.mark.asyncio
    async def test_execute_dispatches(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("[]", "", 0))
        result = await fw.execute("scan", binary_path="/tmp/test.bin")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_unknown(self, fw: FirmwareBridge):
        with pytest.raises(ValueError, match="Unknown command"):
            await fw.execute("nonexistent")


# ── Scan ─────────────────────────────────────────────────

V3_SCAN_RESULT = json.dumps([{
    "Analysis": {
        "file_map": [
            {"offset": 0, "size": 1024, "name": "gzip", "description": "gzip compressed data", "confidence": 95},
            {"offset": 2048, "size": 512, "name": "squashfs", "description": "SquashFS filesystem", "confidence": 90},
        ]
    }
}])


class TestFirmwareScan:
    @pytest.mark.asyncio
    async def test_scan_v3(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(V3_SCAN_RESULT, "", 0))
        results = await fw.scan("/tmp/firmware.bin")
        assert len(results) == 2
        assert results[0]["name"] == "gzip"
        assert results[0]["offset"] == 0

    @pytest.mark.asyncio
    async def test_scan_v3_empty(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("[]", "", 0))
        results = await fw.scan("/tmp/firmware.bin")
        assert results == []

    @pytest.mark.asyncio
    async def test_scan_v3_error(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("", "error", 1))
        results = await fw.scan("/tmp/firmware.bin")
        assert results == []

    @pytest.mark.asyncio
    async def test_scan_v3_bad_json(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("not json", "", 0))
        results = await fw.scan("/tmp/firmware.bin")
        assert results == []

    @pytest.mark.asyncio
    async def test_scan_v2(self, fw_v2: FirmwareBridge):
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.offset = 0
        mock_result.description = "gzip compressed data"
        mock_result.module = "Signature"
        mock_module.results = [mock_result]
        mock_binwalk = MagicMock()
        mock_binwalk.scan.return_value = [mock_module]
        with patch.dict("sys.modules", {"binwalk": mock_binwalk}):
            results = await fw_v2.scan("/tmp/firmware.bin")
        assert len(results) == 1


# ── Filtered scans ───────────────────────────────────────


class TestFirmwareFilteredScan:
    @pytest.mark.asyncio
    async def test_scan_filtered_include(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(V3_SCAN_RESULT, "", 0))
        results = await fw.scan_filtered("/tmp/test.bin", include=["gzip", "lzma"])
        assert len(results) == 2
        # Verify -y flag was passed
        call_args = fw._spm.execute.call_args[0][0]
        assert "-y" in call_args

    @pytest.mark.asyncio
    async def test_scan_filtered_exclude(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("[]", "", 0))
        await fw.scan_filtered("/tmp/test.bin", exclude=["jpeg"])
        call_args = fw._spm.execute.call_args[0][0]
        assert "-x" in call_args

    @pytest.mark.asyncio
    async def test_scan_crypto(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("[]", "", 0))
        await fw.scan_crypto("/tmp/test.bin")
        call_args = fw._spm.execute.call_args[0][0]
        assert "-y" in call_args

    @pytest.mark.asyncio
    async def test_scan_filesystems(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("[]", "", 0))
        await fw.scan_filesystems("/tmp/test.bin")
        call_args = fw._spm.execute.call_args[0][0]
        assert "-y" in call_args

    @pytest.mark.asyncio
    async def test_scan_compression(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("[]", "", 0))
        await fw.scan_compression("/tmp/test.bin")
        call_args = fw._spm.execute.call_args[0][0]
        assert "-y" in call_args


# ── Extraction ───────────────────────────────────────────

V3_EXTRACT_RESULT = json.dumps([{
    "Analysis": {
        "file_map": [
            {"offset": 0, "size": 1024, "name": "gzip", "description": "gzip data", "confidence": 95},
        ],
        "extractions": {
            "uuid1": {"size": 1024, "success": True, "extractor": "gzip", "output_directory": "/tmp/out"}
        }
    }
}])


class TestFirmwareExtraction:
    @pytest.mark.asyncio
    async def test_extract_v3(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(V3_EXTRACT_RESULT, "", 0))
        with patch("os.makedirs"):
            result = await fw.extract("/tmp/firmware.bin", "/tmp/out")
        assert result["output_dir"] == "/tmp/out"
        assert len(result["results"]) == 1
        assert len(result["extractions"]) == 1
        assert result["extractions"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_extract_recursive_v3(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(V3_EXTRACT_RESULT, "", 0))
        with patch("os.makedirs"):
            result = await fw.extract_recursive("/tmp/firmware.bin")
        assert "output_dir" in result
        # Check -Me flag
        call_args = fw._spm.execute.call_args[0][0]
        assert "-Me" in call_args

    @pytest.mark.asyncio
    async def test_carve_v3(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(V3_EXTRACT_RESULT, "", 0))
        with patch("os.makedirs"):
            await fw.carve("/tmp/firmware.bin")
        call_args = fw._spm.execute.call_args[0][0]
        assert "--carve" in call_args

    @pytest.mark.asyncio
    async def test_extract_v2(self, fw_v2: FirmwareBridge):
        mock_module = MagicMock()
        mock_module.results = []
        mock_binwalk = MagicMock()
        mock_binwalk.scan.return_value = [mock_module]
        with patch.dict("sys.modules", {"binwalk": mock_binwalk}):
            with patch("os.makedirs"):
                with patch.object(fw_v2, "_list_extracted", return_value=[]):
                    result = await fw_v2.extract("/tmp/firmware.bin")
        assert "output_dir" in result


# ── Entropy ──────────────────────────────────────────────

V3_ENTROPY_RESULT = json.dumps([{
    "Entropy": {
        "blocks": [
            {"start": 0, "end": 1024, "entropy": 7.95},
            {"start": 1024, "end": 2048, "entropy": 3.2},
        ]
    }
}])


class TestFirmwareEntropy:
    @pytest.mark.asyncio
    async def test_entropy_v3(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(V3_ENTROPY_RESULT, "", 0))
        results = await fw.entropy("/tmp/firmware.bin")
        assert len(results) == 2
        assert results[0]["entropy"] == 7.95
        assert results[1]["start"] == 1024

    @pytest.mark.asyncio
    async def test_entropy_graph_v3(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("", "", 0))
        result = await fw.entropy_graph("/tmp/firmware.bin")
        assert result.endswith(".png")
        # Check --png flag
        call_args = fw._spm.execute.call_args[0][0]
        assert any("--png=" in arg for arg in call_args)


# ── Strings ──────────────────────────────────────────────


class TestFirmwareStrings:
    @pytest.mark.asyncio
    async def test_strings(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(
            "     a0 Hello World\n    1f0 firmware v1.0\n",
            "", 0
        ))
        results = await fw.strings("/tmp/firmware.bin")
        assert len(results) == 2
        assert results[0]["offset"] == 0xa0
        assert results[0]["string"] == "Hello World"

    @pytest.mark.asyncio
    async def test_strings_min_length(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("", "", 0))
        await fw.strings("/tmp/firmware.bin", min_length=8)
        call_args = fw._spm.execute.call_args[0][0]
        assert "-n8" in call_args

    @pytest.mark.asyncio
    async def test_strings_empty(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("", "", 0))
        results = await fw.strings("/tmp/firmware.bin")
        assert results == []


# ── Opcodes ──────────────────────────────────────────────


class TestFirmwareOpcodes:
    @pytest.mark.asyncio
    async def test_opcodes_v3_fallback(self, fw: FirmwareBridge):
        """v3 doesn't have opcode scan — falls back to file command."""
        fw._use_v2_python = False
        fw._spm.execute = AsyncMock(return_value=("ELF 64-bit LSB executable, x86-64", "", 0))
        results = await fw.opcodes("/tmp/firmware.bin")
        assert len(results) == 1
        assert "x86-64" in results[0]["description"]

    @pytest.mark.asyncio
    async def test_opcodes_v2(self, fw_v2: FirmwareBridge):
        mock_module = MagicMock()
        mock_result = MagicMock()
        mock_result.offset = 0
        mock_result.description = "ARM instructions"
        mock_result.module = "Opcodes"
        mock_module.results = [mock_result]
        mock_binwalk = MagicMock()
        mock_binwalk.scan.return_value = [mock_module]
        with patch.dict("sys.modules", {"binwalk": mock_binwalk}):
            results = await fw_v2.opcodes("/tmp/firmware.bin")
        assert len(results) == 1


# ── Raw search ───────────────────────────────────────────


class TestFirmwareRawSearch:
    @pytest.mark.asyncio
    async def test_search_raw(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("100:match\n200:match\n", "", 0))
        results = await fw.search_raw("/tmp/firmware.bin", "deadbeef")
        assert len(results) == 2
        assert results[0]["offset"] == 100
        assert results[1]["offset"] == 200

    @pytest.mark.asyncio
    async def test_search_raw_no_match(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("", "", 1))
        results = await fw.search_raw("/tmp/firmware.bin", "ffff")
        assert results == []


# ── Secrets ──────────────────────────────────────────────


class TestFirmwareSecrets:
    @pytest.mark.asyncio
    async def test_scan_secrets_finds_private_key(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(
            "    100 -----BEGIN RSA PRIVATE KEY-----\n",
            "", 0
        ))
        results = await fw.scan_secrets("/tmp/firmware.bin")
        assert len(results) == 1
        assert results[0]["type"] == "private_key"

    @pytest.mark.asyncio
    async def test_scan_secrets_finds_password(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(
            "    200 password=admin123\n",
            "", 0
        ))
        results = await fw.scan_secrets("/tmp/firmware.bin")
        assert len(results) == 1
        assert results[0]["type"] == "password"

    @pytest.mark.asyncio
    async def test_scan_secrets_finds_apikey(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(
            "    300 api_key=sk_live_abc123def456\n",
            "", 0
        ))
        results = await fw.scan_secrets("/tmp/firmware.bin")
        assert len(results) == 1
        assert results[0]["type"] == "api_key"

    @pytest.mark.asyncio
    async def test_scan_secrets_none_found(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(
            "    100 normal text string\n",
            "", 0
        ))
        results = await fw.scan_secrets("/tmp/firmware.bin")
        assert results == []


# ── File info ────────────────────────────────────────────


class TestFirmwareFileInfo:
    @pytest.mark.asyncio
    async def test_file_info(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(side_effect=[
            ("data", "", 0),
            ("1048576", "", 0),
        ])
        result = await fw.file_info("/tmp/firmware.bin")
        assert result["path"] == "/tmp/firmware.bin"
        assert result["type"] == "data"
        assert result["size"] == 1048576


# ── List extracted ───────────────────────────────────────


class TestFirmwareListExtracted:
    @pytest.mark.asyncio
    async def test_list_extracted_empty(self, fw: FirmwareBridge):
        with patch.object(Path, "exists", return_value=False):
            result = await fw.list_extracted("/tmp/nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_extracted(self, fw: FirmwareBridge, tmp_path: Path):
        # Create test files
        (tmp_path / "file1.bin").write_bytes(b"\x00" * 100)
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("hello")
        result = await fw.list_extracted(str(tmp_path))
        assert len(result) == 2
        paths = [r["path"] for r in result]
        assert "file1.bin" in paths
        assert str(Path("sub/file2.txt")) in paths


# ── Signatures list ──────────────────────────────────────


class TestFirmwareSignatures:
    @pytest.mark.asyncio
    async def test_list_signatures(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=(
            "gzip\nlzma\nsquashfs\ncramfs\n",
            "", 0
        ))
        result = await fw.list_signatures()
        assert len(result) == 4
        assert "gzip" in result

    @pytest.mark.asyncio
    async def test_list_signatures_empty(self, fw: FirmwareBridge):
        fw._spm.execute = AsyncMock(return_value=("", "", 1))
        result = await fw.list_signatures()
        assert result == []


# ── Properties ───────────────────────────────────────────


class TestFirmwareProperties:
    def test_binwalk_version(self, fw: FirmwareBridge):
        assert fw.binwalk_version == "3.x"

    def test_workspace(self, fw: FirmwareBridge):
        assert fw.workspace == "/tmp/anvil_fw_test"


# ── Parsing helpers ──────────────────────────────────────


class TestFirmwareParsing:
    def test_parse_v3_analysis(self, fw: FirmwareBridge):
        data = [{
            "Analysis": {
                "file_map": [
                    {"offset": 0, "size": 100, "name": "gzip", "description": "compressed", "confidence": 90}
                ]
            }
        }]
        result = fw._parse_v3_analysis(data)
        assert len(result) == 1
        assert result[0]["name"] == "gzip"

    def test_parse_v3_analysis_empty(self, fw: FirmwareBridge):
        assert fw._parse_v3_analysis([]) == []

    def test_parse_v3_extractions(self, fw: FirmwareBridge):
        data = [{
            "Analysis": {
                "extractions": {
                    "uid1": {"size": 1024, "success": True, "extractor": "gzip", "output_directory": "/tmp"}
                }
            }
        }]
        result = fw._parse_v3_extractions(data)
        assert len(result) == 1
        assert result[0]["success"] is True

    def test_parse_v3_entropy(self, fw: FirmwareBridge):
        data = [{
            "Entropy": {
                "blocks": [{"start": 0, "end": 1024, "entropy": 7.5}]
            }
        }]
        result = fw._parse_v3_entropy(data)
        assert len(result) == 1
        assert result[0]["entropy"] == 7.5

    def test_list_extracted_nonexistent(self, fw: FirmwareBridge):
        result = fw._list_extracted("/tmp/nonexistent_dir_xyz")
        assert result == []


# ── Not ready guard ──────────────────────────────────────


class TestFirmwareGuards:
    @pytest.mark.asyncio
    async def test_methods_fail_when_not_ready(self):
        bridge = FirmwareBridge()
        with pytest.raises(BridgeNotReady):
            await bridge.scan("/tmp/test")
        with pytest.raises(BridgeNotReady):
            await bridge.extract("/tmp/test")
        with pytest.raises(BridgeNotReady):
            await bridge.entropy("/tmp/test")
        with pytest.raises(BridgeNotReady):
            await bridge.strings("/tmp/test")
