"""Tests for Anvil configuration (core/config.py)."""


import pytest


class TestSettings:
    def test_default_values(self):
        from backend.app.core.config import Settings

        s = Settings()
        assert s.app_mode == "dev"
        assert s.version == "0.1.0"
        assert s.max_sessions == 10
        assert s.session_timeout_seconds == 3600
        assert s.subprocess_default_timeout_seconds == 30.0
        assert s.subprocess_kill_grace_seconds == 5.0
        assert s.max_upload_size_bytes == 10 * 1024 * 1024
        assert ".asm" in s.allowed_upload_extensions
        assert ".c" in s.allowed_upload_extensions
        assert s.ws_heartbeat_interval_seconds == 30.0
        assert s.rate_limit_per_minute == 600

    def test_cors_origins_default(self):
        """ADR-015: defaults are tight (Tauri/Vite local only), never `*`."""
        from backend.app.core.config import Settings

        s = Settings()
        assert "http://localhost:1420" in s.cors_origins
        assert "tauri://localhost" in s.cors_origins
        assert "*" not in s.cors_origins

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("ANVIL_MAX_SESSIONS", "42")
        monkeypatch.setenv("ANVIL_APP_MODE", "prod")

        from backend.app.core.config import Settings

        s = Settings()
        assert s.max_sessions == 42
        assert s.app_mode == "prod"

    def test_invalid_app_mode(self, monkeypatch):
        monkeypatch.setenv("ANVIL_APP_MODE", "invalid")

        from backend.app.core.config import Settings

        with pytest.raises(Exception):
            Settings()
