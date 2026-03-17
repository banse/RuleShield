"""Core proxy routes: /v1/chat/completions, /v1/completions, /v1/models.

Contains the main _handle_completion logic, _forward_upstream, and
_stream_upstream for non-streaming and streaming LLM forwarding.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from ruleshield import state
from ruleshield.helpers import (
    extract_prompt_text,
    estimate_cost,
    forward_headers,
    record_metrics,
    resolve_upstream_for_model,
    retry_request,
    translate_model_name,
    normalize_chat_payload_for_upstream,
    normalize_tools_for_openrouter_chat,
    wrap_openai_response,
    shadow_compare,
    apply_shadow_feedback,
    RETRY_STATUS_CODES,
)

logger = logging.getLogger("ruleshield.proxy")

router = APIRouter()


# ---------------------------------------------------------------------------
# /v1/models
# ---------------------------------------------------------------------------


@router.get("/v1/models")
async def list_models(request: Request):
    """Proxy the models list from the upstream provider."""
    upstream_url = f"{state.settings.provider_url.rstrip('/')}/v1/models"
    headers = forward_headers(request)

    try:
        if state.http_client is None:
            return JSONResponse(
                status_code=503, content={"error": "Proxy not initialized"}
            )
        resp = await state.http_client.get(upstream_url, headers=headers)
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


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Handle OpenAI-compatible chat completion requests."""
    return await _handle_completion(request, endpoint="/v1/chat/completions")


@router.post("/v1/completions")
async def completions(request: Request):
    """Handle legacy completion requests."""
    return await _handle_completion(request, endpoint="/v1/completions")


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
            content={
                "error": {
                    "message": "Invalid JSON body",
                    "type": "invalid_request_error",
                }
            },
        )

    model = body.get("model", "unknown")
    stream = body.get("stream", False)

    # Extract a single text representation of the prompt for cache/rules.
    prompt_text = extract_prompt_text(body, endpoint)
    prompt_hash = state.extractor.hash_prompt(prompt_text)

    # --- 1. Cache check ----------------------------------------------------
    resolution = "llm"  # default: forwarded to the real LLM

    if state.settings.cache_enabled:
        try:
            cached = await state.cache_manager.check(prompt_hash, prompt_text)
            if cached is not None:
                resolution = "cache"
                latency_ms = (time.monotonic() - t_start) * 1000
                estimated_cost = estimate_cost(cached.get("response", {}))
                await record_metrics(
                    model,
                    resolution,
                    cached.get("response", {}),
                    latency_ms,
                    prompt_hash=prompt_hash,
                    prompt_text=prompt_text,
                    estimated_saving=estimated_cost,
                )
                return JSONResponse(
                    content=cached["response"],
                    headers={"X-RuleShield-Resolution": resolution},
                )
        except Exception as exc:
            logger.warning(
                "Cache check failed (proceeding without cache): %s", exc
            )

    # --- 1.5 Template check ------------------------------------------------
    if state.settings.rules_enabled and prompt_text:
        try:
            from ruleshield.template_optimizer import TemplateOptimizer

            if not hasattr(_handle_completion, "_tpl_optimizer"):
                _handle_completion._tpl_optimizer = TemplateOptimizer()  # type: ignore[attr-defined]
                _handle_completion._tpl_optimizer.load_templates()  # type: ignore[attr-defined]

            tpl_result = _handle_completion._tpl_optimizer.match(prompt_text)  # type: ignore[attr-defined]
            if tpl_result:
                tpl, variables, cached_response = tpl_result
                if cached_response:
                    resolution = "template"
                    latency_ms = (time.monotonic() - t_start) * 1000
                    resp_payload = wrap_openai_response(
                        cached_response, model="ruleshield-template"
                    )
                    await record_metrics(
                        model,
                        resolution,
                        resp_payload,
                        latency_ms,
                        prompt_hash=prompt_hash,
                        prompt_text=prompt_text,
                        estimated_saving=0.001,
                    )
                    return JSONResponse(
                        content=resp_payload,
                        headers={"X-RuleShield-Resolution": "template"},
                    )
                else:
                    logger.info(
                        "Template '%s' matched with new variables %s -- forwarding to LLM",
                        tpl.id,
                        variables,
                    )
        except Exception as exc:
            logger.debug("Template check skipped: %s", exc)

    # --- 2. Rule check -----------------------------------------------------
    shadow_rule_hit: dict[str, Any] | None = None

    if state.settings.rules_enabled:
        shadow_confidence_floor = (
            state.settings.shadow_test_confidence_floor
            if state.settings.shadow_mode
            and state.settings.shadow_test_confidence_floor > 0.0
            else None
        )
        try:
            rule_hit = await state.rule_engine.async_match(
                prompt_text,
                messages=body.get("messages"),
                model=model,
                confidence_floor=shadow_confidence_floor,
            )
            if rule_hit is not None:
                if state.settings.shadow_mode:
                    shadow_rule_hit = rule_hit
                    logger.info(
                        "Shadow mode: rule '%s' matched but forwarding to LLM for comparison",
                        rule_hit.get("rule_id", rule_hit.get("id", "unknown")),
                    )
                else:
                    resolution = "rule"
                    latency_ms = (time.monotonic() - t_start) * 1000
                    raw_response = rule_hit.get("response", {})
                    estimated_cost = 0.001
                    resp_payload = wrap_openai_response(
                        content=raw_response.get("content", str(raw_response)),
                        model=raw_response.get("model", "ruleshield-rule"),
                    )
                    await record_metrics(
                        model,
                        resolution,
                        resp_payload,
                        latency_ms,
                        prompt_hash=prompt_hash,
                        prompt_text=prompt_text,
                        estimated_saving=estimated_cost,
                    )
                    return JSONResponse(
                        content=resp_payload,
                        headers={"X-RuleShield-Resolution": resolution},
                    )
            elif state.settings.shadow_mode:
                candidate_hit = await state.rule_engine.async_match_candidates(
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
            logger.warning(
                "Rule check failed (proceeding without rules): %s", exc
            )

    # --- 2.5 Prompt Trimming (optional) ------------------------------------
    if (
        state.settings.prompt_trimming_enabled
        and state.settings.rules_enabled
        and prompt_text
        and len(prompt_text) > 50
        and resolution == "llm"
    ):
        try:
            from ruleshield.hermes_bridge import trim_prompt

            rule_matches = []
            for rule in state.rule_engine.rules:
                if not rule.get("enabled", True):
                    continue
                matching_values = []
                for pattern in rule.get("patterns", []):
                    if pattern.get("type") == "contains":
                        if pattern["value"].lower() in prompt_text.lower():
                            matching_values.append(pattern["value"])
                if matching_values:
                    rule_matches.append(
                        {
                            "patterns": matching_values,
                            "answer": rule.get("response", {}).get("content", ""),
                            "rule_id": rule["id"],
                        }
                    )

            if rule_matches:
                trimmed, known_parts = trim_prompt(prompt_text, rule_matches)

                if trimmed and len(trimmed) < len(prompt_text) * 0.8:
                    logger.info(
                        "Prompt trimmed: %d -> %d chars (%d parts handled by rules)",
                        len(prompt_text),
                        len(trimmed),
                        len(known_parts),
                    )

                    context = "Context (already known):\n"
                    for kp in known_parts:
                        context += f"- {kp['question']}: {kp['answer']}\n"
                    context += (
                        f"\nPlease answer ONLY this remaining question:\n{trimmed}"
                    )

                    if "messages" in body:
                        for msg in reversed(body["messages"]):
                            if msg.get("role") == "user":
                                msg["content"] = context
                                break

                    prompt_text = context
                    prompt_hash = state.extractor.hash_prompt(prompt_text)

                    await record_metrics(
                        model,
                        "trimmed",
                        {},
                        0,
                        prompt_hash=prompt_hash,
                        prompt_text=f"[trimmed] {trimmed[:100]}",
                        estimated_saving=0.0,
                    )
        except Exception as exc:
            logger.debug("Prompt trimming skipped: %s", exc)

    # --- 3. Smart Router ---------------------------------------------------
    route_decision = None
    if state.smart_router is not None:
        try:
            route_decision = state.smart_router.route(
                prompt_text=prompt_text,
                messages=body.get("messages"),
                original_model=model,
                provider_url=state.settings.provider_url,
            )
            if route_decision["routed"]:
                resolution = "routed"
                body["model"] = route_decision["model"]
                logger.info(
                    "Router: %s -> %s (score=%d, tier=%s)",
                    model,
                    route_decision["model"],
                    route_decision["complexity_score"],
                    route_decision["tier"],
                )
        except Exception as exc:
            logger.warning(
                "Router failed (proceeding with original model): %s", exc
            )

    # --- 3b. Translate model name for upstream provider --------------------
    headers = forward_headers(request)
    selected_provider_url, headers, provider_error = resolve_upstream_for_model(
        model=body.get("model", model),
        request=request,
        headers=headers,
    )
    if provider_error:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": provider_error,
                    "type": "provider_config_error",
                }
            },
        )

    # OpenRouter-compatible chat schema for Codex-style Hermes payloads.
    if endpoint == "/v1/chat/completions":
        body = normalize_chat_payload_for_upstream(body)
        if "openrouter.ai/api" in selected_provider_url:
            body = normalize_tools_for_openrouter_chat(body)
        prompt_text = extract_prompt_text(body, endpoint)
        prompt_hash = state.extractor.hash_prompt(prompt_text)

    body["model"] = translate_model_name(
        body.get("model", model), selected_provider_url
    )

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
    if state.http_client is None:
        return JSONResponse(
            status_code=503, content={"error": "Proxy not initialized"}
        )

    try:
        resp = await retry_request("POST", url, headers, body=body)
    except Exception as exc:
        logger.error("Upstream request failed after retries: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"error": {"message": "Upstream error", "type": "proxy_error"}},
        )

    latency_ms = (time.monotonic() - t_start) * 1000
    resolution = (
        "routed" if (route_decision and route_decision.get("routed")) else "llm"
    )

    resp_body: dict[str, Any] = {}
    try:
        resp_body = resp.json()
    except Exception:
        pass

    await record_metrics(
        model,
        resolution,
        resp_body,
        latency_ms,
        prompt_hash=prompt_hash,
        prompt_text=prompt_text,
        route_decision=route_decision,
    )

    # Store in cache (best-effort).
    if state.settings.cache_enabled and resp.status_code == 200 and resp_body:
        try:
            usage = resp_body.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            cost = (tokens_in * 0.000005) + (tokens_out * 0.000015)
            await state.cache_manager.store(
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

    # Shadow mode comparison
    resolution_headers: dict[str, str] = {"X-RuleShield-Resolution": resolution}

    if shadow_rule_hit is not None and resp_body:
        try:
            comparison = await shadow_compare(
                shadow_rule_hit, resp_body, prompt_text
            )
            await state.cache_manager.log_shadow(
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
            await apply_shadow_feedback(comparison, prompt_text)
            resolution_headers["X-RuleShield-Shadow"] = comparison["rule_id"]
        except Exception as exc:
            logger.warning("Shadow comparison failed: %s", exc)

    if route_decision and route_decision.get("routed"):
        resolution_headers["X-RuleShield-Routed-Model"] = route_decision.get(
            "model", ""
        )
        resolution_headers["X-RuleShield-Complexity"] = str(
            route_decision.get("complexity_score", "")
        )

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
    stream_resolution = (
        "routed" if (route_decision and route_decision.get("routed")) else "llm"
    )
    stream_headers: dict[str, str] = {"X-RuleShield-Resolution": stream_resolution}
    stream_state = {"status_code": 200}
    if shadow_rule_hit is not None:
        stream_headers["X-RuleShield-Shadow"] = shadow_rule_hit.get("rule_id", "")

    async def event_generator():
        if state.http_client is None:
            yield f"data: {json.dumps({'error': 'Proxy not initialized'})}\n\n"
            return
        collected_chunks: list[str] = []
        tokens_completion = 0
        tokens_prompt = 0

        try:
            async with state.http_client.stream(
                "POST", url, headers=headers, json=body
            ) as resp:
                stream_state["status_code"] = resp.status_code
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    yield error_body
                    return

                async for line in resp.aiter_lines():
                    yield f"{line}\n"

                    if (
                        line.startswith("data: ")
                        and line.strip() != "data: [DONE]"
                    ):
                        try:
                            chunk_data = json.loads(line[6:])
                            choices = chunk_data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    collected_chunks.append(content)
                                    tokens_completion += 1
                            if "usage" in chunk_data:
                                usage = chunk_data.get("usage", {})
                                tokens_prompt = max(
                                    tokens_prompt,
                                    usage.get("prompt_tokens", 0),
                                )
                                tokens_completion = max(
                                    tokens_completion,
                                    usage.get(
                                        "completion_tokens", tokens_completion
                                    ),
                                )
                        except (json.JSONDecodeError, IndexError, KeyError):
                            pass

        except Exception as exc:
            logger.error("Streaming upstream error: %s", exc)
            error_payload = json.dumps(
                {
                    "error": {
                        "message": "Upstream stream error",
                        "type": "proxy_error",
                    }
                }
            )
            yield f"data: {error_payload}\n\n"
            return

        # Post-stream bookkeeping.
        latency_ms = (time.monotonic() - t_start) * 1000
        content = "".join(collected_chunks)
        resp_body = wrap_openai_response(content, model=model)
        resp_body["usage"]["prompt_tokens"] = tokens_prompt
        resp_body["usage"]["completion_tokens"] = max(
            resp_body["usage"]["completion_tokens"], tokens_completion
        )
        resp_body["usage"]["total_tokens"] = (
            resp_body["usage"]["prompt_tokens"]
            + resp_body["usage"]["completion_tokens"]
        )

        await record_metrics(
            model,
            stream_resolution,
            resp_body,
            latency_ms,
            prompt_hash=prompt_hash,
            prompt_text=prompt_text,
            route_decision=route_decision,
        )

        if (
            state.settings.cache_enabled
            and stream_state["status_code"] == 200
            and content
        ):
            try:
                usage = resp_body.get("usage", {})
                cost = (usage.get("prompt_tokens", 0) * 0.000005) + (
                    usage.get("completion_tokens", 0) * 0.000015
                )
                await state.cache_manager.store(
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
                comparison = await shadow_compare(
                    shadow_rule_hit, resp_body, prompt_text
                )
                await state.cache_manager.log_shadow(
                    rule_id=comparison["rule_id"],
                    prompt_text=prompt_text[:2000],
                    rule_response=comparison["rule_response"],
                    llm_response=comparison["llm_response"],
                    similarity=comparison["similarity"],
                    length_ratio=comparison["length_ratio"],
                    match_quality=comparison["match_quality"],
                )
                await apply_shadow_feedback(comparison, prompt_text)
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
        sse_headers["X-RuleShield-Complexity"] = str(
            route_decision.get("complexity_score", "")
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=sse_headers,
    )
