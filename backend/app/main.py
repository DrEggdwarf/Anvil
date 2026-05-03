"""Anvil Backend — FastAPI entry point."""

from __future__ import annotations

import logging

from backend.app.api import compile, firmware, gdb, health, protocol, pwn, rizin, sessions, ws
from backend.app.core.config import settings
from backend.app.core.exceptions import AnvilError
from backend.app.core.lifecycle import lifespan
from backend.app.models.errors import ErrorResponse
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

logging.basicConfig(
    level=logging.DEBUG if settings.app_mode == "dev" else logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

# ── Rate limiting ────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)

app = FastAPI(
    title="Anvil",
    description="Low-Level Security Toolkit API",
    version=settings.version,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error handler ────────────────────────────────────────
_STATUS_MAP: dict[str, int] = {
    "SESSION_NOT_FOUND": 404,
    "SESSION_EXPIRED": 410,
    "SESSION_LIMIT_REACHED": 429,
    "BRIDGE_NOT_READY": 503,
    "BRIDGE_TIMEOUT": 504,
    "BRIDGE_CRASH": 500,
    "TOOL_NOT_FOUND": 503,
    "VALIDATION_ERROR": 400,
    "INVALID_FILE": 400,
    "INVALID_COMMAND": 400,
    "UNKNOWN_BRIDGE_TYPE": 400,
    "SUBPROCESS_TIMEOUT": 504,
    "SUBPROCESS_CRASH": 500,
    "INJECTION_BLOCKED": 400,
    "PATH_BLOCKED": 403,
    "PATH_TRAVERSAL": 403,
    "UNSUPPORTED_LANGUAGE": 400,
    "FILE_NOT_FOUND": 404,
    "INVALID_BASE64": 400,
    "WRONG_SESSION_TYPE": 400,
    "COMPILE_ERROR": 422,
    "DECOMPILER_MISSING": 422,
}


@app.exception_handler(AnvilError)
async def anvil_error_handler(request: Request, exc: AnvilError) -> JSONResponse:
    status = _STATUS_MAP.get(exc.code, 500)
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=exc.message,
            code=exc.code,
            details=exc.details,
        ).model_dump(),
    )


# ── Routers ──────────────────────────────────────────────
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(gdb.router)
app.include_router(compile.router)
app.include_router(rizin.router)
app.include_router(pwn.router)
app.include_router(firmware.router)
app.include_router(protocol.router)
app.include_router(ws.router)
