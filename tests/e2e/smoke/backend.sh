#!/usr/bin/env bash
# Sprint 18 e2e — backend smoke test.
#
# Validates the bare bones of the FastAPI surface without booting the frontend
# or Playwright. Cheap (<5s) and runs in CI alongside pytest as a tripwire.
#
# Assumes the backend is already up on :8000. If not, the caller starts it.
# Returns non-zero on the first failure.

set -euo pipefail

BACKEND=${ANVIL_BACKEND:-http://127.0.0.1:8000}
PASS=0
FAIL=0

ok() { echo "  ✓ $1"; PASS=$((PASS+1)); }
ko() { echo "  ✗ $1" >&2; FAIL=$((FAIL+1)); }

echo "=== Backend smoke against $BACKEND ==="

# 1. Health endpoint
status=$(curl -s -o /tmp/anvil_smoke_health -w "%{http_code}" "$BACKEND/api/health")
if [[ "$status" == "200" ]] && grep -q '"status":"ok"' /tmp/anvil_smoke_health; then
  ok "health returns 200 ok"
else
  ko "health returned $status"
fi

# 2. Session create returns a 32-hex token (Sprint 14 ADR-016)
# Use pwn bridge — always available via pip install -e "backend/[dev,pwn]"
sess=$(curl -s -X POST "$BACKEND/api/sessions" -H 'Content-Type: application/json' -d '{"bridge_type":"pwn"}')
sid=$(echo "$sess" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
token=$(echo "$sess" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))")
if [[ -n "$sid" && "$token" =~ ^[a-f0-9]{32}$ ]]; then
  ok "session create returns id + 32-hex token"
else
  ko "session create did not surface a token (got: $(echo "$sess" | head -c 200))"
fi

# 3. GET session info masks the token
info=$(curl -s "$BACKEND/api/sessions/$sid")
if echo "$info" | grep -q '"token"'; then
  ko "GET /api/sessions/{id} leaks token"
else
  ok "GET /api/sessions/{id} hides token (ADR-016)"
fi

# 4. Path traversal on /api/pwn/elf/checksec is rejected with 403
pwn_sess=$(curl -s -X POST "$BACKEND/api/sessions" -H 'Content-Type: application/json' -d '{"bridge_type":"pwn"}')
pwn_sid=$(echo "$pwn_sess" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
status=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND/api/pwn/$pwn_sid/elf/checksec?path=%2Fetc%2Fpasswd")
if [[ "$status" == "403" ]]; then
  ok "LFI on /api/pwn/elf/checksec is blocked (Sprint 14 #3)"
else
  ko "LFI guard returned $status (expected 403)"
fi

# 5. WS without token is rejected (HTTP 403 during handshake)
status=$(python3 - "$sid" <<'PY' 2>/dev/null || echo "exception"
import asyncio, sys, websockets
async def go(sid):
    try:
        async with websockets.connect(f"ws://127.0.0.1:8000/ws/pwn/{sid}", open_timeout=2):
            print("200")
    except websockets.InvalidStatus as e:
        print(e.response.status_code)
    except Exception:
        print("rejected")
asyncio.run(go(sys.argv[1]))
PY
)
if [[ "$status" == "403" || "$status" == "rejected" ]]; then
  ok "WS handshake without token is rejected"
else
  ko "WS handshake returned $status (expected 403/rejected)"
fi

# Cleanup
curl -s -X DELETE "$BACKEND/api/sessions/$sid" >/dev/null || true
curl -s -X DELETE "$BACKEND/api/sessions/$pwn_sid" >/dev/null || true

echo ""
echo "=== $PASS passed, $FAIL failed ==="
[[ "$FAIL" -eq 0 ]]
