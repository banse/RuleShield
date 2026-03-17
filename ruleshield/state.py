"""Shared mutable state for the RuleShield proxy.

All subsystem instances are initialised to safe defaults here and
populated during the FastAPI lifespan (see app.py).  Route modules
import from this module instead of maintaining their own globals.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from ruleshield.cache import CacheManager
from ruleshield.config import Settings
from ruleshield.extractor import PromptExtractor
from ruleshield.metrics import MetricsCollector
from ruleshield.router import SmartRouter
from ruleshield.rules import RuleEngine
from ruleshield.integrations.slack import SlackNotifier

logger = logging.getLogger("ruleshield.proxy")

# ---------------------------------------------------------------------------
# Core subsystems (initialised at startup)
# ---------------------------------------------------------------------------

settings: Settings = Settings()
cache_manager: CacheManager = CacheManager()
rule_engine: RuleEngine = RuleEngine()
extractor: PromptExtractor = PromptExtractor()
metrics: MetricsCollector = MetricsCollector()
smart_router: SmartRouter | None = None
slack_notifier: SlackNotifier | None = None
feedback_manager: Any = None
http_client: httpx.AsyncClient | None = None

# ---------------------------------------------------------------------------
# Startup timestamp for uptime calculation
# ---------------------------------------------------------------------------

proxy_start_time: float = time.monotonic()

# ---------------------------------------------------------------------------
# Codex adapter (optional import)
# ---------------------------------------------------------------------------

try:
    from ruleshield.codex_adapter import (
        extract_prompt_from_codex,
        extract_messages_from_codex,
        wrap_codex_response,
        wrap_codex_streaming_response,
    )
    HAS_CODEX_ADAPTER = True
except ImportError:
    HAS_CODEX_ADAPTER = False
    extract_prompt_from_codex = None  # type: ignore[assignment]
    extract_messages_from_codex = None  # type: ignore[assignment]
    wrap_codex_response = None  # type: ignore[assignment]
    wrap_codex_streaming_response = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Test monitor state
# ---------------------------------------------------------------------------


@dataclass
class TestRunState:
    """In-memory state for a single monitored test run."""

    run_id: str
    script_path: str
    command: list[str]
    status: str = "active"
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    return_code: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    process: asyncio.subprocess.Process | None = None
    stop_requested: bool = False
    model_profile_id: str = "gpt5_mini_openai"
    model: str = "gpt-5.1-codex-mini"
    provider_label: str = "OpenAI OAuth"
    baseline_shadow_total: int = 0
    baseline_rule_hits: int = 0
    baseline_cache_hits: int = 0
    baseline_cost_without: float = 0.0
    baseline_cost_with: float = 0.0
    baseline_confidence_up: int = 0
    baseline_confidence_down: int = 0


TEST_MONITOR_LOCK = asyncio.Lock()
TEST_RUNS: dict[str, TestRunState] = {}
TEST_LAST_RUN_BY_SCRIPT: dict[str, str] = {}
