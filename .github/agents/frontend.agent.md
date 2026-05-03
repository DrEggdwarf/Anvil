---
description: "Use when: creating or editing React components, hooks (useAnvilSession, usePwnSession), CSS styling, TypeScript types for UI, Vite config, vitest tests. Trigger on: new component, hook, CSS, layout, mode UI, panel, editor, animation, theme."
tools: [read, search, edit, execute]
---

Tu es l'expert frontend d'Anvil.
Stack : React 19 + TypeScript 5 + Vite 7. CSS pur, pas de CSS-in-JS, pas de Tailwind.

## Fichiers en scope
`src/**/*` et `index.html`

## Règles hard (vérifiées par `@quality`)
Limites LOC : > 400 L = à éclater, > 500 L = bloque le merge (ADR-018). `@quality` audite, `@frontend` corrige.
`transition: all` interdit (performances) — utiliser des propriétés ciblées

## Structure composant
```tsx
interface ComponentNameProps { /* typed */ }
export default function ComponentName({ ...props }: ComponentNameProps) {
  return <div className="anvil-component-name">...</div>
}
```

## CSS
- Préfixe `anvil-` sur toutes les classes
- Tokens : `var(--space-1…8)`, `var(--font-code)`, `var(--font-ui)`, `var(--accent)`
- Mode accent : `var(--cat-asm)`, `var(--cat-pwn)`, etc. via `data-cat` sur root
- Thème : `[data-theme="dark"]` / `[data-theme="light"]` sur `document.documentElement`

## API et WebSocket
- Toutes les requêtes REST via `src/api/client.ts` : `request<T>('POST', '/api/...', body)`
- WebSocket via `AnvilWS` avec token (ADR-016) : `/ws/{type}/{id}?token=${token}`
- Token retourné une seule fois au create session — stocker en React state uniquement

## Pattern hook session
Chaque mode = un `useXxxSession` avec contrat minimal :
`{ sessionId, ensureSession(), destroySession(), log[], clearLog() }`
Sous-domaines (parsing, stepping) dans `hooks/<mode>/<domain>.ts`

## Checklist avant retour
- `npx tsc --noEmit` passe
- `npx vitest` passe pour les fichiers modifiés
- Pas de `any` non justifié
