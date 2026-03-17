"""Shared helper functions for the RuleShield proxy.

Contains header forwarding, prompt extraction, response wrapping,
cost estimation, model translation, rate limiting, and metrics recording.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import Header, HTTPException, Request

from ruleshield.config import CONFIG_PATH, RULESHIELD_DIR
from ruleshield.router import SmartRouter

from ruleshield import state

logger = logging.getLogger("ruleshield.proxy")

# ---------------------------------------------------------------------------
# Rate limiter
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


# Singleton rate limiter
rate_limiter = SimpleRateLimiter(
    state.settings.rate_limit_rpm if hasattr(state.settings, "rate_limit_rpm") else 120
)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def require_admin_key(
    authorization: str = Header(None, alias="X-RuleShield-Admin-Key"),
):
    """Require admin key for management endpoints."""
    if not state.settings.admin_key:
        return
    if not authorization or authorization != state.settings.admin_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")


# ---------------------------------------------------------------------------
# Header forwarding
# ---------------------------------------------------------------------------


def forward_headers(request: Request) -> dict[str, str]:
    """Build headers to send to the upstream provider.

    Passes through Authorization and selected headers while stripping
    hop-by-hop headers that should not be forwarded.
    """
    headers: dict[str, str] = {}

    # Always forward auth.
    if auth := request.headers.get("authorization"):
        headers["Authorization"] = auth
    elif state.settings.api_key:
        headers["Authorization"] = f"Bearer {state.settings.api_key}"

    # Forward safe headers.
    for name in (
        "openai-organization",
        "openai-project",
        "x-request-id",
        "user-agent",
    ):
        if val := request.headers.get(name):
            headers[name] = val

    return headers


# ---------------------------------------------------------------------------
# Prompt extraction
# ---------------------------------------------------------------------------


def extract_prompt_text(body: dict[str, Any], endpoint: str) -> str:
    """Extract a flat text representation of the prompt from the request body."""
    if endpoint == "/v1/chat/completions":
        messages = body.get("messages", [])
        return state.extractor.extract_messages_text(messages)
    else:
        # Legacy completions.
        prompt = body.get("prompt", "")
        if isinstance(prompt, list):
            return "\n".join(prompt)
        return prompt


# ---------------------------------------------------------------------------
# Response wrapping
# ---------------------------------------------------------------------------


def wrap_openai_response(
    content: str, model: str = "ruleshield-rule"
) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_cost(resp_body: dict[str, Any]) -> float:
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


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


def count_tokens(resp_body: dict[str, Any]) -> int:
    """Pull total token count from the response usage block."""
    usage = resp_body.get("usage", {})
    return usage.get("total_tokens", 0)


# ---------------------------------------------------------------------------
# Model name translation
# ---------------------------------------------------------------------------

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


def resolve_upstream_for_model(
    *,
    model: str,
    request: Request,
    headers: dict[str, str],
) -> tuple[str, dict[str, str], str | None]:
    """Determine the upstream provider URL for a given model.

    Returns (provider_url, headers, error_message_or_None).
    """
    provider_override = (
        (request.headers.get("x-ruleshield-provider") or "").strip().lower()
    )
    use_openrouter = provider_override == "openrouter" or _is_openrouter_model(model)
    if not use_openrouter:
        logger.info(
            "Upstream route: provider=default model=%s override=%s",
            model,
            provider_override or "-",
        )
        return state.settings.provider_url, headers, None

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


def translate_model_name(model: str, provider_url: str) -> str:
    """Translate short model names to full provider-specific IDs.

    Only translates when the upstream is Nous/OpenRouter (which need full IDs).
    Direct provider APIs (api.openai.com, api.anthropic.com) accept short names.
    """
    url_lower = provider_url.lower()

    # Only translate for OpenRouter
    if "openrouter" not in url_lower:
        return model

    # Already has a provider prefix
    if "/" in model:
        return model

    translated = _MODEL_ALIASES.get(model, model)
    if translated != model:
        logger.debug("Model translated: %s -> %s", model, translated)
    return translated


def normalize_chat_payload_for_upstream(body: dict[str, Any]) -> dict[str, Any]:
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
    if state.HAS_CODEX_ADAPTER:
        try:
            extracted = state.extract_messages_from_codex(body)
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


def normalize_tools_for_openrouter_chat(body: dict[str, Any]) -> dict[str, Any]:
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

        normalized_tools.append(
            {
                "type": "function",
                "function": fn_obj,
            }
        )
        changed = True

    if changed:
        body["tools"] = normalized_tools
    return body


# ---------------------------------------------------------------------------
# Response text extraction
# ---------------------------------------------------------------------------


def extract_response_text(resp_body: dict[str, Any]) -> str:
    """Pull the textual content from an OpenAI-compatible response payload."""
    if not isinstance(resp_body, dict):
        return ""
    for choice in resp_body.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content", "")
        if content:
            return content
    return resp_body.get("content", "")


# ---------------------------------------------------------------------------
# Shadow mode comparison
# ---------------------------------------------------------------------------


async def shadow_compare(
    rule_result: dict[str, Any],
    llm_response: dict[str, Any],
    prompt_text: str,
) -> dict[str, Any]:
    """Compare rule response with LLM response for shadow mode accuracy tracking.

    Uses Jaccard word-overlap similarity (no embeddings needed).
    """
    rule_id = rule_result.get("rule_id", rule_result.get("id", "unknown"))
    rule_text = extract_response_text(rule_result.get("response", {}))
    llm_text = extract_response_text(llm_response)

    # Jaccard similarity on word sets (case-insensitive)
    rule_words = set(rule_text.lower().split())
    llm_words = set(llm_text.lower().split())

    if rule_words or llm_words:
        intersection = rule_words & llm_words
        union = rule_words | llm_words
        similarity = len(intersection) / len(union) if union else 0.0
    else:
        similarity = 1.0  # both empty

    # Length ratio
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


async def apply_shadow_feedback(
    comparison: dict[str, Any], prompt_text: str
) -> None:
    """Translate clear shadow outcomes into feedback updates."""
    if state.feedback_manager is None:
        return

    similarity = float(comparison.get("similarity", 0.0))
    rule_id = comparison.get("rule_id", "")
    if not rule_id:
        return

    if similarity >= 0.85:
        await state.feedback_manager.record_accept(rule_id, prompt_text)
    elif similarity < 0.50:
        await state.feedback_manager.record_reject(
            rule_id,
            prompt_text,
            comparison.get("rule_response", ""),
            comparison.get("llm_response", ""),
        )


# ---------------------------------------------------------------------------
# Metrics recording
# ---------------------------------------------------------------------------


async def record_metrics(
    model: str,
    resolution: str,
    resp_body: dict[str, Any],
    latency_ms: float,
    prompt_hash: str = "",
    prompt_text: str = "",
    estimated_saving: float = 0.0,
    route_decision: dict[str, Any] | None = None,
) -> None:
    """Best-effort metrics recording."""
    usage = resp_body.get("usage", {}) if isinstance(resp_body, dict) else {}
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    actual_cost = (tokens_in * 0.000005) + (tokens_out * 0.000015)

    if resolution in ("cache", "rule"):
        cost_without = estimated_saving
        cost_with = 0.0
    elif resolution == "routed" and route_decision:
        tier = route_decision.get("tier", "premium")
        cost_ratios = {"cheap": 0.05, "mid": 0.30, "premium": 1.0}
        ratio = cost_ratios.get(tier, 1.0)
        cost_without = usage.get("cost", actual_cost)
        if ratio < 1.0 and actual_cost > 0:
            cost_without = actual_cost / ratio
            cost_with = actual_cost
        else:
            cost_with = cost_without
    else:
        cost_without = usage.get("cost", actual_cost)
        cost_with = cost_without

    try:
        await state.metrics.record(
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
        await state.cache_manager.log_request(
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

    # Fire-and-forget Slack milestone notification.
    if state.slack_notifier is not None:
        dashboard = state.metrics.dashboard
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
        asyncio.create_task(
            state.slack_notifier.notify_savings_milestone(milestone_stats)
        )

    # Cache eviction check (every 1000 requests)
    if not hasattr(record_metrics, "_evict_counter"):
        record_metrics._evict_counter = 0  # type: ignore[attr-defined]
    record_metrics._evict_counter += 1  # type: ignore[attr-defined]
    if record_metrics._evict_counter % 1000 == 0:  # type: ignore[attr-defined]
        try:
            await state.cache_manager.evict()
        except Exception:
            pass

    # Auto-promotion check (every 100 requests)
    if not hasattr(record_metrics, "_request_count"):
        record_metrics._request_count = 0  # type: ignore[attr-defined]
    record_metrics._request_count += 1  # type: ignore[attr-defined]

    if record_metrics._request_count % 100 == 0:  # type: ignore[attr-defined]
        try:
            from ruleshield.feedback import RuleFeedback

            fb = RuleFeedback(state.rule_engine)
            await fb.init()
            promoted = await fb.check_promotions()
            for rule_id in promoted:
                state.rule_engine.activate_rule(rule_id)
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
# Codex pricing & helpers
# ---------------------------------------------------------------------------

CODEX_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.3-codex": {"input": 5.0, "output": 20.0},
    "gpt-5.2-codex": {"input": 2.5, "output": 10.0},
    "gpt-5.1-codex-max": {"input": 4.0, "output": 16.0},
    "gpt-5.1-codex-mini": {"input": 0.25, "output": 2.0},
    "gpt-5.4": {"input": 2.0, "output": 8.0},
    "gpt-5.4-pro": {"input": 5.0, "output": 20.0},
}


def compute_codex_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD for a Codex API call."""
    pricing = CODEX_PRICING.get(model, {"input": 2.5, "output": 10.0})
    return (input_tokens / 1_000_000) * pricing["input"] + (
        output_tokens / 1_000_000
    ) * pricing["output"]


def extract_codex_content(response: dict) -> str:
    """Extract text content from a cached response (may be OpenAI or Codex format)."""
    # Codex Responses API format
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

    # OpenAI Chat Completions format
    try:
        choices = response.get("choices", [])
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message", {})
            if isinstance(msg, dict) and msg.get("content"):
                return msg["content"]
    except (TypeError, AttributeError, IndexError):
        pass

    # Plain content key
    if isinstance(response.get("content"), str):
        return response["content"]

    return str(response) if response else ""


def extract_codex_assistant_text(response: dict[str, Any]) -> str:
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


def extract_codex_event_text(event_data: dict[str, Any]) -> str:
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
            return extract_codex_assistant_text({"output": [item]})

    if event_type == "response.completed":
        response = event_data.get("response", {})
        if isinstance(response, dict):
            return extract_codex_assistant_text(response)

    return ""


def select_codex_stream_text(stream_state: dict[str, Any]) -> str:
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
# Runtime config persistence
# ---------------------------------------------------------------------------


def to_bool(value: Any) -> bool | None:
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


def persist_runtime_settings(changes: dict[str, bool]) -> bool:
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
            yaml.dump(
                data, fh, default_flow_style=False, sort_keys=False, allow_unicode=True
            )
        return True
    except Exception as exc:
        logger.warning("Failed to persist runtime settings: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Retry logic for upstream requests
# ---------------------------------------------------------------------------

RETRY_STATUS_CODES = {429, 500, 502, 503, 529}


async def retry_request(
    method: str,
    url: str,
    headers: dict,
    body: dict | bytes | None = None,
    max_retries: int | None = None,
) -> "httpx.Response":
    """Execute an HTTP request with exponential backoff retry."""
    import random

    if max_retries is None:
        max_retries = state.settings.max_retries if state.settings else 3
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if isinstance(body, bytes):
                resp = await state.http_client.request(
                    method, url, headers=headers, content=body
                )
            elif body is not None:
                resp = await state.http_client.request(
                    method, url, headers=headers, json=body
                )
            else:
                resp = await state.http_client.request(method, url, headers=headers)

            if resp.status_code not in RETRY_STATUS_CODES:
                return resp

            if attempt < max_retries:
                wait = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    "Upstream returned %d, retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait)
            else:
                return resp

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    "Upstream connection error: %s, retrying in %.1fs (attempt %d/%d)",
                    exc,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(wait)
            else:
                raise

    raise last_exc or Exception("Retry exhausted")
