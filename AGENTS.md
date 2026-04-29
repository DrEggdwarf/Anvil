# Anvil — Agent Instructions

Low-level security toolkit: ASM, Pwn, Reverse Engineering, Firmware, Wire (ICS/OT).
Desktop app (Tauri v2) with React frontend and FastAPI backend wrapping tool bridges.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `make check` | Run all CI gates locally (lint + tests + audits) — do this before push |
| `npm run dev` | Frontend dev server (port 1420) |
| `npm run tauri dev` | Full desktop dev (Tauri + frontend + backend) |
| `uvicorn backend.app.main:app --reload --port 8000` | Backend standalone (run from repo root) |
| `python -m pytest tests/ -v` | Run all ~736 Python tests |
| `python -m pytest tests/test_gdb_bridge.py -k "test_load"` | Single test |
| `npx vitest` | Frontend unit/component tests (27) |
| `npx playwright test` | E2E tests (31 specs) |
| `ruff check backend/ tests/ anvil_mcp/` | Python lint |
| `bandit -r backend/ -c backend/pyproject.toml` | Security scan |

pytest asyncio_mode is `"auto"` in `backend/pyproject.toml` — no `@pytest.mark.asyncio` needed.

## Architecture

See [CLAUDE.md](CLAUDE.md) for full architecture details, bridge pattern, security layers, and error hierarchy.

```
src-tauri/src/     Rust shell (thin — no business logic, just IPC + subprocess spawn)
src/               React 19 + TypeScript 5 — 5-module UI: ASM (3-col debug), Pwn (split editors+terminal)
backend/app/       FastAPI — main.py → 9 routers, core/, bridges/, models/, sessions/
anvil_mcp/         MCP server skeleton — tools/resources/prompts (stubs, wired per-sprint)
tests/             pytest modules — all use MockBridge (no real tools needed)
```

### Key patterns

- **Sessions**: every API call scoped to a `session_id` (16 hex chars). Session owns one bridge + workspace dir.
- **Bridges**: subclass `BaseBridge`, implement `start/stop/health/execute`, register via `bridge_registry`.
- **WebSocket**: single endpoint `/ws/{session_type}/{session_id}`, typed `WSMessage`, handlers registered by command name.
- **Frontend state**: `useAnvilSession()` hook manages GDB lifecycle; `usePwnSession()` manages Pwn mode; mode system via `data-cat` attribute.
- **Pwn pipeline**: drop source file → auto-compile backend → load ELF → checksec/symbols/GOT/PLT → side-by-side editors (SourceViewer + PwnEditor) + bottom panel (Terminal/data tabs).
- **MCP rule**: every bridge method exposed via MCP must return a structured `dict` (not raw `str`). See ADR-022.

## Conventions

### Python (backend)
- Type hints on everything, Pydantic v2 `Field(...)` with `max_length`/`ge`/`le` on **all** request fields
- Input sanitization mandatory in bridges (`core/sanitization.py`)
- Tests use `MockBridge` from `conftest.py` — never depend on real tools (gdb, rizin, etc.)
- `from __future__ import annotations` in every file
- Imports: stdlib → third-party → local (ruff I001)

### React / TypeScript (frontend)
- Functional components only, props via `interface XxxProps`
- Pure CSS with `anvil-` prefix — no CSS-in-JS, no Tailwind
- Design tokens via CSS custom properties (`--space-*`, `--cat-*`, `--font-*`)
- Theme: `data-theme="dark|light"` on root, mode accent via `data-cat="asm|re|pwn|dbg|fw|hw"`
- API calls through `src/api/client.ts` — single typed `request<T>()` wrapper

### Rust (src-tauri)
- Shell only — no business logic. Only IPC commands: `check_backend`, `check_dependencies`

## Backend dependencies

```bash
pip install -e backend/          # core only
pip install -e "backend/[dev]"   # + test/lint (pytest, ruff, bandit)
pip install -e "backend/[mcp]"   # + MCP server (mcp SDK + httpx)
```

Optional groups: `re` (rzpipe), `pwn` (pwntools), `firmware` (binwalk), `protocols` (pymodbus), `mcp`.

## CI

5 jobs GitHub Actions on push/PR to main — run `make check` locally to mirror them.

| Job | Gates | Blocking |
|-----|-------|----------|
| `lint` | ruff check+format+bandit on backend/tests/anvil_mcp | yes |
| `test` | pytest ~736 + vitest 27 | yes |
| `smoke` | live backend + 5 ADR-016 checks | yes |
| `audit` | pip-audit + npm audit + cargo audit | no (continue-on-error) |
| `e2e` | Playwright 31 specs | no (continue-on-error) |
