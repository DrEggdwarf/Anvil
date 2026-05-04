"""Tests for the agent storage layer (SQLite) — ADR-023."""

from __future__ import annotations

import pytest

from backend.app.agent import storage as storage_mod
from backend.app.agent.models import ChatMessage, ToolCall


@pytest.fixture
def store(tmp_path):
    db = tmp_path / "agent.db"
    return storage_mod.AgentStorage(path=db)


def test_create_and_get_session(store):
    s = store.create_session(
        module="re", provider="anthropic", model="claude-3-5-sonnet-latest"
    )
    assert s.id and len(s.id) == 16
    fetched = store.get(s.id)
    assert fetched is not None
    assert fetched.module == "re"
    assert fetched.messages == []


def test_update_messages_persists_tool_calls(store):
    s = store.create_session(module="pwn", provider="openai", model="gpt-4o-mini")
    msgs = [
        ChatMessage(role="user", content="hello"),
        ChatMessage(
            role="assistant",
            content="calling",
            tool_calls=[
                ToolCall(
                    id="t1", name="rizin_open_binary", arguments={"binary_path": "/x"}
                )
            ],
        ),
        ChatMessage(role="tool", tool_call_id="t1", content='{"ok":true}'),
    ]
    store.update_messages(s.id, msgs, title="Hello")
    again = store.get(s.id)
    assert again.title == "Hello"
    assert len(again.messages) == 3
    assert again.messages[1].tool_calls[0].name == "rizin_open_binary"


def test_list_sessions_orders_by_last_used(store):
    a = store.create_session(module="re", provider="anthropic", model="m")
    b = store.create_session(module="pwn", provider="anthropic", model="m")
    # Touch a after b
    store.update_messages(a.id, [ChatMessage(role="user", content="ping")])
    listed = store.list_sessions(limit=10)
    ids = [s.id for s in listed]
    assert ids[0] == a.id
    assert b.id in ids


def test_delete_session(store):
    s = store.create_session(module="re", provider="anthropic", model="m")
    assert store.delete(s.id) is True
    assert store.get(s.id) is None
    assert store.delete(s.id) is False


def test_purge_all(store):
    store.create_session(module="re", provider="anthropic", model="m")
    store.create_session(module="pwn", provider="anthropic", model="m")
    assert store.purge_all() == 2
    assert store.list_sessions() == []


def test_derive_title():
    assert (
        storage_mod.derive_title("explique cette fonction") == "explique cette fonction"
    )
    long = "a" * 80
    out = storage_mod.derive_title(long)
    assert out.endswith("…")
    assert len(out) <= 62
    assert storage_mod.derive_title("") == "Nouvelle conversation"
