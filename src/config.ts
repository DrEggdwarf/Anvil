// Frontend tunables — extracted Sprint 16 to remove magic numbers scattered
// across hooks/components. Keep this file tiny: only constants, no logic.
//
// Naming convention: <DOMAIN>_<UNIT> in SCREAMING_SNAKE_CASE.

// ── WebSocket (api/ws.ts) ───────────────────────────────────
export const WS_RECONNECT_MS = 2000
export const WS_HEARTBEAT_MS = 30000

// ── ASM editor (components/editor/AsmEditor.tsx) ────────────
export const EDITOR_UNDO_HISTORY_MAX = 80
export const EDITOR_SNAPSHOT_DEBOUNCE_MS = 400
export const EDITOR_AUTOCOMPLETE_DEBOUNCE_MS = 30
export const EDITOR_AUTOCOMPLETE_BLUR_DELAY_MS = 150
export const EDITOR_FIND_FOCUS_DELAY_MS = 50
// Approximate width of one Geist-Mono char at 13px — recomputed at runtime
// from the actual canvas measurement, but seeded here to avoid a NaN frame.
export const EDITOR_DEFAULT_CHAR_WIDTH_PX = 7.22
