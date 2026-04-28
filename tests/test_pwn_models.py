"""Tests for backend.app.models.pwn — Pydantic validators.

Covers the custom validators on PwnUploadRequest, PwnRopSetRegsRequest,
PwnSropRequest, PwnFmtstrRequest. Audit (Sprint 14 fix #6) flagged these
as 0% covered before this sprint.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from backend.app.models.pwn import (
    PwnFmtstrRequest,
    PwnRopSetRegsRequest,
    PwnSropRequest,
    PwnUploadRequest,
)


class TestPwnUploadRequestValidator:
    def test_accepts_plain_filename(self):
        req = PwnUploadRequest(filename="exploit.elf", data_b64="SGVsbG8=")
        assert req.filename == "exploit.elf"

    def test_rejects_forward_slash(self):
        with pytest.raises(PydanticValidationError, match="path separators"):
            PwnUploadRequest(filename="../etc/passwd", data_b64="x")

    def test_rejects_backslash(self):
        with pytest.raises(PydanticValidationError, match="path separators"):
            PwnUploadRequest(filename="..\\windows", data_b64="x")

    def test_rejects_null_byte(self):
        with pytest.raises(PydanticValidationError, match="path separators"):
            PwnUploadRequest(filename="ok.bin\x00.txt", data_b64="x")

    def test_rejects_too_long_filename(self):
        with pytest.raises(PydanticValidationError):
            PwnUploadRequest(filename="a" * 256, data_b64="x")

    def test_rejects_oversized_payload(self):
        with pytest.raises(PydanticValidationError):
            PwnUploadRequest(filename="ok.bin", data_b64="A" * 104_857_601)


class TestPwnRopSetRegsValidator:
    def test_accepts_normal_registers(self):
        req = PwnRopSetRegsRequest(rop_id="r1", registers={"rdi": 1, "rsi": 2})
        assert req.registers == {"rdi": 1, "rsi": 2}

    def test_rejects_too_many_registers(self):
        regs = {f"r{i}": i for i in range(65)}
        with pytest.raises(PydanticValidationError, match="too many registers"):
            PwnRopSetRegsRequest(rop_id="r1", registers=regs)

    def test_accepts_exact_limit(self):
        regs = {f"r{i}": i for i in range(64)}
        req = PwnRopSetRegsRequest(rop_id="r1", registers=regs)
        assert len(req.registers) == 64


class TestPwnSropValidator:
    def test_rejects_too_many_registers(self):
        regs = {f"r{i}": i for i in range(65)}
        with pytest.raises(PydanticValidationError, match="too many registers"):
            PwnSropRequest(registers=regs)


class TestPwnFmtstrValidator:
    def test_accepts_normal_writes(self):
        req = PwnFmtstrRequest(offset=6, writes={"0x401234": 0xdeadbeef})
        assert req.writes == {"0x401234": 0xdeadbeef}

    def test_rejects_too_many_writes(self):
        writes = {f"0x{i:08x}": i for i in range(257)}
        with pytest.raises(PydanticValidationError, match="too many writes"):
            PwnFmtstrRequest(offset=6, writes=writes)

    def test_accepts_exact_limit(self):
        writes = {f"0x{i:08x}": i for i in range(256)}
        req = PwnFmtstrRequest(offset=6, writes=writes)
        assert len(req.writes) == 256
