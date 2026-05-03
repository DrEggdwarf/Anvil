---
description: "Add a new backend API route with model, bridge method, and test"
---
When adding a new backend endpoint to Anvil, follow this checklist:

1. **Model** (`backend/app/models/{module}.py`):
   - `from __future__ import annotations` en première ligne
   - Imports : stdlib → third-party → local (ruff I001)
   - Add Pydantic v2 `BaseModel` request/response classes
   - Every `str` field must have `Field(..., max_length=N)`
   - Every `int` field must have `Field(..., ge=X, le=Y)`
   - Every `list` field must have `Field(..., max_length=N)`
   - Import `Field` from pydantic

2. **Bridge method** (`backend/app/bridges/{module}_bridge.py`):
   - Add method to the bridge class
   - Call `self._require_ready()` first
   - Sanitize all user inputs via `core/sanitization.py` helpers
   - **Binary data (ADR-010)**: exchange as hex strings (`"9090"` for `\x90\x90`) — bridge converts hex↔bytes
   - **MCP rule (ADR-022)**: if endpoint will be exposed via MCP, return `dict` with `summary` field
   - Return plain dicts/lists (Pydantic serializes in the route)

3. **API route** (`backend/app/api/{module}.py`):
   - Add route with `@router.post("/{session_id}/action", response_model=ResponseModel)`
   - First param: `session_id: str`, second: `body: RequestModel`
   - Use `Depends(get_session_manager)` for session access
   - Get bridge via `_get_{module}_bridge(session_id, sm)`
   - Keep route body to 2-4 lines max

4. **Test** (`tests/test_{module}_api.py` or `tests/test_{module}_bridge.py`):
   - Use `MockBridge` from conftest — never real tools
   - Test happy path + error cases
   - For API tests: use `async_client` fixture with `httpx.AsyncClient`

5. **Verify**:
   - `ruff check backend/ tests/` (must pass — run from repo root)
   - `python -m pytest tests/ -v --tb=short` (use `python -m`, not `pytest` directly — fixes import paths)
