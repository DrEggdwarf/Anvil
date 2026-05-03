---
description: "Add a new React component following Anvil conventions"
---
When creating a new frontend component in Anvil:

1. **File**: `src/components/{ComponentName}.tsx` (PascalCase)
   - Test file: `src/components/__tests__/{ComponentName}.test.tsx`
   - **LOC limit (ADR-018)**: > 400 L → split; > 500 L → blocks merge

2. **Structure** — functional components only, no `any`:
   ```tsx
   interface ComponentNameProps {
     // typed props — no `any`
   }
   export default function ComponentName({ ...props }: ComponentNameProps) {
     return <div className="anvil-component-name">...</div>
   }
   ```

3. **CSS** — add styles to `src/App.css` or a co-located `.css` file:
   - All classes prefixed with `anvil-` (e.g., `anvil-memory-panel`)
   - Spacing: `var(--space-1)` … `var(--space-8)`
   - Typography: `var(--font-code)`, `var(--font-ui)`
   - Accent/mode: `var(--accent)` adapts per `data-cat` (asm|pwn|re|fw|hw)
   - Support both themes: `[data-theme="dark"]` / `[data-theme="light"]`
   - **Forbidden**: CSS-in-JS (emotion, styled-components), Tailwind, `transition: all`

4. **Mode detection** (if the component is mode-aware):
   ```ts
   const mode = document.documentElement.getAttribute('data-cat') // 'asm'|'pwn'|'re'|'fw'|'hw'
   ```
   New mode = new `--cat-<mode>` token + new `useXxxSession` hook.

5. **API calls**: use `src/api/client.ts` — `request<T>('POST', '/api/...', body)`

6. **State**: lift to App.tsx or use a `useXxxSession` hook in `src/hooks/`
   Minimal hook contract: `{ sessionId, ensureSession(), destroySession(), log[], clearLog() }`

7. **Forbidden**: CSS-in-JS, Tailwind, class components, Redux/Zustand, `any` TypeScript
