"""Anvil agent — file paths and BYOK config persistence (ADR-023)."""

from __future__ import annotations

import contextlib
import json
import logging
import os
from pathlib import Path

from backend.app.agent.models import AgentSettings, ProviderConfig

logger = logging.getLogger(__name__)


def anvil_dir() -> Path:
    """Return ``~/.anvil``, creating it with mode 700 if missing."""
    path = Path(os.path.expanduser("~/.anvil"))
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            path.chmod(0o700)
    return path


def config_path() -> Path:
    return anvil_dir() / "config.json"


def db_path() -> Path:
    return anvil_dir() / "agent.db"


def audit_log_path() -> Path:
    return anvil_dir() / "agent.log"


# ── Settings load/save ───────────────────────────────────
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-3-5-sonnet-latest",
    "openai": "gpt-4o-mini",
    "openrouter": "anthropic/claude-3.5-sonnet",
    "ollama": "llama3.1",
}


def _default_settings() -> AgentSettings:
    return AgentSettings(
        providers={name: ProviderConfig(default_model=model) for name, model in _DEFAULT_MODELS.items()}  # type: ignore[arg-type]
    )


def load_settings() -> AgentSettings:
    """Load settings from ``~/.anvil/config.json``. Returns defaults if missing."""
    path = config_path()
    if not path.exists():
        return _default_settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return AgentSettings.model_validate(raw)
    except Exception as exc:  # pragma: no cover — corrupted config
        logger.warning("Failed to load agent config (%s); using defaults", exc)
        return _default_settings()


def save_settings(settings: AgentSettings) -> None:
    """Persist settings with 0600 permissions."""
    path = config_path()
    payload = settings.model_dump(mode="json")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with contextlib.suppress(OSError):
        tmp.chmod(0o600)
    tmp.replace(path)


def mask_api_key(key: str) -> str:
    """Return a masked preview (first 6 chars + ``****``)."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:6]}...****"


def settings_for_frontend(settings: AgentSettings) -> dict:
    """Settings dict with API keys masked — safe to send to the UI."""
    providers: dict[str, dict] = {}
    for name, conf in settings.providers.items():
        providers[name] = {
            "api_key_masked": mask_api_key(conf.api_key),
            "has_key": bool(conf.api_key),
            "base_url": conf.base_url,
            "default_model": conf.default_model,
        }
    return {
        "active_provider": settings.active_provider,
        "providers": providers,
        "strict_mode": settings.strict_mode,
        "allow_write_exec": settings.allow_write_exec,
        "token_cap": settings.token_cap,
        "language": settings.language,
    }
