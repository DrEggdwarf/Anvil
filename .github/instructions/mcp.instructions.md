---
applyTo: "anvil_mcp/**"
---

# MCP server conventions — Anvil

> Full MCP architecture in [CLAUDE.md](../../CLAUDE.md#mcp-server-anvil_mcp). ADR-022 in [ai/context/decisions.md](../../ai/context/decisions.md).

## Principe fondamental (ADR-022)

`anvil_mcp/` est un **client HTTP** du backend FastAPI. Aucune logique métier ici.

```
Claude Desktop/Cursor → anvil_mcp/server.py → http://127.0.0.1:8000 → FastAPI bridges
```

## Contrat de retour obligatoire

Tout tool MCP retourne un `dict` avec `summary` — jamais une `str` brute :

```python
# ✅
return {"summary": "3 functions found in binary", "functions": [...], "status": "ok"}

# ❌ Interdit
return "Analysis complete"
```

## Structure — où ajouter du code

| Fichier | Rôle |
|---------|------|
| `server.py` | Enregistre tools/resources/prompts via FastMCP |
| `client.py` | `httpx.AsyncClient` — seul point d'entrée HTTP |
| `tools/{domain}.py` | Un fichier par domaine (asm, pwn, re, firmware, wire, session) |
| `resources/session.py` | Resources `session://list`, `session://{id}/binary` |
| `prompts/pipelines.py` | Prompts orchestrés (`exploit_pipeline`, `firmware_audit`, `ctf_binary`) |

## Pattern d'ajout d'un tool

```python
@mcp.tool()
async def domain_action(session_id: str, param: str) -> dict:
    """One-line docstring for Claude (shown in tool picker)."""
    result = await client.post(f"/api/domain/{session_id}/action", json={"param": param})
    data = result.json()
    return {"summary": f"...", **data}
```

## Checklist

- `summary` présent dans le retour
- Docstring LLM-friendly (une phrase — s'affiche dans le tool picker Claude)
- Pas d'appels directs aux bridges — passer par `client.py`
- `ruff check anvil_mcp/` passe
