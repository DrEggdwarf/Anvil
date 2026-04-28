"""Anvil backend configuration — Pydantic settings with env var support."""

from __future__ import annotations

from enum import StrEnum

from pydantic_settings import BaseSettings


class AppMode(StrEnum):
    DEV = "dev"
    PROD = "prod"
    TEST = "test"


class Settings(BaseSettings):
    """All settings are overridable via ANVIL_ prefixed env vars."""

    model_config = {"env_prefix": "ANVIL_"}

    # ── App ──────────────────────────────────────────────
    app_mode: AppMode = AppMode.DEV
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000

    # ── Sessions ─────────────────────────────────────────
    max_sessions: int = 10
    session_timeout_seconds: int = 3600
    session_cleanup_interval_seconds: int = 60

    # ── Subprocess ───────────────────────────────────────
    subprocess_default_timeout_seconds: float = 30.0
    subprocess_kill_grace_seconds: float = 5.0
    subprocess_max_output_bytes: int = 10 * 1024 * 1024  # 10 MB

    # ── Files ────────────────────────────────────────────
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_upload_extensions: list[str] = [
        ".asm", ".s", ".c", ".h", ".py",
        ".elf", ".bin", ".hex", ".o",
    ]
    workspace_base_dir: str = "~/.anvil/workspaces"

    # ── WebSocket ────────────────────────────────────────
    ws_heartbeat_interval_seconds: float = 30.0
    ws_message_max_size_bytes: int = 1 * 1024 * 1024  # 1 MB

    # ── CORS ─────────────────────────────────────────────
    # ADR-015: locked down to Tauri/Vite local origins by default. Override with
    # ANVIL_CORS_ORIGINS='http://example.com,http://other.com' for web deployment.
    cors_origins: list[str] = [
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ]

    # ── Rate limiting ────────────────────────────────────
    # 600/min global cap; effective per-route limits live in slowapi decorators.
    rate_limit_per_minute: int = 600


settings = Settings()
