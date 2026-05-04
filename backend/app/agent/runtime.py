"""Agent runtime — chat orchestrator producing SSE chunks (ADR-023)."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from backend.app.agent import storage as storage_mod
from backend.app.agent import tools as tools_mod
from backend.app.agent.audit import record_tool_call
from backend.app.agent.config_store import load_settings
from backend.app.agent.models import (
    AgentChatRequest,
    AgentChunk,
    AgentSession,
    ChatMessage,
    ToolCall,
)
from backend.app.agent.providers import ProviderError, get_provider
from backend.app.core.exceptions import AnvilError

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT_FR = (
    "Tu es Anvil Agent, l'assistant in-app du toolkit Anvil (sécurité bas niveau : "
    "ASM, Pwn, Reverse Engineering, Firmware, Wire). Réponds en français par défaut. "
    "Tu peux appeler des tools pour analyser un binaire, lire des registres, désassembler, "
    "décompiler, etc. Privilégie une démarche pédagogique : explique ce que tu fais avant "
    "d'appeler un tool destructif. N'invente jamais une adresse ou un résultat — utilise un tool."
)
_SYSTEM_PROMPT_EN = (
    "You are Anvil Agent, the in-app assistant for the Anvil low-level security toolkit "
    "(ASM, Pwn, RE, Firmware, Wire). Reply in English by default. You may call tools to "
    "inspect binaries, read registers, disassemble, decompile, etc. Be pedagogical: "
    "explain before invoking destructive tools. Never invent addresses or results — call a tool."
)


def _system_prompt(language: str, module: str, chips: list[str]) -> str:
    base = _SYSTEM_PROMPT_FR if language == "fr" else _SYSTEM_PROMPT_EN
    ctx_line = f"Module actif : {module}. Chips contexte : {', '.join(chips) or 'aucun'}."
    return base + "\n\n" + ctx_line


def _build_anthropic_tools(modules: list[str], strict: bool) -> list[dict[str, Any]]:
    return tools_mod.to_anthropic_schema(tools_mod.tools_for_modules(modules, strict=strict))


def _build_openai_tools(modules: list[str], strict: bool) -> list[dict[str, Any]]:
    return tools_mod.to_openai_schema(tools_mod.tools_for_modules(modules, strict=strict))


def _chunk(type_: str, **data: Any) -> str:
    """Encode a chunk as an SSE 'data:' line."""
    payload = AgentChunk(type=type_, data=data).model_dump()  # type: ignore[arg-type]
    return f"data: {json.dumps(payload)}\n\n"


class Runtime:
    """One Runtime per request (cheap dataclass-ish coordinator)."""

    def __init__(self, *, session_manager: Any) -> None:
        self.session_manager = session_manager

    async def chat_stream(self, req: AgentChatRequest) -> AsyncIterator[str]:
        settings = load_settings()
        provider_name = settings.active_provider
        provider_conf = settings.providers.get(provider_name)
        if provider_conf is None or (not provider_conf.api_key and provider_name != "ollama"):
            yield _chunk(
                "error",
                code="PROVIDER_NOT_CONFIGURED",
                message=f"Configure {provider_name} dans Settings → Agent.",
            )
            return

        store = storage_mod.get_storage()
        session = self._load_or_create_session(
            store, req=req, provider=provider_name, model=provider_conf.default_model
        )
        yield _chunk("session", session_id=session.id)

        # System message (always replace head; cheap)
        sys_prompt = _system_prompt(settings.language, req.module, req.chips)
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=sys_prompt),
            *[m for m in session.messages if m.role != "system"],
            ChatMessage(role="user", content=req.message),
        ]
        # Persist user message immediately
        session.messages = [m for m in messages if m.role != "system"]
        title = session.title
        if len(session.messages) <= 1:
            title = storage_mod.derive_title(req.message)
        store.update_messages(session.id, session.messages, title=title)

        provider = get_provider(provider_name)
        allow_write = req.allow_write_exec if req.allow_write_exec is not None else settings.allow_write_exec
        modules = [req.module, *req.chips]
        tools_schema = (
            _build_anthropic_tools(modules, settings.strict_mode)
            if provider_name == "anthropic"
            else _build_openai_tools(modules, settings.strict_mode)
        )

        # Up to 5 tool-loop iterations to keep things bounded.
        for _iter in range(5):
            assistant_text = ""
            pending_calls: list[dict[str, Any]] = []
            try:
                async for ev in provider.stream(
                    messages=messages,
                    tools=tools_schema,
                    model=provider_conf.default_model or session.model,
                    config=provider_conf,
                    max_tokens=min(settings.token_cap, 4096),
                ):
                    if ev["type"] == "text":
                        assistant_text += ev["delta"]
                        yield _chunk("delta", text=ev["delta"])
                    elif ev["type"] == "tool_call":
                        pending_calls.append(ev)
                    elif ev["type"] == "stop":
                        break
            except ProviderError as exc:
                yield _chunk("error", code="PROVIDER_ERROR", message=str(exc))
                return

            # Build assistant turn (text + tool_calls)
            tool_calls = [
                ToolCall(
                    id=c["id"] or uuid.uuid4().hex,
                    name=c["name"],
                    arguments=c["arguments"],
                    destructive=_is_destructive(c["name"]),
                )
                for c in pending_calls
            ]
            assistant_msg = ChatMessage(role="assistant", content=assistant_text, tool_calls=tool_calls)
            messages.append(assistant_msg)
            session.messages.append(assistant_msg)

            if not tool_calls:
                store.update_messages(session.id, session.messages, title=title)
                yield _chunk("done", session_id=session.id)
                return

            # Execute tools (or pause for approval if destructive)
            for tc in tool_calls:
                if tc.destructive and not allow_write:
                    record_tool_call(
                        session_id=session.id,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                        result_size=0,
                        duration_ms=0,
                        approved=False,
                        error="rejected_by_safeguard",
                    )
                    blocked_msg = (
                        f"Outil {tc.name} bloqué : tools destructifs désactivés "
                        f"(toggle 🔓 dans le header pour autoriser)."
                    )
                    tool_result_msg = ChatMessage(role="tool", tool_call_id=tc.id, content=blocked_msg)
                    messages.append(tool_result_msg)
                    session.messages.append(tool_result_msg)
                    yield _chunk(
                        "tool_result",
                        id=tc.id,
                        name=tc.name,
                        error=blocked_msg,
                        blocked=True,
                    )
                    continue
                yield _chunk(
                    "tool_call",
                    id=tc.id,
                    name=tc.name,
                    arguments=tc.arguments,
                    destructive=tc.destructive,
                )
                try:
                    out = await tools_mod.dispatch(
                        tool_name=tc.name,
                        arguments=dict(tc.arguments),
                        anvil_session_ids=req.anvil_session_ids,
                        agent_session_id=session.id,
                        session_manager=self.session_manager,
                    )
                    tc.result = out["result"]
                    tc.duration_ms = out["duration_ms"]
                    yield _chunk(
                        "tool_result",
                        id=tc.id,
                        name=tc.name,
                        result=_truncate(tc.result),
                        duration_ms=tc.duration_ms,
                    )
                    tool_result_msg = ChatMessage(
                        role="tool",
                        tool_call_id=tc.id,
                        content=_serialize_tool_result(tc.result),
                    )
                    messages.append(tool_result_msg)
                    session.messages.append(tool_result_msg)
                except AnvilError as exc:
                    tc.error = exc.message
                    yield _chunk("tool_result", id=tc.id, name=tc.name, error=exc.message)
                    err_msg = ChatMessage(role="tool", tool_call_id=tc.id, content=f"ERROR: {exc.message}")
                    messages.append(err_msg)
                    session.messages.append(err_msg)

            store.update_messages(session.id, session.messages, title=title)
            # loop again so the model can continue with the tool results

        # Hit max iterations
        yield _chunk("error", code="MAX_TOOL_ITERATIONS", message="Limite d'itérations tool atteinte.")

    # ── Session helpers ──────────────────────────────────
    def _load_or_create_session(
        self, store: storage_mod.AgentStorage, *, req: AgentChatRequest, provider: str, model: str
    ) -> AgentSession:
        if req.session_id:
            existing = store.get(req.session_id)
            if existing:
                return existing
        return store.create_session(module=req.module, provider=provider, model=model)


# ── Helpers ──────────────────────────────────────────────
_DESTRUCTIVE_NAMES = {
    "gdb_run",
}


def _is_destructive(name: str) -> bool:
    spec = tools_mod.get_tool(name)
    if spec is not None:
        return spec.destructive
    return name in _DESTRUCTIVE_NAMES


def _truncate(value: Any, *, limit: int = 4000) -> Any:
    text = json.dumps(value, default=str)
    if len(text) <= limit:
        return value
    return {"_truncated": True, "preview": text[:limit]}


def _serialize_tool_result(value: Any) -> str:
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)
