---
applyTo: "backend/**,tests/**,anvil_mcp/**"
---

# Backend conventions — Anvil

> Full architecture in [CLAUDE.md](../../CLAUDE.md). Full ADR history in [ai/context/decisions.md](../../ai/context/decisions.md).

## Adding a route — use `/new-endpoint` prompt

`.github/prompts/new-endpoint.prompt.md` walks through the full checklist:
model → bridge method → API route → test.

## Python conventions

- `from __future__ import annotations` en première ligne de chaque fichier
- Imports : stdlib → third-party → local (ruff `I001`)
- Type hints sur **tout** : paramètres, valeurs de retour, attributs de classe
- Pydantic v2 : `Field(...)` obligatoire sur chaque champ de requête — `max_length` sur les `str`, `ge`/`le` sur les `int`, `max_length` sur les `list`

## Critical rules

- **`CompilationBridge` only** (ADR-017): all compilation (ASM/C/C++/Rust/Go) goes through `bridges/compilation.py`. Never spawn compilers directly in routes.
- **Binary data = hex strings** (ADR-010): encode all bytes as hex (`"9090"` for `\x90\x90`). Bridge converts hex↔bytes.
- **MCP dict rule** (ADR-022): any endpoint intended for MCP must return a structured `dict` with a `summary` field — never a raw string.
- **`pyproject.toml` is the only dep source** (ADR-019): don't create or edit `requirements*.txt`.
- **SubprocessManager only** (ADR-020): never call `os.system` or `subprocess.run` directly.

## Session lifecycle

```
POST /api/sessions {bridge_type}  → {session_id, token}
...use /api/{mode}/{session_id}/*...
DELETE /api/sessions/{session_id}
```

Token from session create is required for WS: `/ws/{type}/{session_id}?token=<token>`.

## Bridge checklist

1. Subclass `BaseBridge`, implement `start / stop / health / execute`
2. Call `self._require_ready()` at top of every action method
3. Sanitize all user input via `core/sanitization.py`
4. Register bridge: import it in `core/lifecycle.py`

## Test conventions

- Fixture `async_client` (httpx) for API tests, `mock_session_manager` for bridge tests
- All bridges mocked via `sys.modules` in `conftest.py` — CI has no GDB/rizin/pwntools
- No `@pytest.mark.asyncio` needed — `asyncio_mode = "auto"` in pyproject.toml
