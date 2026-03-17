"""RuleShield Hermes -- FastAPI proxy server.

Sits between the Hermes AI Agent (or any OpenAI-compatible client) and the
upstream LLM provider.  For every request the proxy:

  1. Checks the semantic/exact cache for a hit.
  2. Evaluates cost-saving rules.
  3. If neither fires, forwards the request transparently to the provider.
  4. Records metrics and stores the response in the cache.

Streaming (SSE) is fully supported -- the proxy relays chunks as they arrive
from the upstream provider.
"""

from __future__ import annotations

import asyncio
import os
import hashlib
import json
import logging
import random
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from ruleshield.cache import CacheManager
from ruleshield.config import CONFIG_PATH, RULESHIELD_DIR, Settings, load_settings
from ruleshield.cron_automation import build_automation_suggestion
from ruleshield.cron_execution import get_profile_execution_history
from ruleshield.cron_optimizer import (
    activate_cron_profile,
    archive_cron_profile,
    delete_cron_profile,
    duplicate_cron_profile,
    execute_active_cron_profile,
    list_cron_profiles,
    load_cron_profile,
    restore_cron_profile,
    update_draft_cron_profile,
)
from ruleshield.cron_validation import get_profile_validation_history
from ruleshield.cron_validation import run_cron_shadow
from ruleshield.extractor import PromptExtractor
from ruleshield.integrations.slack import SlackNotifier
from ruleshield.metrics import MetricsCollector
from ruleshield.router import SmartRouter
from ruleshield.rules import RuleEngine

try:
    from ruleshield.codex_adapter import (
        extract_prompt_from_codex,
        extract_messages_from_codex,
        wrap_codex_response,
        wrap_codex_streaming_response,
    )
    _HAS_CODEX_ADAPTER = True
except ImportError:
    _HAS_CODEX_ADAPTER = False

# ---------------------------------------------------------------------------
# Globals initialised at startup
# ---------------------------------------------------------------------------

logger = logging.getLogger("ruleshield.proxy")

settings: Settings = Settings()
cache_manager = CacheManager()
rule_engine = RuleEngine()
extractor = PromptExtractor()
metrics = MetricsCollector()
smart_router: SmartRouter | None = None
slack_notifier: SlackNotifier | None = None
feedback_manager: Any = None
http_client: httpx.AsyncClient | None = None


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


_TEST_MONITOR_LOCK = asyncio.Lock()
_TEST_RUNS: dict[str, TestRunState] = {}
_TEST_LAST_RUN_BY_SCRIPT: dict[str, str] = {}

_DEFAULT_TEST_MODEL_PROFILES: list[dict[str, str]] = [
    {
        "id": "gpt5_mini_openai",
        "label": "GPT-5.1 Mini (OpenAI OAuth)",
        "provider": "openai_oauth",
        "provider_label": "OpenAI OAuth",
        "model": "gpt-5.1-codex-mini",
        "fallback_model": "gpt-4.1-mini",
        # Future-proofing for profile-specific script variants.
        # Example: test_training_health_check.gpt5_mini_openai.sh
        "script_suffix": "gpt5_mini_openai",
    },
    {
        "id": "gpt5_max_openai",
        "label": "GPT-5.1 Max (OpenAI OAuth)",
        "provider": "openai_oauth",
        "provider_label": "OpenAI OAuth",
        "model": "gpt-5.1-codex-max",
        "fallback_model": "gpt-5.1-codex-mini",
        "script_suffix": "gpt5_max_openai",
    },
    {
        "id": "gpt41_mini_openai",
        "label": "GPT-4.1 Mini (OpenAI OAuth)",
        "provider": "openai_oauth",
        "provider_label": "OpenAI OAuth",
        "model": "gpt-4.1-mini",
        "fallback_model": "gpt-5.1-codex-mini",
        "script_suffix": "gpt41_mini_openai",
    },
    {
        "id": "openrouter_arcee_trinity_free",
        "label": "Arcee Trinity Large (OpenRouter Free)",
        "provider": "openrouter",
        "provider_label": "OpenRouter",
        "model": "arcee-ai/trinity-large-preview:free",
        "fallback_model": "stepfun/step-3.5-flash:free",
        "script_suffix": "openrouter_arcee_trinity_free",
    },
    {
        "id": "openrouter_stepfun_flash_free",
        "label": "StepFun 3.5 Flash (OpenRouter Free)",
        "provider": "openrouter",
        "provider_label": "OpenRouter",
        "model": "stepfun/step-3.5-flash:free",
        "fallback_model": "arcee-ai/trinity-large-preview:free",
        "script_suffix": "openrouter_stepfun_flash_free",
    },
]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODEL_PROFILES_PATH = _PROJECT_ROOT / "ruleshield" / "training_configs" / "model_profiles.yaml"


def _to_bool(value: Any) -> bool | None:
    """Best-effort bool conversion for config payload values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def _persist_runtime_settings(changes: dict[str, bool]) -> bool:
    """Persist runtime toggle changes into ~/.ruleshield/config.yaml."""
    try:
        RULESHIELD_DIR.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            if isinstance(loaded, dict):
                data = loaded
        data.update(changes)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            yaml.dump(data, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception as exc:
        logger.warning("Failed to persist runtime settings: %s", exc)
        return False

# ---------------------------------------------------------------------------
# Codex Responses API pricing ($ per 1M tokens)
# ---------------------------------------------------------------------------

CODEX_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.3-codex": {"input": 5.0, "output": 20.0},
    "gpt-5.2-codex": {"input": 2.5, "output": 10.0},
    "gpt-5.1-codex-max": {"input": 4.0, "output": 16.0},
    "gpt-5.1-codex-mini": {"input": 0.25, "output": 2.0},
    "gpt-5.4": {"input": 2.0, "output": 8.0},
    "gpt-5.4-pro": {"input": 5.0, "output": 20.0},
}


def _compute_codex_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD for a Codex API call."""
    pricing = CODEX_PRICING.get(model, {"input": 2.5, "output": 10.0})
    return (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]


def _test_roots() -> list[Path]:
    """Directories that contain executable test scripts."""
    cwd = Path.cwd()
    roots = [cwd / "tests", cwd / "demo"]
    return [root for root in roots if root.exists() and root.is_dir()]


def _discover_test_scripts() -> list[dict[str, str]]:
    """Return supported test scripts from test/demo directories."""
    scripts: list[dict[str, str]] = []
    for root in _test_roots():
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            name = file_path.name
            if file_path.suffix == ".sh" and name.startswith("test_"):
                script_type = "shell"
            elif file_path.suffix == ".py" and name.startswith("test_"):
                script_type = "pytest"
            else:
                continue

            scripts.append({
                "path": str(file_path.resolve()),
                "name": name,
                "type": script_type,
            })
    return scripts


_RUN_DIR_PATTERN = re.compile(r"Run directory:\s*(.+)$")
_SHADOW_FINAL_PATTERN = re.compile(r"shadow:\s*(.+shadow-final\.json)\s*$")


def _extract_run_directory_from_events(events: list[dict[str, Any]]) -> Path | None:
    """Best-effort extraction of suite run directory from monitor events."""
    for event in events:
        text = str(event.get("text") or "").strip()
        if not text:
            continue
        run_match = _RUN_DIR_PATTERN.search(text)
        if run_match:
            candidate = Path(run_match.group(1).strip()).expanduser()
            if candidate.exists():
                return candidate
        shadow_match = _SHADOW_FINAL_PATTERN.search(text)
        if shadow_match:
            shadow_file = Path(shadow_match.group(1).strip()).expanduser()
            if shadow_file.exists():
                return shadow_file.parent
    return None


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _safe_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except Exception:
        return 0.0


def _parse_request_created_at(value: Any) -> datetime | None:
    """Parse request timestamps used in /api/requests entries."""
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _count_resolution_types(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        key = str(entry.get("resolution_type") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _count_confidence_directions(events: list[dict[str, Any]]) -> tuple[int, int]:
    up = 0
    down = 0
    for event in events:
        if str(event.get("event_type", "")) != "confidence_update":
            continue
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        direction = str(details.get("direction", event.get("direction", ""))).lower()
        if direction == "up":
            up += 1
        elif direction == "down":
            down += 1
    return up, down


def _build_test_command(script_path: Path, script_type: str) -> list[str]:
    """Build command used to execute a test script."""
    if script_type == "shell":
        return ["bash", str(script_path)]
    python_bin = Path.cwd() / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path("/usr/bin/env")
        return [str(python_bin), "python3", "-m", "pytest", str(script_path), "-q"]
    return [str(python_bin), "-m", "pytest", str(script_path), "-q"]


def _model_profiles() -> list[dict[str, str]]:
    required_fields = {
        "id",
        "label",
        "provider",
        "provider_label",
        "model",
        "fallback_model",
        "script_suffix",
    }

    if not _MODEL_PROFILES_PATH.is_file():
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    try:
        raw = yaml.safe_load(_MODEL_PROFILES_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("Could not read model profiles file %s: %s", _MODEL_PROFILES_PATH, exc)
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    profiles = raw.get("profiles", [])
    if not isinstance(profiles, list):
        logger.warning("Invalid model profiles format in %s: 'profiles' must be a list", _MODEL_PROFILES_PATH)
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    normalized: list[dict[str, str]] = []
    for entry in profiles:
        if not isinstance(entry, dict):
            continue
        missing = [field for field in required_fields if not entry.get(field)]
        if missing:
            logger.warning(
                "Skipping invalid model profile in %s (missing: %s)",
                _MODEL_PROFILES_PATH,
                ", ".join(sorted(missing)),
            )
            continue
        normalized.append({field: str(entry[field]) for field in required_fields})

    if not normalized:
        logger.warning("No valid model profiles found in %s; using defaults", _MODEL_PROFILES_PATH)
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    return normalized


def _profile_by_id(profile_id: str | None) -> dict[str, str]:
    profile_map = {profile["id"]: profile for profile in _model_profiles()}
    if profile_id and profile_id in profile_map:
        return profile_map[profile_id]
    return _model_profiles()[0]


def _resolve_profile_script_path(script_file: Path, profile: dict[str, str]) -> Path:
    """Resolve profile-specific test script variant when it exists.

    Expected variant naming:
      test_name.<profile_id>.sh
    Example:
      test_training_health_check.gpt5_max_openai.sh

    Falls back to the base script while we have only one set of test files.
    """
    if script_file.suffix != ".sh":
        return script_file
    variant = script_file.with_name(
        f"{script_file.stem}.{profile['script_suffix']}{script_file.suffix}"
    )
    if variant.is_file():
        return variant
    return script_file


def _status_from_run(run: TestRunState | None) -> str:
    if run is None:
        return "not_started"
    return run.status


def _append_test_event(run: TestRunState, kind: str, text: str):
    run.events.append({
        "ts": time.time(),
        "kind": kind,
        "text": text.rstrip(),
    })
    if len(run.events) > 1200:
        run.events = run.events[-1200:]


async def _stream_test_output(run: TestRunState):
    """Stream process output lines into run events."""
    proc = run.process
    if proc is None or proc.stdout is None:
        return
    while True:
        raw_line = await proc.stdout.readline()
        if not raw_line:
            break
        line = raw_line.decode(errors="replace").rstrip("\n")
        async with _TEST_MONITOR_LOCK:
            _append_test_event(run, "output", line)


async def _wait_test_run(run: TestRunState):
    """Finalize run state when the process exits."""
    proc = run.process
    if proc is None:
        return
    return_code = await proc.wait()
    async with _TEST_MONITOR_LOCK:
        run.return_code = return_code
        run.ended_at = time.time()
        if return_code == 0:
            run.status = "inactive"
        else:
            run.status = "failed"
        _append_test_event(
            run,
            "output",
            f"[process exited] code={return_code} status={run.status}",
        )


def _extract_codex_content(response: dict) -> str:
    """Extract text content from a cached response (may be OpenAI or Codex format).

    Tries Codex format first (output[].content[].text), then OpenAI chat
    format (choices[].message.content), and falls back to stringifying the
    whole response dict.
    """
    # Codex Responses API format: response.output[].content[].text
    try:
        text_parts: list[str] = []
        for output_item in response.get("output", []):
            if isinstance(output_item, dict):
                for content_part in output_item.get("content", []):
                    if not isinstance(content_part, dict):
                        continue
                    text = content_part.get("text")
                    if isinstance(text, str) and text:
                        text_parts.append(text)
        if text_parts:
            return "".join(text_parts)
    except (TypeError, AttributeError):
        pass

    # OpenAI Chat Completions format: choices[0].message.content
    try:
        choices = response.get("choices", [])
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message", {})
            if isinstance(msg, dict) and msg.get("content"):
                return msg["content"]
    except (TypeError, AttributeError, IndexError):
        pass

    # Plain content key (from cache_manager.log_request storage)
    if isinstance(response.get("content"), str):
        return response["content"]

    return str(response) if response else ""


def _extract_codex_assistant_text(response: dict[str, Any]) -> str:
    """Extract only real assistant text from a Codex-style response object."""
    if not isinstance(response, dict):
        return ""

    text_parts: list[str] = []

    for output_item in response.get("output", []):
        if not isinstance(output_item, dict):
            continue
        for content_part in output_item.get("content", []):
            if not isinstance(content_part, dict):
                continue
            text = content_part.get("text")
            if isinstance(text, str) and text:
                text_parts.append(text)

    if text_parts:
        return "".join(text_parts)

    content = response.get("content")
    if isinstance(content, str):
        return content

    return ""


def _extract_codex_event_text(event_data: dict[str, Any]) -> str:
    """Extract assistant text from a single Codex SSE event payload."""
    if not isinstance(event_data, dict):
        return ""

    event_type = event_data.get("type", "")
    if event_type == "response.output_text.done":
        text = event_data.get("text", "")
        return text if isinstance(text, str) else ""

    if event_type == "response.content_part.done":
        part = event_data.get("part", {})
        if isinstance(part, dict):
            text = part.get("text", "")
            if isinstance(text, str):
                return text

    if event_type == "response.output_item.done":
        item = event_data.get("item", {})
        if isinstance(item, dict):
            return _extract_codex_assistant_text({"output": [item]})

    if event_type == "response.completed":
        response = event_data.get("response", {})
        if isinstance(response, dict):
            return _extract_codex_assistant_text(response)

    return ""


def _select_codex_stream_text(stream_state: dict[str, Any]) -> str:
    """Choose the best available assistant text extracted from a Codex stream."""
    delta_text = "".join(stream_state.get("content_parts", [])).strip()
    fallback_texts = [
        text.strip()
        for text in stream_state.get("fallback_texts", [])
        if isinstance(text, str) and text.strip()
    ]
    fallback_text = max(fallback_texts, key=len, default="")

    if len(fallback_text) > len(delta_text):
        return fallback_text
    return delta_text or fallback_text


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global settings, http_client, smart_router, slack_notifier, feedback_manager

    settings = load_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "RuleShield Hermes proxy starting -- provider=%s port=%s",
        settings.provider_url,
        settings.port,
    )

    # Initialise subsystems.
    await cache_manager.init()
    await rule_engine.init(rules_dir=settings.rules_dir)
    await extractor.init()
    await metrics.init()

    from ruleshield.feedback import RuleFeedback

    feedback_manager = RuleFeedback(rule_engine)
    await feedback_manager.init()

    if settings.router_enabled:
        smart_router = SmartRouter(config=settings.router_config or None)
        logger.info("Smart Router enabled -- complexity-based model routing active")

    if settings.slack_webhook:
        slack_notifier = SlackNotifier(webhook_url=settings.slack_webhook)
        logger.info("Slack notifications enabled")

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )

    yield

    # Shutdown.
    if feedback_manager is not None:
        await feedback_manager.close()
    if cache_manager is not None:
        await cache_manager.close()
    if http_client:
        await http_client.aclose()
    logger.info("RuleShield Hermes proxy stopped.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RuleShield Hermes",
    version="0.1.0",
    description="LLM cost-optimizer proxy for the Hermes AI Agent",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS -- allow the SvelteKit dashboard to talk to the proxy
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:4173",
        "http://localhost:4174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:4174",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Security middleware
# ---------------------------------------------------------------------------

class SimpleRateLimiter:
    """In-memory per-IP rate limiter."""
    def __init__(self, rpm: int = 120):
        self.rpm = rpm
        self._buckets: dict[str, list[float]] = {}
    def check(self, ip: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets.setdefault(ip, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= self.rpm:
            return False
        bucket.append(now)
        return True

_rate_limiter = SimpleRateLimiter(settings.rate_limit_rpm if hasattr(settings, 'rate_limit_rpm') else 120)

async def require_admin_key(authorization: str = Header(None, alias="X-RuleShield-Admin-Key")):
    """Require admin key for management endpoints."""
    if not settings.admin_key:
        return
    if not authorization or authorization != settings.admin_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.check(ip):
        logger.warning("Rate limit exceeded for %s", ip)
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    return await call_next(request)

@app.middleware("http")
async def body_size_middleware(request: Request, call_next):
    cl = request.headers.get("content-length")
    max_bytes = getattr(settings, 'max_body_size_mb', 10) * 1024 * 1024
    if cl and int(cl) > max_bytes:
        return JSONResponse(status_code=413, content={"error": "Request body too large"})
    return await call_next(request)

# ---------------------------------------------------------------------------
# Startup timestamp for uptime calculation
# ---------------------------------------------------------------------------

_proxy_start_time: float = time.monotonic()

# ---------------------------------------------------------------------------
# Health / info endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Liveness check."""
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Test monitor API endpoints
# ---------------------------------------------------------------------------


@app.get("/api/test-monitor/scripts")
async def api_test_monitor_scripts():
    """List all test scripts and their current status."""
    try:
        discovered = _discover_test_scripts()
        script_map = {entry["path"]: entry for entry in discovered}

        async with _TEST_MONITOR_LOCK:
            scripts = []
            for path, entry in sorted(script_map.items(), key=lambda item: item[1]["name"]):
                last_run_id = _TEST_LAST_RUN_BY_SCRIPT.get(path)
                last_run = _TEST_RUNS.get(last_run_id) if last_run_id else None
                scripts.append({
                    "path": path,
                    "name": entry["name"],
                    "type": entry["type"],
                    "default_model_profile_id": _model_profiles()[0]["id"],
                    "status": _status_from_run(last_run),
                    "active_run_id": last_run.run_id if last_run and last_run.status == "active" else None,
                    "last_run_id": last_run.run_id if last_run else None,
                    "last_return_code": last_run.return_code if last_run else None,
                    "last_started_at": last_run.started_at if last_run else None,
                    "last_ended_at": last_run.ended_at if last_run else None,
                })
            active_count = sum(1 for run in _TEST_RUNS.values() if run.status == "active")
            return {
                "scripts": scripts,
                "active_runs": active_count,
                "total": len(scripts),
            }
    except Exception as exc:
        logger.error("Failed to fetch /api/test-monitor/scripts: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/test-monitor/model-profiles")
async def api_test_monitor_model_profiles():
    """List available model/provider profiles for test runs."""
    try:
        profiles = _model_profiles()
        return {
            "profiles": profiles,
            "default_profile_id": profiles[0]["id"] if profiles else "",
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/test-monitor/model-profiles: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/test-monitor/runs")
async def api_test_monitor_runs(limit: int = Query(default=40, ge=1, le=200)):
    """List recent runs across all test scripts."""
    try:
        async with _TEST_MONITOR_LOCK:
            runs = sorted(
                _TEST_RUNS.values(),
                key=lambda run: run.started_at,
                reverse=True,
            )[:limit]
            out = [
                {
                    "run_id": run.run_id,
                    "script_path": run.script_path,
                    "command": run.command,
                    "status": run.status,
                    "started_at": run.started_at,
                    "ended_at": run.ended_at,
                    "return_code": run.return_code,
                    "event_count": len(run.events),
                    "model_profile_id": run.model_profile_id,
                    "model": run.model,
                    "provider_label": run.provider_label,
                }
                for run in runs
            ]
        return {"runs": out, "limit": limit}
    except Exception as exc:
        logger.error("Failed to fetch /api/test-monitor/runs: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/test-monitor/runs/{run_id}/events")
async def api_test_monitor_run_events(
    run_id: str,
    limit: int = Query(default=500, ge=20, le=2000),
):
    """Return monitor events (input/output text) for one run."""
    try:
        async with _TEST_MONITOR_LOCK:
            run = _TEST_RUNS.get(run_id)
            if run is None:
                return {
                    "run_id": run_id,
                    "status": "not_found",
                    "events": [],
                }
            events = run.events[-limit:]
            return {
                "run_id": run_id,
                "status": run.status,
                "events": events,
            }
    except Exception as exc:
        logger.error("Failed to fetch /api/test-monitor/runs/%s/events: %s", run_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/test-monitor/runs/{run_id}/ruleshield")
async def api_test_monitor_run_ruleshield(run_id: str):
    """Run-specific RuleShield snapshot using existing prompt-training summaries."""
    try:
        async with _TEST_MONITOR_LOCK:
            run = _TEST_RUNS.get(run_id)
            if run is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Run '{run_id}' not found"},
                )
            run_dir = _extract_run_directory_from_events(run.events)

        started_at_dt = datetime.fromtimestamp(run.started_at, tz=timezone.utc)

        async def _build_live_preview(run_dir_value: str) -> dict[str, Any]:
            stats_snapshot = await api_stats()
            stats_payload = stats_snapshot if isinstance(stats_snapshot, dict) else {}
            shadow_snapshot = await api_shadow(recent=None, rule_id=None)
            shadow_payload = shadow_snapshot if isinstance(shadow_snapshot, dict) else {}
            requests_payload = await api_requests(limit=300)
            requests_list = requests_payload.get("requests", []) if isinstance(requests_payload, dict) else []
            rule_events_payload = await api_rule_events(limit=500)
            rule_events_list = (
                rule_events_payload.get("events", [])
                if isinstance(rule_events_payload, dict) and isinstance(rule_events_payload.get("events"), list)
                else []
            )

            recent_requests = [
                entry
                for entry in requests_list
                if isinstance(entry, dict)
                and (_parse_request_created_at(entry.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc))
                >= started_at_dt
            ]
            request_breakdown = _count_resolution_types(recent_requests)

            recent_rule_events = [
                event
                for event in rule_events_list
                if isinstance(event, dict)
                and (_parse_request_created_at(event.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc))
                >= started_at_dt
            ]
            recent_rule_events = sorted(
                recent_rule_events,
                key=lambda item: str(item.get("created_at", "")),
                reverse=True,
            )[:12]

            conf_up_total, conf_down_total = _count_confidence_directions(rule_events_list)
            confidence_up = max(0, conf_up_total - int(run.baseline_confidence_up))
            confidence_down = max(0, conf_down_total - int(run.baseline_confidence_down))

            current_rule_hits = int(_safe_number(stats_payload.get("rule_hits", 0)))
            current_cache_hits = int(_safe_number(stats_payload.get("cache_hits", 0)))
            current_shadow_total = int(_safe_number(shadow_payload.get("total_comparisons", 0)))
            current_cost_without = float(_safe_number(stats_payload.get("cost_without", 0.0)))
            current_cost_with = float(_safe_number(stats_payload.get("cost_with", 0.0)))

            triggered_rules = max(
                int(request_breakdown.get("rule", 0)),
                max(0, current_rule_hits - int(run.baseline_rule_hits)),
            )
            triggered_cache = max(
                int(request_breakdown.get("cache", 0)),
                max(0, current_cache_hits - int(run.baseline_cache_hits)),
            )
            would_trigger_shadow = max(0, current_shadow_total - int(run.baseline_shadow_total))
            cost_without = max(0.0, current_cost_without - float(run.baseline_cost_without))
            cost_with = max(0.0, current_cost_with - float(run.baseline_cost_with))
            savings_usd = max(0.0, cost_without - cost_with)
            savings_pct = (savings_usd / cost_without * 100.0) if cost_without > 0 else 0.0

            return {
                "run_id": run_id,
                "status": run.status,
                "available": True,
                "source": "live_preview",
                "run_dir": run_dir_value,
                "request_breakdown": request_breakdown,
                "triggered_rules": triggered_rules,
                "triggered_cache": triggered_cache,
                "would_trigger_shadow": would_trigger_shadow,
                "cost_without": round(cost_without, 6),
                "cost_with": round(cost_with, 6),
                "savings_usd": round(savings_usd, 6),
                "savings_pct": round(savings_pct, 2),
                "shadow_enabled": bool(shadow_payload.get("enabled", settings.shadow_mode)),
                "confidence_up": confidence_up,
                "confidence_down": confidence_down,
                "recent_rule_events": recent_rule_events,
            }

        if run_dir is None:
            return await _build_live_preview("")

        summary_paths = sorted(run_dir.rglob("ruleshield-summary.json"))
        if not summary_paths:
            return await _build_live_preview(str(run_dir))

        summaries = [_read_json_file(path) for path in summary_paths]
        summaries = [entry for entry in summaries if entry]
        if not summaries:
            return {
                "run_id": run_id,
                "status": run.status,
                "available": False,
                "run_dir": str(run_dir),
                "reason": "invalid_summary_files",
            }

        request_breakdown: dict[str, int] = {}
        recent_rule_events: list[dict[str, Any]] = []
        confidence_up = 0
        confidence_down = 0

        for entry in summaries:
            rs = entry.get("ruleshield_summary", {}) if isinstance(entry.get("ruleshield_summary"), dict) else {}
            if not isinstance(rs, dict):
                continue
            breakdown = rs.get("request_breakdown", {})
            if isinstance(breakdown, dict):
                for key, value in breakdown.items():
                    try:
                        request_breakdown[key] = request_breakdown.get(key, 0) + int(value)
                    except Exception:
                        continue
            events = rs.get("recent_rule_events", [])
            if isinstance(events, list):
                recent_rule_events.extend([event for event in events if isinstance(event, dict)])

        recent_rule_events_sorted = sorted(
            recent_rule_events,
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )
        confidence_events = [
            event for event in recent_rule_events_sorted if event.get("event_type") == "confidence_update"
        ]
        for event in confidence_events:
            direction = str((event.get("details") or {}).get("direction", event.get("direction", ""))).lower()
            if direction == "up":
                confidence_up += 1
            elif direction == "down":
                confidence_down += 1

        first = summaries[0]
        last = summaries[-1]
        first_rs = first.get("ruleshield_summary", {}) if isinstance(first.get("ruleshield_summary"), dict) else {}
        last_rs = last.get("ruleshield_summary", {}) if isinstance(last.get("ruleshield_summary"), dict) else {}
        first_stats = first_rs.get("stats_snapshot", {}) if isinstance(first_rs.get("stats_snapshot"), dict) else {}
        last_stats = last_rs.get("stats_snapshot", {}) if isinstance(last_rs.get("stats_snapshot"), dict) else {}
        first_shadow = first_rs.get("shadow_snapshot", {}) if isinstance(first_rs.get("shadow_snapshot"), dict) else {}
        last_shadow = last_rs.get("shadow_snapshot", {}) if isinstance(last_rs.get("shadow_snapshot"), dict) else {}

        # For runs with a single summary file, use the in-memory run baseline
        # captured at run start. Otherwise first/last summary delta is fine.
        if len(summaries) == 1:
            first_stats = {
                "rule_hits": int(run.baseline_rule_hits),
                "cache_hits": int(run.baseline_cache_hits),
                "cost_without": float(run.baseline_cost_without),
                "cost_with": float(run.baseline_cost_with),
            }
            first_shadow = {
                "total_comparisons": int(run.baseline_shadow_total),
            }

        rule_hits_delta = max(
            0.0,
            _safe_number(last_stats.get("rule_hits")) - _safe_number(first_stats.get("rule_hits")),
        )
        cache_hits_delta = max(
            0.0,
            _safe_number(last_stats.get("cache_hits")) - _safe_number(first_stats.get("cache_hits")),
        )
        shadow_comparisons_delta = max(
            0.0,
            _safe_number(last_shadow.get("total_comparisons")) - _safe_number(first_shadow.get("total_comparisons")),
        )
        cost_without_delta = max(
            0.0,
            _safe_number(last_stats.get("cost_without")) - _safe_number(first_stats.get("cost_without")),
        )
        cost_with_delta = max(
            0.0,
            _safe_number(last_stats.get("cost_with")) - _safe_number(first_stats.get("cost_with")),
        )

        # KISS: single-summary runs cannot reliably produce per-run snapshot deltas.
        # Use run-local request breakdown only and avoid leaking global totals.
        if len(summaries) == 1:
            rule_hits_delta = float(int(request_breakdown.get("rule", 0)))
            cache_hits_delta = float(int(request_breakdown.get("cache", 0)))
            shadow_comparisons_delta = float(int(request_breakdown.get("shadow", 0)))
            cost_without_delta = 0.0
            cost_with_delta = 0.0
        savings_delta = max(0.0, cost_without_delta - cost_with_delta)
        savings_pct = (savings_delta / cost_without_delta * 100.0) if cost_without_delta > 0 else 0.0

        return {
            "run_id": run_id,
            "status": run.status,
            "available": True,
            "run_dir": str(run_dir),
            "summary_files": [str(path) for path in summary_paths],
            "request_breakdown": request_breakdown,
            "triggered_rules": int(rule_hits_delta),
            "triggered_cache": int(cache_hits_delta),
            "would_trigger_shadow": int(shadow_comparisons_delta),
            "cost_without": round(cost_without_delta, 6),
            "cost_with": round(cost_with_delta, 6),
            "savings_usd": round(savings_delta, 6),
            "savings_pct": round(savings_pct, 2),
            "shadow_enabled": bool(last_shadow.get("enabled", False)),
            "confidence_up": confidence_up,
            "confidence_down": confidence_down,
            "recent_rule_events": recent_rule_events_sorted[:12],
            "source": "ruleshield-summary",
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/test-monitor/runs/%s/ruleshield: %s", run_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/test-monitor/start")
async def api_test_monitor_start(request: Request):
    """Start a test script from the monitored test directories."""
    try:
        body = await request.json()
        script_path = str(body.get("script_path", "")).strip()
        model_profile_id = str(body.get("model_profile_id", "")).strip() or None
        if not script_path:
            return JSONResponse(status_code=400, content={"error": "script_path is required"})

        discovered = _discover_test_scripts()
        script_by_path = {entry["path"]: entry for entry in discovered}
        entry = script_by_path.get(script_path)
        if entry is None:
            return JSONResponse(
                status_code=404,
                content={"error": "Script not found in monitored test directories"},
            )

        profile = _profile_by_id(model_profile_id)
        script_file = Path(script_path)
        resolved_script = _resolve_profile_script_path(script_file, profile)
        command = _build_test_command(resolved_script, entry["type"])
        run_id = f"run-{int(time.time())}-{random.randint(1000, 9999)}"

        async with _TEST_MONITOR_LOCK:
            last_run_id = _TEST_LAST_RUN_BY_SCRIPT.get(script_path)
            last_run = _TEST_RUNS.get(last_run_id) if last_run_id else None
            if last_run and last_run.status == "active":
                return JSONResponse(
                    status_code=409,
                    content={"error": "Script is already active", "run_id": last_run.run_id},
                )

        child_env = os.environ.copy()
        # Ensure Python children flush output line-by-line in monitor mode.
        child_env["PYTHONUNBUFFERED"] = "1"
        child_env.setdefault("PYTHONIOENCODING", "utf-8")
        # Profile-driven model/provider env for shell-based test suites.
        child_env["MODEL"] = profile["model"]
        child_env["FALLBACK_MODEL"] = profile["fallback_model"]
        child_env["RULESHIELD_TEST_PROVIDER"] = profile["provider"]
        child_env["RULESHIELD_TEST_PROFILE_ID"] = profile["id"]
        # Important: monitor-started scripts must not restart/kill the gateway
        # process they are running under.
        child_env["RULESHIELD_TEST_MONITOR"] = "1"
        child_env["AUTO_GATEWAY_RESTART"] = "0"

        stats_snapshot = await api_stats()
        stats_payload = stats_snapshot if isinstance(stats_snapshot, dict) else {}
        shadow_snapshot = await api_shadow(recent=None, rule_id=None)
        shadow_payload = shadow_snapshot if isinstance(shadow_snapshot, dict) else {}
        events_snapshot = await api_rule_events(limit=500)
        events_payload = events_snapshot if isinstance(events_snapshot, dict) else {}
        baseline_events = events_payload.get("events", []) if isinstance(events_payload.get("events"), list) else []
        baseline_conf_up, baseline_conf_down = _count_confidence_directions(baseline_events)

        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(Path.cwd()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=child_env,
        )

        run = TestRunState(
            run_id=run_id,
            script_path=script_path,
            command=command,
            process=proc,
            model_profile_id=profile["id"],
            model=profile["model"],
            provider_label=profile["provider_label"],
            baseline_shadow_total=int(_safe_number(shadow_payload.get("total_comparisons", 0))),
            baseline_rule_hits=int(_safe_number(stats_payload.get("rule_hits", 0))),
            baseline_cache_hits=int(_safe_number(stats_payload.get("cache_hits", 0))),
            baseline_cost_without=float(_safe_number(stats_payload.get("cost_without", 0.0))),
            baseline_cost_with=float(_safe_number(stats_payload.get("cost_with", 0.0))),
            baseline_confidence_up=baseline_conf_up,
            baseline_confidence_down=baseline_conf_down,
        )
        _append_test_event(run, "input", f"$ {' '.join(command)}")
        _append_test_event(
            run,
            "input",
            (
                f"[profile] id={profile['id']} provider={profile['provider_label']} "
                f"model={profile['model']} fallback={profile['fallback_model']}"
            ),
        )

        async with _TEST_MONITOR_LOCK:
            _TEST_RUNS[run_id] = run
            _TEST_LAST_RUN_BY_SCRIPT[script_path] = run_id

        asyncio.create_task(_stream_test_output(run))
        asyncio.create_task(_wait_test_run(run))

        return {
            "started": True,
            "run_id": run_id,
            "script_path": script_path,
            "resolved_script_path": str(resolved_script),
            "status": "active",
            "command": command,
            "model_profile_id": profile["id"],
            "model": profile["model"],
            "provider_label": profile["provider_label"],
        }
    except Exception as exc:
        logger.error("Failed to start test monitor run: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/test-monitor/stop")
async def api_test_monitor_stop(request: Request):
    """Stop/abort an active test run."""
    try:
        body = await request.json()
        run_id = str(body.get("run_id", "")).strip()
        if not run_id:
            return JSONResponse(status_code=400, content={"error": "run_id is required"})

        proc: asyncio.subprocess.Process | None = None
        async with _TEST_MONITOR_LOCK:
            run = _TEST_RUNS.get(run_id)
            if run is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Run '{run_id}' not found"},
                )
            if run.status != "active":
                return {"stopped": False, "run_id": run_id, "status": run.status}
            run.stop_requested = True
            _append_test_event(run, "input", "[stop requested]")
            proc = run.process

        if proc is not None and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                proc.kill()
                await proc.wait()

        async with _TEST_MONITOR_LOCK:
            run = _TEST_RUNS.get(run_id)
            status = run.status if run else "failed"
            return {
                "stopped": True,
                "run_id": run_id,
                "status": status,
            }
    except Exception as exc:
        logger.error("Failed to stop test monitor run: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


# ---------------------------------------------------------------------------
# Dashboard API endpoints
# ---------------------------------------------------------------------------


@app.get("/api/stats")
async def api_stats():
    """Aggregated statistics for the dashboard."""
    try:
        cache_stats = await cache_manager.get_stats()
        rule_stats = rule_engine.get_stats()

        total_requests = cache_stats.get("total_requests", 0)
        cache_hits = cache_stats.get("cache_hits", 0)
        rule_hits = cache_stats.get("rule_hits", 0)
        routed_calls = cache_stats.get("routed_calls", 0)
        llm_calls = cache_stats.get("llm_calls", 0)

        # Passthrough calls (Codex API requests forwarded directly)
        passthrough_calls = cache_stats.get("passthrough_calls", 0)

        # Backward-compatible fallback if routed_calls is unavailable.
        if routed_calls == 0 and total_requests > 0:
            routed_calls = max(
                0,
                total_requests - cache_hits - rule_hits - passthrough_calls - llm_calls,
            )

        # Cost data from the in-memory metrics dashboard (more accurate for
        # the current session) with fallback to DB savings.
        dashboard = metrics.dashboard
        cost_without = dashboard.total_cost_without
        cost_with = dashboard.total_cost_with

        # If the dashboard has no data yet, fall back to DB-based savings.
        if cost_without == 0 and cache_stats.get("total_savings", 0) > 0:
            cost_without = cache_stats["total_savings"]
            cost_with = 0.0

        savings_usd = cost_without - cost_with
        savings_pct = (savings_usd / cost_without * 100) if cost_without > 0 else 0.0

        uptime_seconds = time.monotonic() - _proxy_start_time

        return {
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "rule_hits": rule_hits,
            "routed_calls": routed_calls,
            "passthrough_calls": passthrough_calls,
            "llm_calls": llm_calls,
            "cost_without": round(cost_without, 4),
            "cost_with": round(cost_with, 4),
            "savings_usd": round(savings_usd, 4),
            "savings_pct": round(savings_pct, 1),
            "uptime_seconds": round(uptime_seconds),
        }
    except Exception as exc:
        logger.error("Failed to compute /api/stats: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/requests")
async def api_requests(limit: int = Query(default=20, ge=1, le=200)):
    """Recent requests for the dashboard."""
    try:
        recent = await cache_manager.get_recent_requests(limit=limit)

        requests_out = []
        for entry in recent:
            requests_out.append({
                "id": entry.get("id"),
                "prompt": (entry.get("prompt_text") or "")[:200],
                "resolution_type": entry.get("resolution_type", "unknown"),
                "model": entry.get("model", "unknown"),
                "cost": entry.get("cost_usd", 0.0),
                "tokens_in": entry.get("tokens_in", 0),
                "tokens_out": entry.get("tokens_out", 0),
                "latency_ms": entry.get("latency_ms", 0),
                "created_at": entry.get("created_at", ""),
            })

        return {"requests": requests_out}
    except Exception as exc:
        logger.error("Failed to fetch /api/requests: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/rules")
async def api_rules():
    """All rules and statistics for the dashboard."""
    try:
        stats = rule_engine.get_stats()

        rules_out = []
        for r in rule_engine.rules:
            # Compute confidence level based on the rule's confidence score.
            confidence = r.get("confidence", 1.0)
            if confidence >= 0.9:
                confidence_level = "CONFIRMED"
            elif confidence >= 0.7:
                confidence_level = "LIKELY"
            else:
                confidence_level = "POSSIBLE"

            deployment = r.get("deployment", "production")
            enabled = r.get("enabled", True)
            if not enabled:
                status = "paused"
            elif deployment == "candidate":
                status = "candidate"
            else:
                status = "live"

            rules_out.append({
                "id": r.get("id"),
                "name": r.get("name", r.get("id", "")),
                "hits": r.get("hit_count", 0),
                "shadow_hits": r.get("shadow_hit_count", 0),
                "confidence": r.get("confidence", 1.0),
                "confidence_level": confidence_level,
                "enabled": enabled,
                "deployment": deployment,
                "status": status,
                "pattern_count": len(r.get("patterns", [])),
            })

        return {
            "rules": rules_out,
            "total": stats.get("total_rules", len(rules_out)),
            "active": stats.get("active_rules", len(rules_out)),
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/rules: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/runtime-config")
async def api_runtime_config():
    """Minimal runtime config state for dashboard toggles."""
    try:
        return {
            "rules_enabled": bool(settings.rules_enabled),
            "shadow_mode": bool(settings.shadow_mode),
            "cache_enabled": bool(settings.cache_enabled),
            "router_enabled": bool(settings.router_enabled),
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/runtime-config: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/runtime-config")
async def api_update_runtime_config(request: Request):
    """Update minimal runtime config toggles and persist them locally."""
    global smart_router
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            return JSONResponse(status_code=400, content={"error": "JSON object required"})

        allowed_fields = ("rules_enabled", "shadow_mode", "cache_enabled", "router_enabled")
        applied: dict[str, bool] = {}
        ignored: list[str] = []

        for field in allowed_fields:
            if field not in payload:
                continue
            converted = _to_bool(payload.get(field))
            if converted is None:
                ignored.append(field)
                continue
            setattr(settings, field, converted)
            applied[field] = converted

        persisted = False
        if applied:
            persisted = _persist_runtime_settings(applied)
            # Apply Smart Router toggle live so monitor/test flows don't require a restart.
            if "router_enabled" in applied:
                if applied["router_enabled"]:
                    smart_router = SmartRouter(config=settings.router_config or None)
                else:
                    smart_router = None

        return {
            "applied": applied,
            "ignored": ignored,
            "persisted": persisted,
            "config": {
                "rules_enabled": bool(settings.rules_enabled),
                "shadow_mode": bool(settings.shadow_mode),
                "cache_enabled": bool(settings.cache_enabled),
                "router_enabled": bool(settings.router_enabled),
            },
        }
    except Exception as exc:
        logger.error("Failed to update /api/runtime-config: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/rules/{rule_id}/toggle")
async def api_toggle_rule(rule_id: str):
    """Toggle a rule's enabled state."""
    try:
        for rule in rule_engine.rules:
            if rule.get("id") == rule_id:
                new_state = not rule.get("enabled", True)
                rule["enabled"] = new_state
                rule_engine._dirty = True
                rule_engine._save_rules_to_disk()
                if feedback_manager is not None:
                    await feedback_manager.log_rule_event(
                        rule_id=rule_id,
                        event_type="rule_toggled",
                        direction="up" if new_state else "down",
                        old_confidence=float(rule.get("confidence", 1.0)),
                        new_confidence=float(rule.get("confidence", 1.0)),
                        delta=0.0,
                        details={"enabled": new_state},
                    )
                return {"id": rule_id, "enabled": new_state}

        return JSONResponse(
            status_code=404,
            content={"error": f"Rule '{rule_id}' not found"},
        )
    except Exception as exc:
        logger.error("Failed to toggle rule %s: %s", rule_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/rules/{rule_id}/response")
async def get_rule_response(rule_id: str):
    """Direct API access to a promoted rule's cached response.

    Returns the rule's response in OpenAI-compatible format without going
    through the full proxy pipeline.  Useful for replacing cron jobs:
    instead of sending a prompt through the LLM proxy, call this endpoint
    directly for a known pattern.
    """
    for rule in rule_engine.rules:
        if rule.get("id") == rule_id:
            content = rule.get("response", {}).get("content", "")
            return _wrap_openai_response(content, model="ruleshield-promoted")

    return JSONResponse(
        status_code=404,
        content={"error": f"Rule '{rule_id}' not found"},
    )


@app.get("/api/shadow")
async def api_shadow(
    recent: int | None = Query(default=None, ge=1, le=500),
    rule_id: str | None = Query(default=None),
):
    """Shadow mode comparison statistics for the dashboard."""
    # This endpoint is also called internally (without FastAPI request parsing).
    # Guard against receiving Query() objects as defaults in that code path.
    if not isinstance(recent, (int, type(None))):
        recent = None
    if not isinstance(rule_id, (str, type(None))):
        rule_id = None

    try:
        shadow_stats = await cache_manager.get_shadow_stats(limit=recent, rule_id=rule_id)
        tune_examples = await cache_manager.get_shadow_examples(
            limit=5,
            match_quality="poor",
            rule_id=rule_id,
        )

        by_rule = []
        for entry in shadow_stats.get("per_rule", []):
            avg_sim = entry.get("avg_similarity", 0.0)
            if avg_sim >= 0.8:
                quality = "good"
            elif avg_sim >= 0.4:
                quality = "partial"
            else:
                quality = "poor"

            by_rule.append({
                "rule_id": entry.get("rule_id", ""),
                "comparisons": entry.get("total", 0),
                "avg_similarity": avg_sim,
                "avg_similarity_pct": round(avg_sim * 100, 1),
                "good": entry.get("good", 0),
                "partial": entry.get("partial", 0),
                "poor": entry.get("poor", 0),
                "quality": quality,
            })

        entries = sorted(by_rule, key=lambda entry: entry["comparisons"], reverse=True)[:5]

        return {
            "enabled": settings.shadow_mode,
            "total_comparisons": shadow_stats.get("total_comparisons", 0),
            "avg_similarity": shadow_stats.get("avg_similarity", 0.0),
            "avg_similarity_pct": round(float(shadow_stats.get("avg_similarity", 0.0)) * 100, 1),
            "rules_ready": len(shadow_stats.get("ready_for_activation", [])),
            "recent": recent,
            "rule_id": rule_id,
            "entries": entries,
            "by_rule": by_rule,
            "tune_examples": tune_examples,
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/shadow: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/rule-events")
async def api_rule_events(limit: int = Query(default=100, ge=1, le=500)):
    """Recent rule-engine change events (confidence updates, toggles, lifecycle)."""
    try:
        if feedback_manager is None:
            return {"events": [], "limit": limit}
        events = await feedback_manager.get_recent_rule_events(limit=limit)
        return {"events": events, "limit": limit}
    except Exception as exc:
        logger.error("Failed to fetch /api/rule-events: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/feedback")
async def api_feedback(limit: int = Query(default=50, ge=1, le=300)):
    """Recent feedback entries and aggregated per-rule feedback stats."""
    try:
        if feedback_manager is None:
            return {"entries": [], "stats": [], "limit": limit}
        entries = await feedback_manager.get_recent_feedback(limit=limit)
        stats = await feedback_manager.get_feedback_stats()
        return {"entries": entries, "stats": stats, "limit": limit}
    except Exception as exc:
        logger.error("Failed to fetch /api/feedback: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/cron-profiles")
async def api_cron_profiles():
    """All cron optimization profiles and their runtime state."""
    try:
        result = list_cron_profiles()
        profiles = result.get("profiles", [])
        return {
            "profiles": profiles,
            "total": result.get("count", len(profiles)),
            "drafts": sum(1 for profile in profiles if profile.get("status") == "draft"),
            "active": sum(1 for profile in profiles if profile.get("status") == "active"),
            "ready": sum(1 for profile in profiles if profile.get("runtime_status") == "ready"),
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/cron-profiles: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/cron-profiles/{profile_id}")
async def api_cron_profile_detail(
    profile_id: str,
    history_limit: int = Query(default=8, ge=1, le=50),
):
    """Full cron profile document for dashboard detail views."""
    try:
        result = load_cron_profile(profile_id)
        profile = result.get("profile")
        if not profile:
            return JSONResponse(
                status_code=404,
                content={"error": result.get("message", f"Cron profile '{profile_id}' not found")},
            )
        return {
            "profile": profile,
            "path": result.get("path", ""),
            "history": get_profile_validation_history(
                cache_manager.db_path if hasattr(cache_manager, "db_path") else Path.home() / ".ruleshield" / "cache.db",
                profile_id,
                limit=history_limit,
            ),
            "execution_history": get_profile_execution_history(
                cache_manager.db_path if hasattr(cache_manager, "db_path") else Path.home() / ".ruleshield" / "cache.db",
                profile_id,
                limit=history_limit,
            ),
            "automation": build_automation_suggestion(
                profile,
                cwd=Path.cwd(),
            ) if profile.get("status") == "active" else None,
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/cron-profiles/%s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/activate")
async def api_activate_cron_profile(profile_id: str, request: Request):
    """Activate a validated cron profile."""
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        result = activate_cron_profile(
            profile_id,
            db_path=cache_manager.db_path if hasattr(cache_manager, "db_path") else Path.home() / ".ruleshield" / "cache.db",
            force=bool(body.get("force", False)),
        )
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Activation failed"), "summary": result.get("summary")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to activate cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/execute")
async def api_execute_cron_profile(profile_id: str, request: Request):
    """Execute an active cron profile with a payload."""
    try:
        body = await request.json()
        result = execute_active_cron_profile(
            profile_id,
            str(body.get("payload_text", "")),
            db_path=cache_manager.db_path if hasattr(cache_manager, "db_path") else Path.home() / ".ruleshield" / "cache.db",
            model=body.get("model"),
        )
        if not result.get("execution"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Execution failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to execute cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/shadow-run")
async def api_run_cron_profile_shadow(profile_id: str, request: Request):
    """Run shadow validation for a cron profile from payload or explicit output."""
    try:
        body = await request.json()
        result = run_cron_shadow(
            cache_manager.db_path if hasattr(cache_manager, "db_path") else Path.home() / ".ruleshield" / "cache.db",
            profile_id,
            optimized_response=str(body.get("optimized_response", "")),
            sample_limit=int(body.get("sample_limit", 3)),
            payload_text=str(body.get("payload_text", "")),
            model=body.get("model"),
        )
        if not result.get("count"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Shadow run failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to shadow-run cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/update")
async def api_update_cron_profile(profile_id: str, request: Request):
    """Update editable fields on a draft cron profile."""
    try:
        body = await request.json()
        result = update_draft_cron_profile(
            profile_id,
            updates={
                "name": body.get("name"),
                "prompt_template": body.get("prompt_template"),
                "model": body.get("model"),
            },
        )
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Profile update failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to update cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/archive")
async def api_archive_cron_profile(profile_id: str):
    """Archive a cron profile."""
    try:
        result = archive_cron_profile(profile_id)
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Archive failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to archive cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.delete("/api/cron-profiles/{profile_id}")
async def api_delete_cron_profile(profile_id: str):
    """Delete a cron profile."""
    try:
        result = delete_cron_profile(profile_id)
        if not result.get("deleted"):
            return JSONResponse(
                status_code=404,
                content={"error": result.get("message", "Delete failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to delete cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/restore")
async def api_restore_cron_profile(profile_id: str):
    """Restore an archived cron profile to draft."""
    try:
        result = restore_cron_profile(profile_id)
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Restore failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to restore cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.post("/api/cron-profiles/{profile_id}/duplicate")
async def api_duplicate_cron_profile(profile_id: str):
    """Duplicate a cron profile into a new draft."""
    try:
        result = duplicate_cron_profile(profile_id)
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={"error": result.get("message", "Duplicate failed")},
            )
        return result
    except Exception as exc:
        logger.error("Failed to duplicate cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/api/cron-profiles/{profile_id}/automation")
async def api_cron_profile_automation(profile_id: str):
    """Return a suggested Codex automation for an active cron profile."""
    try:
        result = load_cron_profile(profile_id)
        profile = result.get("profile")
        if not profile:
            return JSONResponse(
                status_code=404,
                content={"error": result.get("message", "Cron profile not found")},
            )
        if profile.get("status") != "active":
            return JSONResponse(
                status_code=400,
                content={"error": "Only active cron profiles can generate automation suggestions."},
            )
        return build_automation_suggestion(profile, cwd=Path.cwd())
    except Exception as exc:
        logger.error("Failed to build automation suggestion for cron profile %s: %s", profile_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@app.get("/v1/models")
async def list_models(request: Request):
    """Proxy the models list from the upstream provider."""
    upstream_url = f"{settings.provider_url.rstrip('/')}/v1/models"
    headers = _forward_headers(request)

    try:
        if http_client is None:
            return JSONResponse(status_code=503, content={"error": "Proxy not initialized"})
        resp = await http_client.get(upstream_url, headers=headers)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type="application/json",
            headers={"X-RuleShield-Resolution": "routed"},
        )
    except Exception as exc:
        logger.error("Failed to list models from upstream: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": "Upstream error", "type": "proxy_error"}},
        )


# ---------------------------------------------------------------------------
# Chat completions
# ---------------------------------------------------------------------------


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Handle OpenAI-compatible chat completion requests."""
    return await _handle_completion(request, endpoint="/v1/chat/completions")


@app.post("/v1/completions")
async def completions(request: Request):
    """Handle legacy completion requests."""
    return await _handle_completion(request, endpoint="/v1/completions")


# ---------------------------------------------------------------------------
# Transparent proxy for all other /v1/* endpoints (e.g. /v1/responses)
# ---------------------------------------------------------------------------


@app.api_route("/responses", methods=["POST"])
@app.api_route("/responses/{path:path}", methods=["GET", "POST", "DELETE"])
@app.api_route("/chat/completions", methods=["POST"])
async def proxy_codex_passthrough(request: Request, path: str = ""):
    """Transparent proxy for Codex-style endpoints without /v1/ prefix.

    Codex API uses {base_url}/responses instead of {base_url}/v1/responses.
    This catches those requests and forwards them to the upstream provider.
    """
    # Reconstruct the full path from the request
    full_path = request.url.path
    endpoint = full_path
    headers = _forward_headers(request)
    body_bytes = await request.body()
    method = request.method.upper()

    t_start = time.monotonic()
    model = "unknown"
    prompt_text = ""
    prompt_hash = ""
    codex_prompt = ""
    raw_user_msg = ""
    codex_messages: list[dict[str, Any]] | None = None
    shadow_rule_hit: dict[str, Any] | None = None
    if body_bytes:
        try:
            _bj = json.loads(body_bytes)
            model = _bj.get("model", "unknown")
            msgs = _bj.get("messages", _bj.get("input", []))
            if isinstance(msgs, list):
                for m in msgs:
                    if isinstance(m, dict) and m.get("role") == "user":
                        prompt_text = str(m.get("content", ""))[:200]
            elif isinstance(msgs, str):
                prompt_text = msgs[:200]
        except (json.JSONDecodeError, AttributeError):
            pass

    provider_url, headers, provider_error = _resolve_upstream_for_model(
        model=model,
        request=request,
        headers=headers,
    )
    if provider_error:
        return JSONResponse(
            status_code=400,
            content={"detail": provider_error},
        )
    upstream_url = f"{provider_url.rstrip('/')}{endpoint}"

    logger.info("Codex passthrough %s %s -> %s (model=%s)", method, endpoint, upstream_url, model)

    if http_client is None:
        return JSONResponse(status_code=503, content={"error": "Proxy not initialized"})
    try:
        headers["Content-Type"] = request.headers.get("content-type", "application/json")

        # Codex Responses API always streams
        is_stream = True
        if body_bytes:
            try:
                _bj = json.loads(body_bytes)
                is_stream = _bj.get("stream", True)
            except (json.JSONDecodeError, AttributeError):
                pass

        # --- Codex Cache/Rules check (requires codex_adapter) ---------------
        logger.debug("Codex cache/rules check: adapter=%s, body=%d bytes, cache=%s, rules=%s",
                     _HAS_CODEX_ADAPTER, len(body_bytes) if body_bytes else 0,
                     settings.cache_enabled, settings.rules_enabled)
        if _HAS_CODEX_ADAPTER and body_bytes and (settings.cache_enabled or settings.rules_enabled):
            try:
                body_json = json.loads(body_bytes)
                codex_prompt = extract_prompt_from_codex(body_json)  # includes [inst:] prefix
                codex_messages = extract_messages_from_codex(body_json)

                # Extract the RAW user message (without instructions prefix)
                # for rule matching -- rules should match "hello" not "[inst:...] hello"
                raw_input = body_json.get("input")
                if isinstance(raw_input, list):
                    raw_user_msg = ""
                    for item in reversed(raw_input):
                        if isinstance(item, dict) and item.get("role") == "user":
                            content = item.get("content", "")
                            raw_user_msg = content if isinstance(content, str) else str(content)
                            break
                elif isinstance(raw_input, str):
                    raw_user_msg = raw_input.strip()
                else:
                    raw_user_msg = ""

                logger.info("Codex prompt: full='%s', user_msg='%s'",
                           codex_prompt[:60] if codex_prompt else "(empty)",
                           raw_user_msg[:60] if raw_user_msg else "(empty)")

                prompt_hash = extractor.hash_prompt(codex_prompt)

                # Update prompt_text for downstream logging
                if codex_prompt:
                    prompt_text = codex_prompt[:200]

                # 1. Cache check (uses full prompt with instructions for key specificity)
                if settings.cache_enabled and codex_prompt:
                    cached = await cache_manager.check(prompt_hash, codex_prompt)
                    if cached is not None:
                        latency_ms = (time.monotonic() - t_start) * 1000
                        logger.info("Codex cache hit for: %s", codex_prompt[:50])
                        estimated_cost = _estimate_cost(cached.get("response", {}))
                        await _record_metrics(
                            model, "cache", cached.get("response", {}), latency_ms,
                            prompt_hash=prompt_hash, prompt_text=codex_prompt,
                            estimated_saving=estimated_cost,
                        )
                        # Return in Codex format (streaming or non-streaming)
                        if is_stream:
                            content = _extract_codex_content(cached.get("response", {}))
                            events = wrap_codex_streaming_response(content, model="ruleshield-cache")

                            async def cache_stream():
                                for event in events:
                                    yield event

                            return StreamingResponse(
                                cache_stream(),
                                media_type="text/event-stream",
                                headers={"X-RuleShield-Resolution": "cache"},
                            )
                        else:
                            content = _extract_codex_content(cached.get("response", {}))
                            return JSONResponse(
                                content=wrap_codex_response(content, model="ruleshield-cache"),
                                headers={"X-RuleShield-Resolution": "cache"},
                            )

                # 2. Rule check (uses raw user message, not full prompt with instructions)
                rule_prompt = raw_user_msg or codex_prompt
                shadow_confidence_floor = (
                    settings.shadow_test_confidence_floor
                    if settings.shadow_mode and settings.shadow_test_confidence_floor > 0.0
                    else None
                )
                if settings.rules_enabled and rule_prompt:
                    rule_hit = await rule_engine.async_match(
                        rule_prompt,
                        messages=codex_messages,
                        model=model,
                        confidence_floor=shadow_confidence_floor,
                    )
                    if rule_hit is not None:
                        if settings.shadow_mode:
                            shadow_rule_hit = rule_hit
                            logger.info(
                                "Codex shadow mode: rule '%s' matched but forwarding upstream",
                                rule_hit.get("rule_name", rule_hit.get("rule_id", "unknown")),
                            )
                        else:
                            latency_ms = (time.monotonic() - t_start) * 1000
                            logger.info(
                                "Codex rule hit: %s -> %s",
                                codex_prompt[:50],
                                rule_hit.get("rule_name", rule_hit.get("rule_id", "unknown")),
                            )
                            raw_response = rule_hit.get("response", {})
                            content = raw_response.get("content", str(raw_response))
                            estimated_cost = 0.001
                            await _record_metrics(
                                model, "rule", raw_response, latency_ms,
                                prompt_hash=prompt_hash, prompt_text=codex_prompt,
                                estimated_saving=estimated_cost,
                            )
                            if is_stream:
                                events = wrap_codex_streaming_response(content, model="ruleshield-rule")

                                async def rule_stream():
                                    for event in events:
                                        yield event

                                return StreamingResponse(
                                    rule_stream(),
                                    media_type="text/event-stream",
                                    headers={"X-RuleShield-Resolution": "rule"},
                                )
                            else:
                                return JSONResponse(
                                    content=wrap_codex_response(content, model="ruleshield-rule"),
                                    headers={"X-RuleShield-Resolution": "rule"},
                                )
                    elif settings.shadow_mode:
                        candidate_hit = await rule_engine.async_match_candidates(
                            rule_prompt,
                            messages=codex_messages,
                            model=model,
                            confidence_floor=shadow_confidence_floor,
                        )
                        if candidate_hit is not None:
                            shadow_rule_hit = candidate_hit
                            logger.info(
                                "Codex shadow mode: candidate rule '%s' matched for comparison",
                                candidate_hit.get("rule_id", "unknown"),
                            )
            except Exception as exc:
                logger.warning("Codex cache/rule check failed (proceeding to upstream): %s", exc)

        # --- End Codex Cache/Rules check ------------------------------------

        if is_stream:
            # Shared state populated by the stream generator, logged after
            # the response body has been fully sent to the client.
            stream_state: dict[str, Any] = {
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
                "content_parts": [],
                "fallback_texts": [],
                "completed": False,
            }

            async def stream_and_track():
                """Forward every SSE chunk immediately while parsing events.

                Extracts token usage from the final ``response.completed``
                event so we can log cost/latency without adding any
                buffering delay to the client stream.
                """
                async with http_client.stream(
                    method, upstream_url, headers=headers, content=body_bytes
                ) as resp:
                    async for line in resp.aiter_lines():
                        # Forward every line to the client immediately.
                        # SSE protocol: each line followed by newline;
                        # blank lines delimit events.
                        yield f"{line}\n"

                        # Parse only data lines for metrics extraction.
                        if not line.startswith("data: "):
                            continue
                        raw_json = line[6:]
                        if raw_json.strip() == "[DONE]":
                            continue
                        try:
                            event_data = json.loads(raw_json)
                        except (json.JSONDecodeError, ValueError):
                            continue

                        event_type = event_data.get("type", "")

                        if event_type == "response.output_text.delta":
                            delta = event_data.get("delta", "")
                            if delta:
                                stream_state["content_parts"].append(delta)
                        else:
                            fallback_text = _extract_codex_event_text(event_data)
                            if fallback_text:
                                stream_state["fallback_texts"].append(fallback_text)

                        if event_type == "response.completed":
                            response_obj = event_data.get("response", {})
                            usage = response_obj.get("usage", {})
                            stream_state["tokens_in"] = usage.get("input_tokens", 0)
                            stream_state["tokens_out"] = usage.get("output_tokens", 0)
                            stream_state["cost"] = _compute_codex_cost(
                                model,
                                stream_state["tokens_in"],
                                stream_state["tokens_out"],
                            )
                            stream_state["completed"] = True

            async def _log_after_stream():
                """Background task to persist metrics after the stream ends."""
                try:
                    latency_ms = (time.monotonic() - t_start) * 1000
                    tokens_in = stream_state["tokens_in"]
                    tokens_out = stream_state["tokens_out"]
                    cost = stream_state["cost"]
                    content = _select_codex_stream_text(stream_state)

                    logger.info(
                        "Codex stream completed: %d in / %d out tokens, $%.6f, %.0fms",
                        tokens_in, tokens_out, cost, latency_ms,
                    )

                    # Compute prompt hash for cache storage
                    codex_ph = ""
                    if _HAS_CODEX_ADAPTER and prompt_text:
                        codex_ph = extractor.hash_prompt(prompt_text)

                    await cache_manager.log_request(
                        prompt_hash=codex_ph,
                        prompt_text=(
                            f"[codex] {prompt_text}" if prompt_text else "[codex]"
                        ),
                        response={"content": content[:500]},
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost=cost,
                        resolution_type="passthrough",
                        latency_ms=int(latency_ms),
                    )

                    # Store in cache for future hits
                    if settings.cache_enabled and content and codex_ph:
                        try:
                            await cache_manager.store(
                                prompt_hash=codex_ph,
                                prompt_text=prompt_text,
                                response={"content": content},
                                model=model,
                                tokens_in=tokens_in,
                                tokens_out=tokens_out,
                                cost=cost,
                            )
                        except Exception as store_exc:
                            logger.warning("Codex cache store failed: %s", store_exc)

                    if shadow_rule_hit is not None and content:
                        try:
                            comparison = await _shadow_compare(
                                shadow_rule_hit,
                                _wrap_openai_response(content, model=model),
                                raw_user_msg or codex_prompt or prompt_text,
                            )
                            await cache_manager.log_shadow(
                                rule_id=comparison["rule_id"],
                                prompt_text=(raw_user_msg or codex_prompt or prompt_text)[:2000],
                                rule_response=comparison["rule_response"],
                                llm_response=comparison["llm_response"],
                                similarity=comparison["similarity"],
                                length_ratio=comparison["length_ratio"],
                                match_quality=comparison["match_quality"],
                            )
                            await _apply_shadow_feedback(
                                comparison, raw_user_msg or codex_prompt or prompt_text
                            )
                            logger.info(
                                "Codex shadow comparison (stream): rule=%s similarity=%.3f quality=%s",
                                comparison["rule_id"],
                                comparison["similarity"],
                                comparison["match_quality"],
                            )
                        except Exception as shadow_exc:
                            logger.warning("Codex streaming shadow comparison failed: %s", shadow_exc)
                except Exception as log_exc:
                    logger.error("Failed to log Codex stream metrics: %s", log_exc)

            stream_headers = {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-RuleShield-Resolution": "passthrough",
            }
            if shadow_rule_hit is not None:
                stream_headers["X-RuleShield-Shadow"] = shadow_rule_hit.get("rule_id", "")

            response = StreamingResponse(
                stream_and_track(),
                media_type="text/event-stream",
                headers=stream_headers,
                background=BackgroundTask(_log_after_stream),
            )
            return response
        else:
            resp = await http_client.request(
                method, upstream_url, headers=headers, content=body_bytes
            )
            latency_ms = (time.monotonic() - t_start) * 1000

            # Extract usage from non-streaming Codex response body
            tokens_in = 0
            tokens_out = 0
            cost = 0.0
            resp_json: dict = {}
            try:
                resp_json = resp.json()
                usage = resp_json.get("usage", {})
                tokens_in = usage.get("input_tokens", 0)
                tokens_out = usage.get("output_tokens", 0)
                cost = _compute_codex_cost(model, tokens_in, tokens_out)
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass

            logger.info(
                "Codex passthrough completed: %d in %.0fms, %d/%d tokens, $%.6f",
                resp.status_code, latency_ms, tokens_in, tokens_out, cost,
            )

            # Compute prompt hash for cache storage
            codex_ph = ""
            if _HAS_CODEX_ADAPTER and prompt_text:
                codex_ph = extractor.hash_prompt(prompt_text)

            try:
                await cache_manager.log_request(
                    prompt_hash=codex_ph,
                    prompt_text=f"[codex] {prompt_text}" if prompt_text else f"[codex] {endpoint}",
                    response=resp_json,
                    model=model,
                    tokens_in=tokens_in, tokens_out=tokens_out, cost=cost,
                    resolution_type="passthrough", latency_ms=int(latency_ms),
                )
            except Exception:
                pass

            # Store in cache for future hits
            if settings.cache_enabled and resp.status_code == 200 and codex_ph and resp_json:
                try:
                    await cache_manager.store(
                        prompt_hash=codex_ph,
                        prompt_text=prompt_text,
                        response=resp_json,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost=cost,
                    )
                except Exception as store_exc:
                    logger.warning("Codex cache store failed: %s", store_exc)

            response_headers = {"X-RuleShield-Resolution": "passthrough"}
            if shadow_rule_hit is not None:
                try:
                    content = _extract_codex_content(resp_json)
                    comparison = await _shadow_compare(
                        shadow_rule_hit,
                        _wrap_openai_response(content, model=model),
                        raw_user_msg or codex_prompt or prompt_text,
                    )
                    await cache_manager.log_shadow(
                        rule_id=comparison["rule_id"],
                        prompt_text=(raw_user_msg or codex_prompt or prompt_text)[:2000],
                        rule_response=comparison["rule_response"],
                        llm_response=comparison["llm_response"],
                        similarity=comparison["similarity"],
                        length_ratio=comparison["length_ratio"],
                        match_quality=comparison["match_quality"],
                    )
                    await _apply_shadow_feedback(
                        comparison, raw_user_msg or codex_prompt or prompt_text
                    )
                    response_headers["X-RuleShield-Shadow"] = comparison["rule_id"]
                    logger.info(
                        "Codex shadow comparison: rule=%s similarity=%.3f quality=%s",
                        comparison["rule_id"],
                        comparison["similarity"],
                        comparison["match_quality"],
                    )
                except Exception as shadow_exc:
                    logger.warning("Codex shadow comparison failed: %s", shadow_exc)

            return Response(
                content=resp.content, status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
                headers=response_headers,
            )
    except Exception as exc:
        logger.error("Codex passthrough error for %s: %s", endpoint, exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": "Upstream error", "type": "proxy_error"}},
        )


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_passthrough(request: Request, path: str):
    """Transparent proxy for any /v1/* endpoint not explicitly handled.

    This catches the OpenAI Responses API (/v1/responses), model listing,
    embeddings, and any other endpoint the upstream supports. Requests are
    forwarded as-is with full header passthrough. Streaming is supported.
    """
    endpoint = f"/v1/{path}"
    headers = _forward_headers(request)

    body_bytes = await request.body()
    method = request.method.upper()

    # Log for visibility
    t_start = time.monotonic()
    model = "unknown"
    prompt_text = ""
    if body_bytes:
        try:
            _bj = json.loads(body_bytes)
            model = _bj.get("model", "unknown")
            # Extract prompt from messages or input field
            msgs = _bj.get("messages", _bj.get("input", []))
            if isinstance(msgs, list):
                for m in msgs:
                    if isinstance(m, dict) and m.get("role") == "user":
                        prompt_text = str(m.get("content", ""))[:200]
            elif isinstance(msgs, str):
                prompt_text = msgs[:200]
        except (json.JSONDecodeError, AttributeError):
            pass

    provider_url, headers, provider_error = _resolve_upstream_for_model(
        model=model,
        request=request,
        headers=headers,
    )
    if provider_error:
        return JSONResponse(status_code=400, content={"detail": provider_error})
    upstream_url = f"{provider_url.rstrip('/')}{endpoint}"
    logger.info("Passthrough %s %s -> %s (model=%s)", method, endpoint, upstream_url, model)

    if http_client is None:
        return JSONResponse(status_code=503, content={"error": "Proxy not initialized"})
    try:
        if method == "GET":
            resp = await http_client.get(upstream_url, headers=headers)
        else:
            headers["Content-Type"] = request.headers.get("content-type", "application/json")
            # Check if this is a streaming request
            is_stream = False
            if body_bytes:
                try:
                    body_json = json.loads(body_bytes)
                    is_stream = body_json.get("stream", False)
                    # Translate model name if present
                    if "model" in body_json:
                        body_json["model"] = _translate_model_name(
                            body_json["model"], provider_url
                        )
                        body_bytes = json.dumps(body_json).encode()
                except (json.JSONDecodeError, AttributeError):
                    pass

            if is_stream:
                # Stream the response
                async def stream_generator():
                    async with http_client.stream(
                        method, upstream_url, headers=headers, content=body_bytes
                    ) as resp:
                        async for chunk in resp.aiter_bytes():
                            yield chunk

                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-RuleShield-Resolution": "passthrough",
                    },
                )
            else:
                resp = await http_client.request(
                    method, upstream_url, headers=headers, content=body_bytes
                )

        latency_ms = (time.monotonic() - t_start) * 1000
        logger.info("Passthrough %s completed: %d in %.0fms (model=%s)",
                     endpoint, resp.status_code, latency_ms, model)

        # Best-effort logging to request_log for stats visibility
        try:
            await cache_manager.log_request(
                prompt_hash="",
                prompt_text=f"[passthrough] {prompt_text}" if prompt_text else f"[passthrough] {endpoint}",
                response={},
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost=0.0,
                resolution_type="passthrough",
                latency_ms=int(latency_ms),
            )
        except Exception:
            pass

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
            headers={"X-RuleShield-Resolution": "passthrough"},
        )
    except Exception as exc:
        logger.error("Passthrough error for %s: %s", endpoint, exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": "Upstream error", "type": "proxy_error"}},
        )


# ---------------------------------------------------------------------------
# Core proxy logic
# ---------------------------------------------------------------------------


async def _handle_completion(request: Request, endpoint: str) -> Response:
    """Shared handler for both /v1/chat/completions and /v1/completions."""
    t_start = time.monotonic()

    # --- Parse body --------------------------------------------------------
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "Invalid JSON body", "type": "invalid_request_error"}},
        )

    model = body.get("model", "unknown")
    stream = body.get("stream", False)

    # Extract a single text representation of the prompt for cache/rules.
    prompt_text = _extract_prompt_text(body, endpoint)
    prompt_hash = extractor.hash_prompt(prompt_text)

    # --- 1. Cache check ----------------------------------------------------
    resolution = "llm"  # default: forwarded to the real LLM

    if settings.cache_enabled:
        try:
            cached = await cache_manager.check(prompt_hash, prompt_text)
            if cached is not None:
                resolution = "cache"
                latency_ms = (time.monotonic() - t_start) * 1000
                # Estimate what this would have cost without cache
                estimated_cost = _estimate_cost(cached.get("response", {}))
                await _record_metrics(
                    model, resolution, cached.get("response", {}), latency_ms,
                    prompt_hash=prompt_hash, prompt_text=prompt_text,
                    estimated_saving=estimated_cost,
                )
                return JSONResponse(
                    content=cached["response"],
                    headers={"X-RuleShield-Resolution": resolution},
                )
        except Exception as exc:
            logger.warning("Cache check failed (proceeding without cache): %s", exc)

    # --- 1.5 Template check --------------------------------------------------
    if settings.rules_enabled and prompt_text:
        try:
            from ruleshield.template_optimizer import TemplateOptimizer
            if not hasattr(_handle_completion, '_tpl_optimizer'):
                _handle_completion._tpl_optimizer = TemplateOptimizer()
                _handle_completion._tpl_optimizer.load_templates()

            tpl_result = _handle_completion._tpl_optimizer.match(prompt_text)
            if tpl_result:
                tpl, variables, cached_response = tpl_result
                if cached_response:
                    # Known template + known variables = instant response
                    resolution = "template"
                    latency_ms = (time.monotonic() - t_start) * 1000
                    resp_payload = _wrap_openai_response(
                        cached_response, model="ruleshield-template"
                    )
                    await _record_metrics(
                        model, resolution, resp_payload, latency_ms,
                        prompt_hash=prompt_hash, prompt_text=prompt_text,
                        estimated_saving=0.001,
                    )
                    return JSONResponse(
                        content=resp_payload,
                        headers={"X-RuleShield-Resolution": "template"},
                    )
                else:
                    logger.info(
                        "Template '%s' matched with new variables %s -- forwarding to LLM",
                        tpl.id, variables,
                    )
        except Exception as exc:
            logger.debug("Template check skipped: %s", exc)

    # --- 2. Rule check -----------------------------------------------------
    shadow_rule_hit: dict[str, Any] | None = None  # stored for shadow mode

    if settings.rules_enabled:
        shadow_confidence_floor = (
            settings.shadow_test_confidence_floor
            if settings.shadow_mode and settings.shadow_test_confidence_floor > 0.0
            else None
        )
        try:
            rule_hit = await rule_engine.async_match(
                prompt_text,
                messages=body.get("messages"),
                model=model,
                confidence_floor=shadow_confidence_floor,
            )
            if rule_hit is not None:
                if settings.shadow_mode:
                    # Shadow mode: do NOT return the rule response.
                    # Store the hit and let execution continue to the upstream LLM.
                    shadow_rule_hit = rule_hit
                    logger.info(
                        "Shadow mode: rule '%s' matched but forwarding to LLM for comparison",
                        rule_hit.get("rule_id", rule_hit.get("id", "unknown")),
                    )
                else:
                    resolution = "rule"
                    latency_ms = (time.monotonic() - t_start) * 1000
                    raw_response = rule_hit.get("response", {})
                    # Estimate saving: a typical short exchange costs ~$0.001
                    estimated_cost = 0.001
                    # Wrap in OpenAI-compatible format so LiteLLM/Hermes can parse it
                    resp_payload = _wrap_openai_response(
                        content=raw_response.get("content", str(raw_response)),
                        model=raw_response.get("model", "ruleshield-rule"),
                    )
                    await _record_metrics(
                        model, resolution, resp_payload, latency_ms,
                        prompt_hash=prompt_hash, prompt_text=prompt_text,
                        estimated_saving=estimated_cost,
                    )
                    return JSONResponse(
                        content=resp_payload,
                        headers={"X-RuleShield-Resolution": resolution},
                    )
            elif settings.shadow_mode:
                candidate_hit = await rule_engine.async_match_candidates(
                    prompt_text,
                    messages=body.get("messages"),
                    model=model,
                    confidence_floor=shadow_confidence_floor,
                )
                if candidate_hit is not None:
                    shadow_rule_hit = candidate_hit
                    logger.info(
                        "Shadow mode: candidate rule '%s' matched for comparison",
                        candidate_hit.get("rule_id", "unknown"),
                    )
        except Exception as exc:
            logger.warning("Rule check failed (proceeding without rules): %s", exc)

    # --- 2.5 Prompt Trimming (optional) ------------------------------------
    # If the full prompt didn't match any rule, try trimming:
    # split into sub-tasks, handle known parts via rules, send only unknown to LLM
    if (
        settings.prompt_trimming_enabled
        and settings.rules_enabled
        and prompt_text
        and len(prompt_text) > 50
        and resolution == "llm"  # only trim when no cache/rule hit already
    ):
        try:
            from ruleshield.hermes_bridge import trim_prompt

            # Get all rule matches for sub-parts of the prompt.
            # Each match needs "patterns" (list[str]) for _find_matching_rule,
            # plus "answer" and "rule_id" for the known_parts output.
            rule_matches = []
            for rule in rule_engine.rules:
                if not rule.get("enabled", True):
                    continue
                # Collect matching pattern values for this rule
                matching_values = []
                for pattern in rule.get("patterns", []):
                    if pattern.get("type") == "contains":
                        if pattern["value"].lower() in prompt_text.lower():
                            matching_values.append(pattern["value"])
                if matching_values:
                    rule_matches.append({
                        "patterns": matching_values,
                        "answer": rule.get("response", {}).get("content", ""),
                        "rule_id": rule["id"],
                    })

            if rule_matches:
                trimmed, known_parts = trim_prompt(prompt_text, rule_matches)

                if trimmed and len(trimmed) < len(prompt_text) * 0.8:
                    # Significant trimming achieved (>20% reduction)
                    logger.info(
                        "Prompt trimmed: %d -> %d chars (%d parts handled by rules)",
                        len(prompt_text), len(trimmed), len(known_parts),
                    )

                    # Modify the body to use the trimmed prompt
                    # Prepend context from known parts
                    context = "Context (already known):\n"
                    for kp in known_parts:
                        context += f"- {kp['question']}: {kp['answer']}\n"
                    context += f"\nPlease answer ONLY this remaining question:\n{trimmed}"

                    # Update the last user message in the body
                    if "messages" in body:
                        for msg in reversed(body["messages"]):
                            if msg.get("role") == "user":
                                msg["content"] = context
                                break

                    # Update prompt_text and hash for logging
                    prompt_text = context
                    prompt_hash = extractor.hash_prompt(prompt_text)

                    # Track the trimming in metrics
                    await _record_metrics(
                        model, "trimmed", {}, 0,
                        prompt_hash=prompt_hash, prompt_text=f"[trimmed] {trimmed[:100]}",
                        estimated_saving=0.0,
                    )
        except Exception as exc:
            logger.debug("Prompt trimming skipped: %s", exc)

    # --- 3. Smart Router -- swap model if complexity is low ----------------
    route_decision = None
    if smart_router is not None:
        try:
            route_decision = smart_router.route(
                prompt_text=prompt_text,
                messages=body.get("messages"),
                original_model=model,
                provider_url=settings.provider_url,
            )
            if route_decision["routed"]:
                resolution = "routed"
                body["model"] = route_decision["model"]
                logger.info(
                    "Router: %s -> %s (score=%d, tier=%s)",
                    model, route_decision["model"],
                    route_decision["complexity_score"],
                    route_decision["tier"],
                )
        except Exception as exc:
            logger.warning("Router failed (proceeding with original model): %s", exc)

    # --- 3b. Translate model name for upstream provider --------------------
    # Some providers (e.g. Nous/OpenRouter) need full model IDs like
    # "anthropic/claude-4.6-sonnet-20260217" instead of short names like
    # "claude-sonnet-4-6". Translate before forwarding.
    headers = _forward_headers(request)
    selected_provider_url, headers, provider_error = _resolve_upstream_for_model(
        model=body.get("model", model),
        request=request,
        headers=headers,
    )
    if provider_error:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": provider_error, "type": "provider_config_error"}},
        )

    # OpenRouter-compatible chat schema for Codex-style Hermes payloads.
    if endpoint == "/v1/chat/completions":
        body = _normalize_chat_payload_for_upstream(body)
        if "openrouter.ai/api" in selected_provider_url:
            body = _normalize_tools_for_openrouter_chat(body)
        prompt_text = _extract_prompt_text(body, endpoint)
        prompt_hash = extractor.hash_prompt(prompt_text)

    body["model"] = _translate_model_name(body.get("model", model), selected_provider_url)

    # --- 4. Forward to upstream LLM ----------------------------------------
    upstream_url = f"{selected_provider_url.rstrip('/')}{endpoint}"
    headers["Content-Type"] = "application/json"

    if stream:
        return await _stream_upstream(
            upstream_url,
            headers,
            body,
            model,
            prompt_hash,
            prompt_text,
            t_start,
            route_decision=route_decision,
            shadow_rule_hit=shadow_rule_hit,
        )
    else:
        return await _forward_upstream(
            upstream_url, headers, body, model, prompt_hash, prompt_text, t_start,
            route_decision=route_decision, shadow_rule_hit=shadow_rule_hit,
        )


# ---------------------------------------------------------------------------
# Retry logic for upstream requests
# ---------------------------------------------------------------------------

RETRY_STATUS_CODES = {429, 500, 502, 503, 529}  # rate limit, server errors, overloaded


async def _retry_request(
    method: str,
    url: str,
    headers: dict,
    body: dict | bytes | None = None,
    max_retries: int | None = None,
) -> httpx.Response:
    """Execute an HTTP request with exponential backoff retry.

    Retries on: 429 (rate limit), 500, 502, 503, 529 (overloaded).
    Does NOT retry on: 400 (bad request), 401 (auth), 404 (not found).

    Backoff: 1s, 2s, 4s with jitter.
    """
    if max_retries is None:
        max_retries = settings.max_retries if settings else 3
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if isinstance(body, bytes):
                resp = await http_client.request(method, url, headers=headers, content=body)
            elif body is not None:
                resp = await http_client.request(method, url, headers=headers, json=body)
            else:
                resp = await http_client.request(method, url, headers=headers)

            if resp.status_code not in RETRY_STATUS_CODES:
                return resp

            if attempt < max_retries:
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Upstream returned %d, retrying in %.1fs (attempt %d/%d)",
                    resp.status_code, wait, attempt + 1, max_retries,
                )
                await asyncio.sleep(wait)
            else:
                return resp  # return the error response on final attempt

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Upstream connection error: %s, retrying in %.1fs (attempt %d/%d)",
                    exc, wait, attempt + 1, max_retries,
                )
                await asyncio.sleep(wait)
            else:
                raise

    raise last_exc or Exception("Retry exhausted")


# ---------------------------------------------------------------------------
# Non-streaming forward
# ---------------------------------------------------------------------------


async def _forward_upstream(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    model: str,
    prompt_hash: str,
    prompt_text: str,
    t_start: float,
    route_decision: dict[str, Any] | None = None,
    shadow_rule_hit: dict[str, Any] | None = None,
) -> Response:
    """Forward request and return the full JSON response."""
    if http_client is None:
        return JSONResponse(status_code=503, content={"error": "Proxy not initialized"})

    try:
        resp = await _retry_request("POST", url, headers, body=body)
    except Exception as exc:
        logger.error("Upstream request failed after retries: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": "Upstream error", "type": "proxy_error"}},
        )

    latency_ms = (time.monotonic() - t_start) * 1000
    resolution = "routed" if (route_decision and route_decision.get("routed")) else "llm"

    # Attempt to parse response for metrics + caching.
    resp_body: dict[str, Any] = {}
    try:
        resp_body = resp.json()
    except Exception:
        pass

    # Record metrics.
    await _record_metrics(model, resolution, resp_body, latency_ms,
                          prompt_hash=prompt_hash, prompt_text=prompt_text,
                          route_decision=route_decision)

    # Store in cache (best-effort).
    if settings.cache_enabled and resp.status_code == 200 and resp_body:
        try:
            usage = resp_body.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            cost = (tokens_in * 0.000005) + (tokens_out * 0.000015)
            await cache_manager.store(
                prompt_hash=prompt_hash,
                prompt_text=prompt_text,
                response=resp_body,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
            )
        except Exception as exc:
            logger.warning("Cache store failed: %s", exc)

    # --- Shadow mode comparison -------------------------------------------
    resolution_headers: dict[str, str] = {"X-RuleShield-Resolution": resolution}

    if shadow_rule_hit is not None and resp_body:
        try:
            comparison = await _shadow_compare(shadow_rule_hit, resp_body, prompt_text)
            await cache_manager.log_shadow(
                rule_id=comparison["rule_id"],
                prompt_text=prompt_text[:2000],
                rule_response=comparison["rule_response"],
                llm_response=comparison["llm_response"],
                similarity=comparison["similarity"],
                length_ratio=comparison["length_ratio"],
                match_quality=comparison["match_quality"],
            )
            logger.info(
                "Shadow comparison: rule=%s similarity=%.3f quality=%s",
                comparison["rule_id"],
                comparison["similarity"],
                comparison["match_quality"],
            )
            await _apply_shadow_feedback(comparison, prompt_text)
            resolution_headers["X-RuleShield-Shadow"] = comparison["rule_id"]
        except Exception as exc:
            logger.warning("Shadow comparison failed: %s", exc)

    if route_decision and route_decision.get("routed"):
        resolution_headers["X-RuleShield-Routed-Model"] = route_decision.get("model", "")
        resolution_headers["X-RuleShield-Complexity"] = str(route_decision.get("complexity_score", ""))

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type="application/json",
        headers=resolution_headers,
    )


# ---------------------------------------------------------------------------
# Streaming forward (SSE)
# ---------------------------------------------------------------------------


async def _stream_upstream(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    model: str,
    prompt_hash: str,
    prompt_text: str,
    t_start: float,
    route_decision: dict[str, Any] | None = None,
    shadow_rule_hit: dict[str, Any] | None = None,
) -> StreamingResponse:
    """Forward a streaming request, relaying SSE chunks as they arrive."""
    stream_resolution = "routed" if (route_decision and route_decision.get("routed")) else "llm"
    stream_headers: dict[str, str] = {"X-RuleShield-Resolution": stream_resolution}
    stream_state = {"status_code": 200}
    if shadow_rule_hit is not None:
        stream_headers["X-RuleShield-Shadow"] = shadow_rule_hit.get("rule_id", "")

    async def event_generator():
        if http_client is None:
            yield f"data: {json.dumps({'error': 'Proxy not initialized'})}\n\n"
            return
        collected_chunks: list[str] = []
        tokens_completion = 0
        tokens_prompt = 0

        try:
            async with http_client.stream("POST", url, headers=headers, json=body) as resp:
                stream_state["status_code"] = resp.status_code
                if resp.status_code != 200:
                    # On error, read the body and yield it as a single event.
                    error_body = await resp.aread()
                    yield error_body
                    return

                async for line in resp.aiter_lines():
                    # Forward every line verbatim.
                    yield f"{line}\n"

                    # Try to capture content for caching.
                    if line.startswith("data: ") and line.strip() != "data: [DONE]":
                        try:
                            chunk_data = json.loads(line[6:])
                            choices = chunk_data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    collected_chunks.append(content)
                                    tokens_completion += 1  # rough estimate
                            if "usage" in chunk_data:
                                usage = chunk_data.get("usage", {})
                                tokens_prompt = max(tokens_prompt, usage.get("prompt_tokens", 0))
                                tokens_completion = max(tokens_completion, usage.get("completion_tokens", tokens_completion))
                        except (json.JSONDecodeError, IndexError, KeyError):
                            pass

        except Exception as exc:
            logger.error("Streaming upstream error: %s", exc)
            error_payload = json.dumps(
                {"error": {"message": "Upstream stream error", "type": "proxy_error"}}
            )
            yield f"data: {error_payload}\n\n"
            return

        # Post-stream bookkeeping.
        latency_ms = (time.monotonic() - t_start) * 1000
        content = "".join(collected_chunks)
        resp_body = _wrap_openai_response(content, model=model)
        resp_body["usage"]["prompt_tokens"] = tokens_prompt
        resp_body["usage"]["completion_tokens"] = max(resp_body["usage"]["completion_tokens"], tokens_completion)
        resp_body["usage"]["total_tokens"] = (
            resp_body["usage"]["prompt_tokens"] + resp_body["usage"]["completion_tokens"]
        )

        await _record_metrics(
            model,
            stream_resolution,
            resp_body,
            latency_ms,
            prompt_hash=prompt_hash,
            prompt_text=prompt_text,
            route_decision=route_decision,
        )

        if settings.cache_enabled and stream_state["status_code"] == 200 and content:
            try:
                usage = resp_body.get("usage", {})
                cost = (usage.get("prompt_tokens", 0) * 0.000005) + (
                    usage.get("completion_tokens", 0) * 0.000015
                )
                await cache_manager.store(
                    prompt_hash=prompt_hash,
                    prompt_text=prompt_text,
                    response=resp_body,
                    model=model,
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                    cost=cost,
                )
            except Exception as exc:
                logger.warning("Streaming cache store failed: %s", exc)

        if shadow_rule_hit is not None and content:
            try:
                comparison = await _shadow_compare(shadow_rule_hit, resp_body, prompt_text)
                await cache_manager.log_shadow(
                    rule_id=comparison["rule_id"],
                    prompt_text=prompt_text[:2000],
                    rule_response=comparison["rule_response"],
                    llm_response=comparison["llm_response"],
                    similarity=comparison["similarity"],
                    length_ratio=comparison["length_ratio"],
                    match_quality=comparison["match_quality"],
                )
                await _apply_shadow_feedback(comparison, prompt_text)
                logger.info(
                    "Shadow comparison (stream): rule=%s similarity=%.3f quality=%s",
                    comparison["rule_id"],
                    comparison["similarity"],
                    comparison["match_quality"],
                )
            except Exception as exc:
                logger.warning("Streaming shadow comparison failed: %s", exc)

    sse_headers: dict[str, str] = {
        **stream_headers,
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if route_decision and route_decision.get("routed"):
        sse_headers["X-RuleShield-Routed-Model"] = route_decision.get("model", "")
        sse_headers["X-RuleShield-Complexity"] = str(route_decision.get("complexity_score", ""))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=sse_headers,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_response_text(resp_body: dict[str, Any]) -> str:
    """Pull the textual content from an OpenAI-compatible response payload."""
    if not isinstance(resp_body, dict):
        return ""
    for choice in resp_body.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content", "")
        if content:
            return content
    return resp_body.get("content", "")


async def _shadow_compare(
    rule_result: dict[str, Any],
    llm_response: dict[str, Any],
    prompt_text: str,
) -> dict[str, Any]:
    """Compare rule response with LLM response for shadow mode accuracy tracking.

    Uses Jaccard word-overlap similarity (no embeddings needed).

    Returns a dict with comparison metrics:
        rule_id, rule_response (truncated), llm_response (truncated),
        similarity (0-1), length_ratio, match_quality (good|partial|poor).
    """
    rule_id = rule_result.get("rule_id", rule_result.get("id", "unknown"))
    rule_text = _extract_response_text(rule_result.get("response", {}))
    llm_text = _extract_response_text(llm_response)

    # Jaccard similarity on word sets (case-insensitive)
    rule_words = set(rule_text.lower().split())
    llm_words = set(llm_text.lower().split())

    if rule_words or llm_words:
        intersection = rule_words & llm_words
        union = rule_words | llm_words
        similarity = len(intersection) / len(union) if union else 0.0
    else:
        similarity = 1.0  # both empty

    # Length ratio: how close the lengths are (0-1, 1 = identical length)
    rule_len = len(rule_text)
    llm_len = len(llm_text)
    if max(rule_len, llm_len) > 0:
        length_ratio = min(rule_len, llm_len) / max(rule_len, llm_len)
    else:
        length_ratio = 1.0

    # Classify match quality
    if similarity >= 0.8:
        match_quality = "good"
    elif similarity >= 0.4:
        match_quality = "partial"
    else:
        match_quality = "poor"

    return {
        "rule_id": rule_id,
        "deployment": rule_result.get("deployment", "production"),
        "rule_response": rule_text[:500],
        "llm_response": llm_text[:500],
        "similarity": round(similarity, 4),
        "length_ratio": round(length_ratio, 4),
        "match_quality": match_quality,
    }


async def _apply_shadow_feedback(comparison: dict[str, Any], prompt_text: str) -> None:
    """Translate clear shadow outcomes into feedback updates.

    Conservative thresholds keep the auto-feedback loop from overreacting to
    merely different phrasing.
    """
    if feedback_manager is None:
        return

    similarity = float(comparison.get("similarity", 0.0))
    rule_id = comparison.get("rule_id", "")
    if not rule_id:
        return

    if similarity >= 0.85:
        await feedback_manager.record_accept(rule_id, prompt_text)
    elif similarity < 0.50:
        await feedback_manager.record_reject(
            rule_id,
            prompt_text,
            comparison.get("rule_response", ""),
            comparison.get("llm_response", ""),
        )


def _forward_headers(request: Request) -> dict[str, str]:
    """Build headers to send to the upstream provider.

    Passes through Authorization and selected headers while stripping
    hop-by-hop headers that should not be forwarded.
    """
    headers: dict[str, str] = {}

    # Always forward auth.
    if auth := request.headers.get("authorization"):
        headers["Authorization"] = auth
    elif settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    # Forward safe headers.
    for name in ("openai-organization", "openai-project", "x-request-id", "user-agent"):
        if val := request.headers.get(name):
            headers[name] = val

    return headers


def _extract_prompt_text(body: dict[str, Any], endpoint: str) -> str:
    """Extract a flat text representation of the prompt from the request body."""
    if endpoint == "/v1/chat/completions":
        messages = body.get("messages", [])
        return extractor.extract_messages_text(messages)
    else:
        # Legacy completions.
        prompt = body.get("prompt", "")
        if isinstance(prompt, list):
            return "\n".join(prompt)
        return prompt


def _count_tokens(resp_body: dict[str, Any]) -> int:
    """Pull total token count from the response usage block."""
    usage = resp_body.get("usage", {})
    return usage.get("total_tokens", 0)


# ---------------------------------------------------------------------------
# Model name translation
# ---------------------------------------------------------------------------
# Providers like Nous/OpenRouter require full model IDs (e.g.
# "anthropic/claude-4.6-sonnet-20260217") while Hermes sends short names
# (e.g. "claude-sonnet-4-6").

_MODEL_ALIASES: dict[str, str] = {
    # Anthropic via Nous/OpenRouter
    "claude-sonnet-4-6": "anthropic/claude-4.6-sonnet-20260217",
    "claude-sonnet-4": "anthropic/claude-sonnet-4-20250514",
    "claude-opus-4-6": "anthropic/claude-opus-4-6",
    "claude-opus-4": "anthropic/claude-opus-4-20250514",
    "claude-haiku-4-5": "anthropic/claude-haiku-4-5-20251001",
    "claude-haiku-4": "anthropic/claude-haiku-4-5-20251001",
    # OpenAI via OpenRouter
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4.5": "openai/gpt-4.5-preview",
    "gpt-4.1": "openai/gpt-4.1",
    "gpt-4.1-mini": "openai/gpt-4.1-mini",
    "gpt-4.1-nano": "openai/gpt-4.1-nano",
    # Google via OpenRouter
    "gemini-2.5-pro": "google/gemini-2.5-pro-preview-06-05",
    "gemini-2.0-flash": "google/gemini-2.0-flash-001",
    # DeepSeek
    "deepseek-chat": "deepseek/deepseek-chat-v3-0324",
    "deepseek-r1": "deepseek/deepseek-r1",
}


# Keep base at /api because proxy endpoints already include /v1/* in many paths.
# This avoids generating /api/v1/v1/chat/completions.
_OPENROUTER_PROVIDER_URL = "https://openrouter.ai/api"
_OPENROUTER_MODEL_HINTS = (
    "arcee-ai/",
    "stepfun/",
    "anthropic/",
    "openai/",
    "google/",
    "deepseek/",
)


def _is_openrouter_model(model: str) -> bool:
    if not model:
        return False
    model_lc = model.strip().lower()
    if not model_lc:
        return False
    if model_lc.endswith(":free"):
        return True
    if any(model_lc.startswith(prefix) for prefix in _OPENROUTER_MODEL_HINTS):
        return True
    return "/" in model_lc


def _is_openrouter_authorization(auth_header: str | None) -> bool:
    if not auth_header:
        return False
    raw = auth_header.strip()
    if not raw.lower().startswith("bearer "):
        return False
    token = raw[7:].strip()
    return token.startswith("sk-or-")


def _parse_dotenv_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def _resolve_openrouter_api_key() -> str:
    for key_name in ("RULESHIELD_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"):
        value = (os.getenv(key_name) or "").strip()
        if value:
            return value

    hermes_env = _parse_dotenv_file(Path.home() / ".hermes" / ".env")
    value = (hermes_env.get("OPENROUTER_API_KEY") or "").strip()
    if value:
        return value

    ruleshield_env = _parse_dotenv_file(Path.home() / ".ruleshield" / ".env")
    value = (ruleshield_env.get("OPENROUTER_API_KEY") or "").strip()
    if value:
        return value

    return ""


def _resolve_upstream_for_model(
    *,
    model: str,
    request: Request,
    headers: dict[str, str],
) -> tuple[str, dict[str, str], str | None]:
    provider_override = (request.headers.get("x-ruleshield-provider") or "").strip().lower()
    use_openrouter = provider_override == "openrouter" or _is_openrouter_model(model)
    if not use_openrouter:
        logger.info(
            "Upstream route: provider=default model=%s override=%s",
            model,
            provider_override or "-",
        )
        return settings.provider_url, headers, None

    resolved_headers = dict(headers)
    if not _is_openrouter_authorization(resolved_headers.get("Authorization")):
        key = _resolve_openrouter_api_key()
        if not key:
            logger.warning(
                "Upstream route: provider=openrouter model=%s but no key detected",
                model,
            )
            return (
                _OPENROUTER_PROVIDER_URL,
                resolved_headers,
                (
                    "OpenRouter model requested, but no OpenRouter API key is configured. "
                    "Set OPENROUTER_API_KEY (or RULESHIELD_OPENROUTER_API_KEY)."
                ),
            )
        resolved_headers["Authorization"] = f"Bearer {key}"
        logger.info(
            "Upstream route: provider=openrouter model=%s auth=overridden_with_openrouter_key",
            model,
        )
    else:
        logger.info(
            "Upstream route: provider=openrouter model=%s auth=request_openrouter_key",
            model,
        )

    return _OPENROUTER_PROVIDER_URL, resolved_headers, None


def _translate_model_name(model: str, provider_url: str) -> str:
    """Translate short model names to full provider-specific IDs.

    Only translates when the upstream is Nous/OpenRouter (which need full IDs).
    Direct provider APIs (api.openai.com, api.anthropic.com) accept short names.
    """
    url_lower = provider_url.lower()

    # Only translate for OpenRouter -- Nous accepts short names directly
    if "openrouter" not in url_lower:
        return model

    # Already has a provider prefix (e.g. "anthropic/claude-...") -- pass through
    if "/" in model:
        return model

    translated = _MODEL_ALIASES.get(model, model)
    if translated != model:
        logger.debug("Model translated: %s -> %s", model, translated)
    return translated


def _normalize_chat_payload_for_upstream(body: dict[str, Any]) -> dict[str, Any]:
    """Normalize Codex-style chat payloads to OpenAI chat-completions schema.

    Hermes can send ``instructions`` + ``input`` payloads even when targeting
    ``/v1/chat/completions``. Providers like OpenRouter reject that shape and
    require ``messages``.
    """
    if not isinstance(body, dict):
        return body
    if "messages" in body and isinstance(body.get("messages"), list):
        return body

    messages: list[dict[str, Any]] = []

    # Reuse adapter logic when available.
    if _HAS_CODEX_ADAPTER:
        try:
            extracted = extract_messages_from_codex(body)
            if isinstance(extracted, list) and extracted:
                messages = extracted
        except Exception:
            messages = []

    if not messages:
        instructions = body.get("instructions")
        if isinstance(instructions, str) and instructions.strip():
            messages.append({"role": "system", "content": instructions.strip()})

        raw_input = body.get("input")
        if isinstance(raw_input, str) and raw_input.strip():
            messages.append({"role": "user", "content": raw_input.strip()})
        elif isinstance(raw_input, list):
            for item in raw_input:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role", "user"))
                content = item.get("content", "")
                if isinstance(content, list):
                    # Flatten rich content parts into plain text for compatibility.
                    parts: list[str] = []
                    for part in content:
                        if isinstance(part, dict):
                            text = part.get("text")
                            if isinstance(text, str) and text.strip():
                                parts.append(text.strip())
                    content = "\n".join(parts)
                if isinstance(content, str) and content.strip():
                    messages.append({"role": role, "content": content.strip()})

    if messages:
        body["messages"] = messages

    # Remove Codex-specific keys that can confuse strict chat-completions providers.
    body.pop("instructions", None)
    body.pop("input", None)

    return body


def _normalize_tools_for_openrouter_chat(body: dict[str, Any]) -> dict[str, Any]:
    """Convert Hermes-style flat function tools to OpenAI/OpenRouter shape."""
    if not isinstance(body, dict):
        return body
    raw_tools = body.get("tools")
    if not isinstance(raw_tools, list):
        return body

    normalized_tools: list[dict[str, Any]] = []
    changed = False
    for tool in raw_tools:
        if not isinstance(tool, dict):
            normalized_tools.append(tool)
            continue
        if tool.get("type") != "function":
            normalized_tools.append(tool)
            continue
        # Already in nested format.
        if isinstance(tool.get("function"), dict):
            normalized_tools.append(tool)
            continue
        name = tool.get("name")
        params = tool.get("parameters")
        if not name or not isinstance(params, dict):
            normalized_tools.append(tool)
            continue

        fn_obj: dict[str, Any] = {
            "name": str(name),
            "parameters": params,
        }
        description = tool.get("description")
        if isinstance(description, str) and description.strip():
            fn_obj["description"] = description
        if "strict" in tool:
            fn_obj["strict"] = bool(tool.get("strict"))

        normalized_tools.append({
            "type": "function",
            "function": fn_obj,
        })
        changed = True

    if changed:
        body["tools"] = normalized_tools
    return body


def _wrap_openai_response(content: str, model: str = "ruleshield-rule") -> dict[str, Any]:
    """Wrap a plain text response in OpenAI-compatible chat completion format.

    LiteLLM / Hermes expects ``response.choices`` to be a list with at least
    one element containing a ``message`` dict.  Without this wrapper, rule and
    cache responses cause "response.choices is None" errors.
    """
    return {
        "id": f"ruleshield-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": max(len(content.split()), 1),
            "total_tokens": max(len(content.split()), 1),
        },
    }


def _estimate_cost(resp_body: dict[str, Any]) -> float:
    """Estimate what a cached/ruled response would have cost as a fresh LLM call."""
    if not isinstance(resp_body, dict):
        return 0.001  # default estimate for a short exchange
    usage = resp_body.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    if tokens_in or tokens_out:
        return (tokens_in * 0.000005) + (tokens_out * 0.000015)
    # No usage info (e.g. rule response) -- estimate based on content length
    content = ""
    for c in resp_body.get("choices", []):
        content += c.get("message", {}).get("content", "")
    if not content:
        content = resp_body.get("content", "")
    estimated_tokens = max(len(content.split()) * 1.3, 10)
    return (10 * 0.000005) + (estimated_tokens * 0.000015)


async def _record_metrics(
    model: str, resolution: str, resp_body: dict[str, Any], latency_ms: float,
    prompt_hash: str = "", prompt_text: str = "", estimated_saving: float = 0.0,
    route_decision: dict[str, Any] | None = None,
) -> None:
    """Best-effort metrics recording."""
    usage = resp_body.get("usage", {}) if isinstance(resp_body, dict) else {}
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    actual_cost = (tokens_in * 0.000005) + (tokens_out * 0.000015)

    # For cache/rule hits, the actual cost is 0 but we track what was saved
    if resolution in ("cache", "rule"):
        cost_without = estimated_saving  # what it would have cost
        cost_with = 0.0  # what it actually cost (nothing!)
    elif resolution == "routed" and route_decision:
        # Routed: actual cost is lower because we used a cheaper model.
        # Estimate premium cost vs actual cheaper-model cost.
        tier = route_decision.get("tier", "premium")
        cost_ratios = {"cheap": 0.05, "mid": 0.30, "premium": 1.0}
        ratio = cost_ratios.get(tier, 1.0)
        cost_without = usage.get("cost", actual_cost)
        # The actual cost at the cheaper model is what we paid;
        # what it *would* have cost is the premium rate.
        if ratio < 1.0 and actual_cost > 0:
            cost_without = actual_cost / ratio  # estimated premium cost
            cost_with = actual_cost
        else:
            cost_with = cost_without
    else:
        # Use provider-reported cost if available, else estimate
        cost_without = usage.get("cost", actual_cost)
        cost_with = cost_without

    try:
        await metrics.record(
            model=model,
            resolution=resolution,
            tokens_prompt=tokens_in,
            tokens_completion=tokens_out,
            latency_ms=latency_ms,
            prompt_text=prompt_text,
            cost_without=cost_without,
            cost_with=cost_with,
        )
    except Exception as exc:
        logger.warning("Metrics recording failed: %s", exc)

    try:
        await cache_manager.log_request(
            prompt_hash=prompt_hash,
            prompt_text=prompt_text,
            response=resp_body if isinstance(resp_body, dict) else {},
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost_without,
            resolution_type=resolution,
            latency_ms=int(latency_ms),
        )
    except Exception as exc:
        logger.warning("Request logging failed: %s", exc)

    # Fire-and-forget Slack milestone notification (non-blocking).
    if slack_notifier is not None:
        dashboard = metrics.dashboard
        savings_usd = dashboard.total_cost_without - dashboard.total_cost_with
        milestone_stats = {
            "savings_usd": savings_usd,
            "savings_pct": (
                (savings_usd / dashboard.total_cost_without * 100)
                if dashboard.total_cost_without > 0
                else 0.0
            ),
            "total_requests": dashboard.total_requests,
            "cache_hits": dashboard.cache_hits,
            "rule_hits": dashboard.rule_hits,
            "llm_calls": dashboard.llm_calls,
        }
        asyncio.create_task(slack_notifier.notify_savings_milestone(milestone_stats))

    # --- Cache eviction check (every 1000 requests) ----------------------
    if not hasattr(_record_metrics, '_evict_counter'):
        _record_metrics._evict_counter = 0
    _record_metrics._evict_counter += 1
    if _record_metrics._evict_counter % 1000 == 0:
        try:
            await cache_manager.evict()
        except Exception:
            pass

    # --- Auto-promotion check (every 100 requests) -----------------------
    if not hasattr(_record_metrics, "_request_count"):
        _record_metrics._request_count = 0  # type: ignore[attr-defined]
    _record_metrics._request_count += 1  # type: ignore[attr-defined]

    if _record_metrics._request_count % 100 == 0:  # type: ignore[attr-defined]
        try:
            from ruleshield.feedback import RuleFeedback

            fb = RuleFeedback(rule_engine)
            await fb.init()
            promoted = await fb.check_promotions()
            for rule_id in promoted:
                rule_engine.activate_rule(rule_id)
                await fb.log_rule_event(
                    rule_id=rule_id,
                    event_type="rule_promoted",
                    direction="up",
                    details={"source": "auto_promotion"},
                )
                logger.info("Auto-promoted rule: %s", rule_id)
            await fb.close()
        except Exception:
            logger.debug("Auto-promotion check failed", exc_info=True)


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    _settings = load_settings()
    uvicorn.run(app, host="0.0.0.0", port=_settings.port, log_level=_settings.log_level)
