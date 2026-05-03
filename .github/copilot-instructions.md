# Copilot workspace instructions — Anvil

## Response format

Every non-trivial response must follow the sprint format used in [ai/context/sprint_log.md](../ai/context/sprint_log.md):

```
## Sprint N — <Title> (<date>)
**Objectif** : one-line description
**Agents** : @backend, @security (agents from .github/agents/)

### A — <Sub-task name>
- [x] done item
- [ ] todo item

### Décisions techniques
- <key decision> — why

### Prochaines étapes
- Sprint N+1 : ...
```

Apply this structure for:
- Any implementation task (features, fixes, refactors)
- Any audit or review response
- Any architecture/design question

For simple factual questions (single-file lookup, syntax question), a direct answer without sprint format is fine.

## Multi-subagent usage

Use subagents **systematically** for:

| Situation | Action |
|-----------|--------|
| Codebase exploration (finding files, understanding structure) | Spawn `Explore` subagent |
| Task spans backend + frontend | Run both investigations in parallel with subagents |
| Security audit, performance audit, architecture review | Spawn specialized subagent per domain |
| Finding where a pattern is used across the codebase | Spawn `Explore` rather than chaining grep calls |

Never chain more than 2 sequential searches before delegating to a subagent.

## Agent roles

When listing agents in sprint headers, map to [.github/agents/](agents/):
- `@architect` — cross-cutting decisions, ADRs
- `@backend` — FastAPI, bridges, sessions, tests
- `@frontend` — React, hooks, CSS, Vite
- `@security` — sanitization, OWASP, injection (static review)
- `@pentester` — exploitation analysis, bridge edge cases (runtime)
- `@testing` — pytest, vitest, playwright coverage
- `@devops` — CI, Docker, packaging
- `@performance` — bundle size, subprocess, LRU
- `@quality` — LOC limits, dead code, conventions
- `@rust` — Tauri IPC, Cargo, packaging
- `@mcp` — MCP server, tool contracts, ADR-022
- `@pm` — backlog, sprint planning, feature spec
- `@a11y` — WCAG, ARIA, keyboard navigation

## ADR references

Before any architecture decision, check [ai/context/decisions.md](../ai/context/decisions.md).
When making a decision that isn't covered by existing ADRs, propose a new ADR inline in the response.
