"""RuleShield Hermes -- Configuration management.

Loads settings from ~/.ruleshield/config.yaml, environment variables, or
sensible defaults.  Keeps things simple for the hackathon while remaining
extensible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RULESHIELD_DIR = Path.home() / ".ruleshield"
CONFIG_PATH = RULESHIELD_DIR / "config.yaml"
HERMES_DIR = Path.home() / ".hermes"
HERMES_CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"

# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


@dataclass
class Settings:
    """Central configuration container for RuleShield Hermes."""

    provider_url: str = "https://api.openai.com"
    api_key: str = ""
    port: int = 8347
    cache_enabled: bool = True
    rules_enabled: bool = True
    shadow_mode: bool = False
    shadow_test_confidence_floor: float = 0.0
    rules_dir: str = str(Path(__file__).resolve().parent.parent / "rules")
    log_level: str = "info"
    log_json: bool = False
    router_enabled: bool = True
    router_config: dict = field(default_factory=dict)  # optional custom model mappings
    hermes_bridge_enabled: bool = False
    hermes_bridge_model: str = "claude-haiku-4-5"
    prompt_trimming_enabled: bool = False
    slack_webhook: str = ""
    max_retries: int = 3
    admin_key: str = ""  # API key for management endpoints (empty = open access)
    rate_limit_rpm: int = 120  # requests per minute per IP
    max_body_size_mb: int = 10  # max request body in MB

    # ---- helpers ----------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dict representation suitable for YAML serialization."""
        return {
            "provider_url": self.provider_url,
            "api_key": self.api_key,
            "port": self.port,
            "cache_enabled": self.cache_enabled,
            "rules_enabled": self.rules_enabled,
            "shadow_mode": self.shadow_mode,
            "shadow_test_confidence_floor": self.shadow_test_confidence_floor,
            "rules_dir": self.rules_dir,
            "log_level": self.log_level,
            "log_json": self.log_json,
            "router_enabled": self.router_enabled,
            "router_config": self.router_config,
            "hermes_bridge_enabled": self.hermes_bridge_enabled,
            "hermes_bridge_model": self.hermes_bridge_model,
            "prompt_trimming_enabled": self.prompt_trimming_enabled,
            "slack_webhook": self.slack_webhook,
            "max_retries": self.max_retries,
            "admin_key": self.admin_key,
            "rate_limit_rpm": self.rate_limit_rpm,
            "max_body_size_mb": self.max_body_size_mb,
        }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _env_overrides(settings: Settings) -> Settings:
    """Apply environment-variable overrides on top of *settings*."""
    if val := os.getenv("RULESHIELD_PROVIDER_URL"):
        settings.provider_url = val
    if val := os.getenv("RULESHIELD_API_KEY"):
        settings.api_key = val
    if val := os.getenv("RULESHIELD_PORT"):
        settings.port = int(val)
    if val := os.getenv("RULESHIELD_CACHE_ENABLED"):
        settings.cache_enabled = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_RULES_ENABLED"):
        settings.rules_enabled = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_SHADOW_MODE"):
        settings.shadow_mode = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_SHADOW_TEST_CONFIDENCE_FLOOR"):
        settings.shadow_test_confidence_floor = float(val)
    if val := os.getenv("RULESHIELD_RULES_DIR"):
        settings.rules_dir = val
    if val := os.getenv("RULESHIELD_LOG_LEVEL"):
        settings.log_level = val.lower()
    if val := os.getenv("RULESHIELD_LOG_JSON"):
        settings.log_json = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_ROUTER_ENABLED"):
        settings.router_enabled = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_HERMES_BRIDGE_ENABLED"):
        settings.hermes_bridge_enabled = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_HERMES_BRIDGE_MODEL"):
        settings.hermes_bridge_model = val
    if val := os.getenv("RULESHIELD_PROMPT_TRIMMING_ENABLED"):
        settings.prompt_trimming_enabled = val.lower() in ("1", "true", "yes")
    if val := os.getenv("RULESHIELD_SLACK_WEBHOOK"):
        settings.slack_webhook = val
    if val := os.getenv("RULESHIELD_MAX_RETRIES"):
        settings.max_retries = int(val)
    if val := os.getenv("RULESHIELD_ADMIN_KEY"):
        settings.admin_key = val
    if val := os.getenv("RULESHIELD_RATE_LIMIT_RPM"):
        settings.rate_limit_rpm = int(val)
    if val := os.getenv("RULESHIELD_MAX_BODY_SIZE_MB"):
        settings.max_body_size_mb = int(val)
    return settings


def load_settings() -> Settings:
    """Load settings from config file then overlay env vars.

    Precedence (highest wins):
        1. Environment variables  (RULESHIELD_*)
        2. ~/.ruleshield/config.yaml
        3. Built-in defaults
    """
    settings = Settings()

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as fh:
                data = yaml.safe_load(fh) or {}
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
        except Exception:
            pass  # Fall back to defaults on parse errors.

    settings = _env_overrides(settings)
    return settings


def write_default_config() -> Path:
    """Write a default config.yaml to ~/.ruleshield/ and return its path."""
    RULESHIELD_DIR.mkdir(parents=True, exist_ok=True)
    defaults = Settings().as_dict()
    # Redact api_key so the file is safe to share.
    defaults["api_key"] = ""
    with open(CONFIG_PATH, "w") as fh:
        yaml.dump(defaults, fh, default_flow_style=False, sort_keys=False)
    return CONFIG_PATH


# ---------------------------------------------------------------------------
# Hermes integration helpers
# ---------------------------------------------------------------------------


def detect_hermes_config() -> dict[str, Any] | None:
    """Read and return the Hermes config if it exists."""
    if not HERMES_CONFIG_PATH.exists():
        return None
    try:
        with open(HERMES_CONFIG_PATH) as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return None


def ensure_hermes_config(proxy_url: str = "http://127.0.0.1:8347/v1") -> dict[str, Any]:
    """Create or patch Hermes config to point at the RuleShield proxy.

    Returns a small status object:

    {
        "ok": bool,
        "status": "created" | "patched" | "unchanged" | "error",
        "path": "...",
    }
    """
    created = not HERMES_CONFIG_PATH.exists()
    cfg = detect_hermes_config() or {}
    if not isinstance(cfg, dict):
        cfg = {}

    model = cfg.get("model")
    if not isinstance(model, dict):
        model = {}

    original_url = str(model.get("base_url", "") or "").strip()
    if original_url and original_url != proxy_url:
        _save_original_hermes_url(original_url)

    if created:
        # Minimal Hermes starter profile for a blank local setup.
        model.setdefault("default", "gpt-5.1-codex-mini")
        model.setdefault("provider", "openai-codex")
        cfg.setdefault("toolsets", ["all"])

    model["base_url"] = proxy_url
    cfg["model"] = model

    try:
        HERMES_DIR.mkdir(parents=True, exist_ok=True)
        with open(HERMES_CONFIG_PATH, "w") as fh:
            yaml.dump(cfg, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
        status = "created" if created else ("unchanged" if original_url == proxy_url else "patched")
        return {"ok": True, "status": status, "path": str(HERMES_CONFIG_PATH)}
    except Exception:
        return {"ok": False, "status": "error", "path": str(HERMES_CONFIG_PATH)}


def patch_hermes_config(proxy_url: str = "http://127.0.0.1:8347/v1") -> bool:
    """Backward-compatible bool wrapper around :func:`ensure_hermes_config`."""
    return bool(ensure_hermes_config(proxy_url).get("ok"))


def restore_hermes_config() -> bool:
    """Restore the original Hermes base_url."""
    cfg = detect_hermes_config()
    if cfg is None:
        return False

    original_url = _load_original_hermes_url()
    if not original_url:
        return False

    model = cfg.get("model", {})
    model["base_url"] = original_url
    cfg["model"] = model

    try:
        with open(HERMES_CONFIG_PATH, "w") as fh:
            yaml.dump(cfg, fh, default_flow_style=False, sort_keys=False,
                      allow_unicode=True)
        return True
    except Exception:
        return False


def _save_original_hermes_url(url: str) -> None:
    backup = RULESHIELD_DIR / "hermes_original_url.txt"
    RULESHIELD_DIR.mkdir(parents=True, exist_ok=True)
    backup.write_text(url)


def _load_original_hermes_url() -> str:
    backup = RULESHIELD_DIR / "hermes_original_url.txt"
    if backup.exists():
        return backup.read_text().strip()
    return ""
