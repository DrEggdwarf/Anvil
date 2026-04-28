# Anvil — End-to-end test suite

Playwright suite that drives the **live frontend + live backend + real tools**.
Sister to the unit-level layers:

| Layer | Tool | Path | Purpose |
|-------|------|------|---------|
| 1. Pure functions | vitest | `src/**/*.test.ts` | Parsers, validators, helpers |
| 2. Components | vitest + RTL + jsdom | `src/components/__tests__/` | Render, props, state |
| 3. Backend | pytest | `tests/test_*.py` | Bridges with `MockBridge`, ~700 tests |
| 4. **Smoke** | bash + curl | `tests/e2e/smoke/backend.sh` | Live backend tripwire (5 checks, <5s) |
| 5. **E2E** | Playwright | `tests/e2e/{asm,pwn}/*.spec.ts` | Real user journeys |

## Run locally

```bash
# Smoke (no browser, requires backend running on :8000)
npm run smoke

# Full e2e suite — Playwright spawns backend + frontend automatically
npm run e2e

# UI mode for picking specs and inspecting the trace viewer
npm run e2e:ui

# Headful debug mode — pauses on failure with the dev-tools panel
npm run e2e:debug
```

## Required tools on the host

E2E specs run against real binaries, so the host needs the tools you would use
in production:

- `nasm` (always required — ASM happy path)
- `gdb` (always required — stepping)
- `ld` (always required — linking)
- `gcc` (set `E2E_HAS_GCC=1` to enable C compile specs)
- `as` (set `E2E_HAS_GAS=1` to enable GAS specs)
- `fasm` (optional, FASM specs gracefully skip when absent)

Sample binaries live in `samples/pwn/`. Build them once with:

```bash
make -C samples/pwn
```

Specs that need a binary call `test.skip(!bin, …)` so the suite stays green even
when samples aren't built.

## Layout

```
tests/e2e/
  fixtures/
    anvil.ts        — Page wrapper (selectors + workflow helpers) + reset hook
    samples.ts      — Inlined NASM/GAS/C source samples
  asm/
    happy-path.spec.ts          — compile → run → step → registers populated
    compile-error.spec.ts       — error reporting + line annotation + recovery
    reverse-step.spec.ts        — Back button + register diff between steps
    multi-assembler.spec.ts     — NASM/GAS/FASM dropdown + status bar
    breakpoint.spec.ts          — gutter click toggles BP, persists on edit
    state-panels.spec.ts        — Stack/Memory/Security panels mount on session
  pwn/
    mode-switch.spec.ts         — lazy chunk loads, layout mounts
    cyclic-tool.spec.ts         — pattern generation + cyclic_find offset
    upload-binary.spec.ts       — drop ELF, checksec badges, symbols filter
    compile-source.spec.ts      — drop .c, auto-compile pipeline, vuln highlight
    security-guard.spec.ts      — live HTTP guards (LFI 403, traversal 422, lang 400)
  smoke/
    backend.sh      — 5 curl + WS checks (health, token, ADR-016, LFI, WS auth)
```

## Adding new modes (RE / Debug / Firmware / Protocols)

When a new mode lands, mirror the ASM/Pwn structure:

1. Add module-specific selectors to `AnvilApp` in `fixtures/anvil.ts`.
2. Create `tests/e2e/<mode>/` with the canonical specs:
   - `mode-switch.spec.ts` — lazy load + layout assertions
   - `<core-feature>.spec.ts` — happy path
   - `<core-feature>-error.spec.ts` — error handling
   - `security-guard.spec.ts` — live API guards if the mode has new endpoints

The fixtures are designed so a new mode rarely touches the global file —
add helpers, don't replace existing ones.

## Discipline (Sprint 18 lessons)

- **No `.skip` without a ticket.** A skipped test is a hidden regression.
- **No `await page.waitForTimeout(N)`.** Use `expect.poll`/`getByText` with
  built-in retries; arbitrary sleeps are the #1 source of CI flake.
- **Selectors via role + text** (`getByRole('button', { name: /Run/ })`),
  not CSS classes. The CSS split (Sprint 16) reorganised classes already.
- **One parcours = one spec.** Don't collapse multiple flows into a single test.
- **`reuseExistingServer`** lets locals iterate without restarting backend +
  vite on every run; CI sets `CI=1` which forces a clean boot.
