---
applyTo: "src/**"
---

# Frontend conventions — Anvil

> Full architecture in [CLAUDE.md](../../CLAUDE.md). Component checklist in `/new-component` (`.github/prompts/new-component.prompt.md`).

## TypeScript conventions

- **Functional components only** — jamais de class components
- Props via `interface XxxProps` — toujours typer explicitement
- **No `any`** — utiliser `unknown` + type guard si nécessaire
- Pas de `as any` non justifié — `as UnknownType` uniquement pour les cas limites d'interop API

## Hard limits (ADR-018)

- File > 400 LOC → must be split before merge
- File > 500 LOC → **blocks merge**

## Module/mode system

5 modules: `asm | pwn | re | fw | hw` — set via `data-cat` attribute on root.
New mode = new entry in `data-cat`, new `--cat-<mode>` CSS token, new hook `useXxxSession`.

## Hook pattern (`useXxxSession`)

Each mode has one root session hook: `useAnvilSession` (ASM), `usePwnSession` (Pwn), etc.
Minimal contract: `{ sessionId, ensureSession(), destroySession(), log[], clearLog() }`.
Sub-concerns (parsing, memory, stepping) live in `hooks/<mode>/<domain>.ts`.

## WebSocket (ADR-016)

```ts
// token is returned ONCE at session create — keep in React state
const ws = new AnvilWS(`/ws/gdb/${sessionId}?token=${token}`)
```

Never store the token in localStorage or sessionStorage.

## API calls

All requests through `src/api/client.ts`:
```ts
const result = await request<MyResponseType>('POST', '/api/gdb/{sessionId}/action', body)
```

## CSS

- Classes prefixed `anvil-` (e.g. `anvil-register-pane`)
- Spacing: `var(--space-1)` … `var(--space-8)`
- Typography: `var(--font-code)`, `var(--font-ui)`
- Accent: `var(--accent)` adapts per `data-cat`
- Theme: `[data-theme="dark"]` / `[data-theme="light"]` on `document.documentElement`
- No CSS-in-JS, no Tailwind, no `transition: all`
