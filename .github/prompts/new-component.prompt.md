---
description: "Add a new React component following Anvil conventions"
---
When creating a new frontend component in Anvil:

1. **File**: `src/components/{ComponentName}.tsx` (PascalCase)

2. **Structure**:
   ```tsx
   interface ComponentNameProps {
     // typed props
   }
   export default function ComponentName({ ...props }: ComponentNameProps) {
     return <div className="anvil-component-name">...</div>
   }
   ```

3. **CSS** — add styles to `src/App.css` or a co-located `.css` file:
   - All classes prefixed with `anvil-` (e.g., `anvil-memory-panel`)
   - Use design tokens: `var(--space-3)`, `var(--font-code)`, `var(--accent)`
   - Mode-aware: colors adapt via `var(--cat-asm)` etc.
   - Support both themes: `[data-theme="dark"]` / `[data-theme="light"]`

4. **API calls**: use `src/api/client.ts` — `request<T>('POST', '/api/...', body)`

5. **State**: lift to App.tsx or use a hook in `src/hooks/`

6. **No**: CSS-in-JS, Tailwind, class components, external state libraries
