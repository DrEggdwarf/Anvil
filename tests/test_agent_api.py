"""Tests for the agent API router (settings, sessions, audit)."""

from __future__ import annotations

import pytest

from backend.app.agent import audit as audit_mod
from backend.app.agent import config_store, storage as storage_mod


@pytest.fixture(autouse=True)
def _isolated_anvil_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config_store, "anvil_dir", lambda: tmp_path)
    monkeypatch.setattr(config_store, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(config_store, "db_path", lambda: tmp_path / "agent.db")
    monkeypatch.setattr(config_store, "audit_log_path", lambda: tmp_path / "agent.log")
    storage_mod.reset_storage_for_tests(tmp_path / "agent.db")
    yield
    storage_mod.reset_storage_for_tests(None)


@pytest.mark.asyncio
async def test_get_settings_returns_masked(async_client):
    resp = await async_client.get("/api/agent/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_provider"] in ("anthropic", "openai", "openrouter", "ollama")
    assert "providers" in body
    for conf in body["providers"].values():
        assert "api_key_masked" in conf


@pytest.mark.asyncio
async def test_update_settings_persists_keys(async_client):
    payload = {
        "active_provider": "openai",
        "providers": {
            "openai": {"api_key": "sk-test-1234567890", "default_model": "gpt-4o-mini"}
        },
        "strict_mode": True,
    }
    resp = await async_client.put("/api/agent/settings", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_provider"] == "openai"
    assert body["strict_mode"] is True
    assert body["providers"]["openai"]["has_key"] is True
    assert body["providers"]["openai"]["api_key_masked"].startswith("sk-tes")


@pytest.mark.asyncio
async def test_update_settings_empty_api_key_preserves_existing(async_client):
    await async_client.put(
        "/api/agent/settings",
        json={"providers": {"anthropic": {"api_key": "sk-ant-XXXXX-real"}}},
    )
    # Empty key should NOT clobber.
    await async_client.put(
        "/api/agent/settings",
        json={
            "providers": {
                "anthropic": {
                    "api_key": "",
                    "default_model": "claude-3-5-sonnet-latest",
                }
            }
        },
    )
    settings = config_store.load_settings()
    assert settings.providers["anthropic"].api_key == "sk-ant-XXXXX-real"


@pytest.mark.asyncio
async def test_list_providers(async_client):
    resp = await async_client.get("/api/agent/providers")
    assert resp.status_code == 200
    assert set(resp.json()["providers"]) == {
        "anthropic",
        "openai",
        "openrouter",
        "ollama",
    }


@pytest.mark.asyncio
async def test_sessions_crud(async_client):
    store = storage_mod.get_storage()
    s = store.create_session(module="re", provider="anthropic", model="m")
    listed = (await async_client.get("/api/agent/sessions")).json()
    assert any(item["id"] == s.id for item in listed["sessions"])

    detail = (await async_client.get(f"/api/agent/sessions/{s.id}")).json()
    assert detail["id"] == s.id

    deleted = (await async_client.delete(f"/api/agent/sessions/{s.id}")).json()
    assert deleted == {"deleted": True}

    missing = await async_client.get(f"/api/agent/sessions/{s.id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_purge_sessions(async_client):
    store = storage_mod.get_storage()
    store.create_session(module="re", provider="anthropic", model="m")
    store.create_session(module="pwn", provider="anthropic", model="m")
    resp = await async_client.delete("/api/agent/sessions")
    assert resp.status_code == 200
    assert resp.json()["deleted"] >= 2


@pytest.mark.asyncio
async def test_audit_log_endpoint(async_client):
    audit_mod.record_tool_call(
        session_id="abc",
        tool_name="rizin_functions",
        arguments={"x": 1},
        result_size=42,
        duration_ms=10,
    )
    resp = await async_client.get("/api/agent/audit?limit=10")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert any(e["tool"] == "rizin_functions" for e in entries)


@pytest.mark.asyncio
async def test_chat_without_provider_emits_error(async_client):
    # No keys configured → SSE error chunk
    resp = await async_client.post(
        "/api/agent/chat",
        json={"message": "hi", "module": "re"},
    )
    assert resp.status_code == 200
    text = resp.text
    assert "PROVIDER_NOT_CONFIGURED" in text
