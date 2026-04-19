"""Tests for the Health & Tools API endpoints.

Tests hit actual API endpoints via httpx — validates the full data flow:
request → route → tool check → JSON response.
"""

import pytest


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, async_client):
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_detailed_returns_tools(self, async_client):
        resp = await async_client.get("/api/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "tools" in data
        tools = data["tools"]
        # Should have all 24 tools
        assert len(tools) >= 20
        # Each tool has expected shape
        for name, info in tools.items():
            assert "name" in info
            assert "available" in info
            assert isinstance(info["available"], bool)


class TestToolsEndpoints:
    @pytest.mark.asyncio
    async def test_list_all_tools(self, async_client):
        resp = await async_client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        # Should have categories
        categories = data["tools"]
        assert "compilation" in categories
        assert "debug" in categories
        assert "reverse_engineering" in categories

    @pytest.mark.asyncio
    async def test_tools_for_mode_asm(self, async_client):
        resp = await async_client.get("/api/tools/asm")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "asm"
        tool_names = [t["name"] for t in data["tools"]]
        assert "nasm" in tool_names
        assert "gdb" in tool_names

    @pytest.mark.asyncio
    async def test_tools_for_mode_re(self, async_client):
        resp = await async_client.get("/api/tools/re")
        assert resp.status_code == 200
        data = resp.json()
        tool_names = [t["name"] for t in data["tools"]]
        assert "rizin" in tool_names
        assert "rzpipe" in tool_names

    @pytest.mark.asyncio
    async def test_tools_for_mode_pwn(self, async_client):
        resp = await async_client.get("/api/tools/pwn")
        assert resp.status_code == 200
        data = resp.json()
        tool_names = [t["name"] for t in data["tools"]]
        assert "gcc" in tool_names
        assert "pwntools" in tool_names
        assert "gdb" in tool_names

    @pytest.mark.asyncio
    async def test_tools_for_mode_protocols(self, async_client):
        resp = await async_client.get("/api/tools/protocols")
        assert resp.status_code == 200
        data = resp.json()
        tool_names = [t["name"] for t in data["tools"]]
        assert "pymodbus" in tool_names
        assert "snap7" in tool_names
        assert "opcua" in tool_names

    @pytest.mark.asyncio
    async def test_tools_for_unknown_mode(self, async_client):
        resp = await async_client.get("/api/tools/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tools"] == []
