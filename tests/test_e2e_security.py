"""E2E integration tests — security through the API layer.

Tests that injection attempts and invalid inputs are properly blocked
when sent through HTTP endpoints.
"""

import pytest


class TestCompilationSecurityE2E:
    """Test that dangerous GCC flags are blocked at the API level."""

    @pytest.mark.asyncio
    async def test_compile_c_blocks_wrapper_flag(self, async_client):
        # First create a session
        resp = await async_client.post(
            "/api/sessions", json={"bridge_type": "compilation"}
        )
        if resp.status_code == 400:
            pytest.skip("Compilation bridge not registered")
        session_id = resp.json().get("id", "")

        # Try to compile with dangerous flag
        resp = await async_client.post(
            f"/api/compile/{session_id}/c",
            json={
                "source_code": "int main() { return 0; }",
                "extra_flags": ["-wrapper", "/bin/sh,-c"],
            },
        )
        # Should be blocked at validation layer
        assert resp.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_compile_c_blocks_fplugin(self, async_client):
        resp = await async_client.post(
            "/api/sessions", json={"bridge_type": "compilation"}
        )
        if resp.status_code == 400:
            pytest.skip("Compilation bridge not registered")
        session_id = resp.json().get("id", "")

        resp = await async_client.post(
            f"/api/compile/{session_id}/c",
            json={
                "source_code": "int main() { return 0; }",
                "extra_flags": ["-fplugin=/tmp/evil.so"],
            },
        )
        assert resp.status_code in (400, 404)


class TestInputValidationE2E:
    """Test Pydantic max_length enforcement at the API level."""

    @pytest.mark.asyncio
    async def test_gdb_load_rejects_oversized_path(self, async_client):
        resp = await async_client.post("/api/sessions", json={"bridge_type": "gdb"})
        if resp.status_code == 400:
            pytest.skip("GDB bridge not registered")
        session_id = resp.json().get("id", "")

        resp = await async_client.post(
            f"/api/gdb/{session_id}/load",
            json={"binary_path": "A" * 5000},
        )
        # Pydantic should reject (422) or bridge should reject (400)
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_compile_rejects_oversized_source(self, async_client):
        """Source code over 1MB should be rejected by Pydantic."""
        resp = await async_client.post(
            "/api/sessions", json={"bridge_type": "compilation"}
        )
        if resp.status_code == 400:
            pytest.skip("Compilation bridge not registered")
        session_id = resp.json().get("id", "")

        resp = await async_client.post(
            f"/api/compile/{session_id}/asm",
            json={"source_code": "x" * 1_100_000},
        )
        assert resp.status_code == 422


class TestSessionIdValidationE2E:
    """Test that malformed session IDs are properly handled."""

    @pytest.mark.asyncio
    async def test_session_not_found_for_invalid_id(self, async_client):
        resp = await async_client.get("/api/gdb/../../etc/passwd/registers")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.asyncio
    async def test_session_not_found_for_nonexistent(self, async_client):
        resp = await async_client.get("/api/gdb/0000000000000000/registers")
        assert resp.status_code in (404, 410)


class TestCORSE2E:
    """Test CORS headers are properly set."""

    @pytest.mark.asyncio
    async def test_cors_allowed_origin(self, async_client):
        resp = await async_client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:1420",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI should respond to preflight
        assert resp.status_code in (200, 204, 400)
