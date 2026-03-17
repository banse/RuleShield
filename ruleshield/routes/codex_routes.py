"""Codex passthrough routes: /responses, /chat/completions, /v1/{path}.

Handles Codex Responses API and catch-all /v1/* passthrough with
full streaming support, cache/rule checking, and shadow mode.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from ruleshield import state
from ruleshield.helpers import (
    compute_codex_cost,
    estimate_cost,
    extract_codex_content,
    extract_codex_event_text,
    extract_prompt_text,
    forward_headers,
    record_metrics,
    resolve_upstream_for_model,
    select_codex_stream_text,
    shadow_compare,
    apply_shadow_feedback,
    translate_model_name,
    wrap_openai_response,
)

logger = logging.getLogger("ruleshield.proxy")

router = APIRouter()


# ---------------------------------------------------------------------------
# Codex Responses API passthrough
# ---------------------------------------------------------------------------


@router.api_route("/responses", methods=["POST"])
@router.api_route("/responses/{path:path}", methods=["GET", "POST", "DELETE"])
@router.api_route("/chat/completions", methods=["POST"])
async def proxy_codex_passthrough(request: Request, path: str = ""):
    """Transparent proxy for Codex-style endpoints without /v1/ prefix.

    Codex API uses {base_url}/responses instead of {base_url}/v1/responses.
    This catches those requests and forwards them to the upstream provider.
    """
    full_path = request.url.path
    endpoint = full_path
    headers = forward_headers(request)
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

    provider_url, headers, provider_error = resolve_upstream_for_model(
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

    logger.info(
        "Codex passthrough %s %s -> %s (model=%s)",
        method,
        endpoint,
        upstream_url,
        model,
    )

    if state.http_client is None:
        return JSONResponse(
            status_code=503, content={"error": "Proxy not initialized"}
        )
    try:
        headers["Content-Type"] = request.headers.get(
            "content-type", "application/json"
        )

        # Codex Responses API always streams
        is_stream = True
        if body_bytes:
            try:
                _bj = json.loads(body_bytes)
                is_stream = _bj.get("stream", True)
            except (json.JSONDecodeError, AttributeError):
                pass

        # --- Codex Cache/Rules check (requires codex_adapter) ---------------
        logger.debug(
            "Codex cache/rules check: adapter=%s, body=%d bytes, cache=%s, rules=%s",
            state.HAS_CODEX_ADAPTER,
            len(body_bytes) if body_bytes else 0,
            state.settings.cache_enabled,
            state.settings.rules_enabled,
        )
        if (
            state.HAS_CODEX_ADAPTER
            and body_bytes
            and (state.settings.cache_enabled or state.settings.rules_enabled)
        ):
            try:
                body_json = json.loads(body_bytes)
                codex_prompt = state.extract_prompt_from_codex(body_json)
                codex_messages = state.extract_messages_from_codex(body_json)

                # Extract the RAW user message for rule matching
                raw_input = body_json.get("input")
                if isinstance(raw_input, list):
                    raw_user_msg = ""
                    for item in reversed(raw_input):
                        if isinstance(item, dict) and item.get("role") == "user":
                            content = item.get("content", "")
                            raw_user_msg = (
                                content if isinstance(content, str) else str(content)
                            )
                            break
                elif isinstance(raw_input, str):
                    raw_user_msg = raw_input.strip()
                else:
                    raw_user_msg = ""

                logger.info(
                    "Codex prompt: full='%s', user_msg='%s'",
                    codex_prompt[:60] if codex_prompt else "(empty)",
                    raw_user_msg[:60] if raw_user_msg else "(empty)",
                )

                prompt_hash = state.extractor.hash_prompt(codex_prompt)

                if codex_prompt:
                    prompt_text = codex_prompt[:200]

                # 1. Cache check
                if state.settings.cache_enabled and codex_prompt:
                    cached = await state.cache_manager.check(
                        prompt_hash, codex_prompt
                    )
                    if cached is not None:
                        latency_ms = (time.monotonic() - t_start) * 1000
                        logger.info(
                            "Codex cache hit for: %s", codex_prompt[:50]
                        )
                        estimated_cost_val = estimate_cost(
                            cached.get("response", {})
                        )
                        await record_metrics(
                            model,
                            "cache",
                            cached.get("response", {}),
                            latency_ms,
                            prompt_hash=prompt_hash,
                            prompt_text=codex_prompt,
                            estimated_saving=estimated_cost_val,
                        )
                        if is_stream:
                            content = extract_codex_content(
                                cached.get("response", {})
                            )
                            events = state.wrap_codex_streaming_response(
                                content, model="ruleshield-cache"
                            )

                            async def cache_stream():
                                for event in events:
                                    yield event

                            return StreamingResponse(
                                cache_stream(),
                                media_type="text/event-stream",
                                headers={
                                    "X-RuleShield-Resolution": "cache"
                                },
                            )
                        else:
                            content = extract_codex_content(
                                cached.get("response", {})
                            )
                            return JSONResponse(
                                content=state.wrap_codex_response(
                                    content, model="ruleshield-cache"
                                ),
                                headers={
                                    "X-RuleShield-Resolution": "cache"
                                },
                            )

                # 2. Rule check
                rule_prompt = raw_user_msg or codex_prompt
                shadow_confidence_floor = (
                    state.settings.shadow_test_confidence_floor
                    if state.settings.shadow_mode
                    and state.settings.shadow_test_confidence_floor > 0.0
                    else None
                )
                if state.settings.rules_enabled and rule_prompt:
                    rule_hit = await state.rule_engine.async_match(
                        rule_prompt,
                        messages=codex_messages,
                        model=model,
                        confidence_floor=shadow_confidence_floor,
                    )
                    if rule_hit is not None:
                        if state.settings.shadow_mode:
                            shadow_rule_hit = rule_hit
                            logger.info(
                                "Codex shadow mode: rule '%s' matched but forwarding upstream",
                                rule_hit.get(
                                    "rule_name",
                                    rule_hit.get("rule_id", "unknown"),
                                ),
                            )
                        else:
                            latency_ms = (time.monotonic() - t_start) * 1000
                            logger.info(
                                "Codex rule hit: %s -> %s",
                                codex_prompt[:50],
                                rule_hit.get(
                                    "rule_name",
                                    rule_hit.get("rule_id", "unknown"),
                                ),
                            )
                            raw_response = rule_hit.get("response", {})
                            content = raw_response.get(
                                "content", str(raw_response)
                            )
                            estimated_cost_val = 0.001
                            await record_metrics(
                                model,
                                "rule",
                                raw_response,
                                latency_ms,
                                prompt_hash=prompt_hash,
                                prompt_text=codex_prompt,
                                estimated_saving=estimated_cost_val,
                            )
                            if is_stream:
                                events = state.wrap_codex_streaming_response(
                                    content, model="ruleshield-rule"
                                )

                                async def rule_stream():
                                    for event in events:
                                        yield event

                                return StreamingResponse(
                                    rule_stream(),
                                    media_type="text/event-stream",
                                    headers={
                                        "X-RuleShield-Resolution": "rule"
                                    },
                                )
                            else:
                                return JSONResponse(
                                    content=state.wrap_codex_response(
                                        content, model="ruleshield-rule"
                                    ),
                                    headers={
                                        "X-RuleShield-Resolution": "rule"
                                    },
                                )
                    elif state.settings.shadow_mode:
                        candidate_hit = (
                            await state.rule_engine.async_match_candidates(
                                rule_prompt,
                                messages=codex_messages,
                                model=model,
                                confidence_floor=shadow_confidence_floor,
                            )
                        )
                        if candidate_hit is not None:
                            shadow_rule_hit = candidate_hit
                            logger.info(
                                "Codex shadow mode: candidate rule '%s' matched for comparison",
                                candidate_hit.get("rule_id", "unknown"),
                            )
            except Exception as exc:
                logger.warning(
                    "Codex cache/rule check failed (proceeding to upstream): %s",
                    exc,
                )

        # --- End Codex Cache/Rules check ------------------------------------

        if is_stream:
            stream_state: dict[str, Any] = {
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
                "content_parts": [],
                "fallback_texts": [],
                "completed": False,
            }

            async def stream_and_track():
                async with state.http_client.stream(
                    method, upstream_url, headers=headers, content=body_bytes
                ) as resp:
                    async for line in resp.aiter_lines():
                        yield f"{line}\n"

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
                            fallback_text = extract_codex_event_text(event_data)
                            if fallback_text:
                                stream_state["fallback_texts"].append(
                                    fallback_text
                                )

                        if event_type == "response.completed":
                            response_obj = event_data.get("response", {})
                            usage = response_obj.get("usage", {})
                            stream_state["tokens_in"] = usage.get(
                                "input_tokens", 0
                            )
                            stream_state["tokens_out"] = usage.get(
                                "output_tokens", 0
                            )
                            stream_state["cost"] = compute_codex_cost(
                                model,
                                stream_state["tokens_in"],
                                stream_state["tokens_out"],
                            )
                            stream_state["completed"] = True

            async def _log_after_stream():
                try:
                    latency_ms = (time.monotonic() - t_start) * 1000
                    tokens_in = stream_state["tokens_in"]
                    tokens_out = stream_state["tokens_out"]
                    cost = stream_state["cost"]
                    content = select_codex_stream_text(stream_state)

                    logger.info(
                        "Codex stream completed: %d in / %d out tokens, $%.6f, %.0fms",
                        tokens_in,
                        tokens_out,
                        cost,
                        latency_ms,
                    )

                    codex_ph = ""
                    if state.HAS_CODEX_ADAPTER and prompt_text:
                        codex_ph = state.extractor.hash_prompt(prompt_text)

                    await state.cache_manager.log_request(
                        prompt_hash=codex_ph,
                        prompt_text=(
                            f"[codex] {prompt_text}"
                            if prompt_text
                            else "[codex]"
                        ),
                        response={"content": content[:500]},
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost=cost,
                        resolution_type="passthrough",
                        latency_ms=int(latency_ms),
                    )

                    if (
                        state.settings.cache_enabled
                        and content
                        and codex_ph
                    ):
                        try:
                            await state.cache_manager.store(
                                prompt_hash=codex_ph,
                                prompt_text=prompt_text,
                                response={"content": content},
                                model=model,
                                tokens_in=tokens_in,
                                tokens_out=tokens_out,
                                cost=cost,
                            )
                        except Exception as store_exc:
                            logger.warning(
                                "Codex cache store failed: %s", store_exc
                            )

                    if shadow_rule_hit is not None and content:
                        try:
                            comparison = await shadow_compare(
                                shadow_rule_hit,
                                wrap_openai_response(content, model=model),
                                raw_user_msg or codex_prompt or prompt_text,
                            )
                            await state.cache_manager.log_shadow(
                                rule_id=comparison["rule_id"],
                                prompt_text=(
                                    raw_user_msg
                                    or codex_prompt
                                    or prompt_text
                                )[:2000],
                                rule_response=comparison["rule_response"],
                                llm_response=comparison["llm_response"],
                                similarity=comparison["similarity"],
                                length_ratio=comparison["length_ratio"],
                                match_quality=comparison["match_quality"],
                            )
                            await apply_shadow_feedback(
                                comparison,
                                raw_user_msg or codex_prompt or prompt_text,
                            )
                            logger.info(
                                "Codex shadow comparison (stream): rule=%s similarity=%.3f quality=%s",
                                comparison["rule_id"],
                                comparison["similarity"],
                                comparison["match_quality"],
                            )
                        except Exception as shadow_exc:
                            logger.warning(
                                "Codex streaming shadow comparison failed: %s",
                                shadow_exc,
                            )
                except Exception as log_exc:
                    logger.error(
                        "Failed to log Codex stream metrics: %s", log_exc
                    )

            stream_headers = {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-RuleShield-Resolution": "passthrough",
            }
            if shadow_rule_hit is not None:
                stream_headers["X-RuleShield-Shadow"] = shadow_rule_hit.get(
                    "rule_id", ""
                )

            response = StreamingResponse(
                stream_and_track(),
                media_type="text/event-stream",
                headers=stream_headers,
                background=BackgroundTask(_log_after_stream),
            )
            return response
        else:
            resp = await state.http_client.request(
                method, upstream_url, headers=headers, content=body_bytes
            )
            latency_ms = (time.monotonic() - t_start) * 1000

            tokens_in = 0
            tokens_out = 0
            cost = 0.0
            resp_json: dict = {}
            try:
                resp_json = resp.json()
                usage = resp_json.get("usage", {})
                tokens_in = usage.get("input_tokens", 0)
                tokens_out = usage.get("output_tokens", 0)
                cost = compute_codex_cost(model, tokens_in, tokens_out)
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass

            logger.info(
                "Codex passthrough completed: %d in %.0fms, %d/%d tokens, $%.6f",
                resp.status_code,
                latency_ms,
                tokens_in,
                tokens_out,
                cost,
            )

            codex_ph = ""
            if state.HAS_CODEX_ADAPTER and prompt_text:
                codex_ph = state.extractor.hash_prompt(prompt_text)

            try:
                await state.cache_manager.log_request(
                    prompt_hash=codex_ph,
                    prompt_text=(
                        f"[codex] {prompt_text}"
                        if prompt_text
                        else f"[codex] {endpoint}"
                    ),
                    response=resp_json,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    resolution_type="passthrough",
                    latency_ms=int(latency_ms),
                )
            except Exception:
                pass

            # Store in cache
            if (
                state.settings.cache_enabled
                and resp.status_code == 200
                and codex_ph
                and resp_json
            ):
                try:
                    await state.cache_manager.store(
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
                    content = extract_codex_content(resp_json)
                    comparison = await shadow_compare(
                        shadow_rule_hit,
                        wrap_openai_response(content, model=model),
                        raw_user_msg or codex_prompt or prompt_text,
                    )
                    await state.cache_manager.log_shadow(
                        rule_id=comparison["rule_id"],
                        prompt_text=(
                            raw_user_msg or codex_prompt or prompt_text
                        )[:2000],
                        rule_response=comparison["rule_response"],
                        llm_response=comparison["llm_response"],
                        similarity=comparison["similarity"],
                        length_ratio=comparison["length_ratio"],
                        match_quality=comparison["match_quality"],
                    )
                    await apply_shadow_feedback(
                        comparison,
                        raw_user_msg or codex_prompt or prompt_text,
                    )
                    response_headers["X-RuleShield-Shadow"] = comparison[
                        "rule_id"
                    ]
                    logger.info(
                        "Codex shadow comparison: rule=%s similarity=%.3f quality=%s",
                        comparison["rule_id"],
                        comparison["similarity"],
                        comparison["match_quality"],
                    )
                except Exception as shadow_exc:
                    logger.warning(
                        "Codex shadow comparison failed: %s", shadow_exc
                    )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get(
                    "content-type", "application/json"
                ),
                headers=response_headers,
            )
    except Exception as exc:
        logger.error("Codex passthrough error for %s: %s", endpoint, exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": {"message": "Upstream error", "type": "proxy_error"}
            },
        )


# ---------------------------------------------------------------------------
# Catch-all /v1/* passthrough
# ---------------------------------------------------------------------------


@router.api_route(
    "/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy_passthrough(request: Request, path: str):
    """Transparent proxy for any /v1/* endpoint not explicitly handled."""
    endpoint = f"/v1/{path}"
    headers = forward_headers(request)

    body_bytes = await request.body()
    method = request.method.upper()

    t_start = time.monotonic()
    model = "unknown"
    prompt_text = ""
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

    provider_url, headers, provider_error = resolve_upstream_for_model(
        model=model,
        request=request,
        headers=headers,
    )
    if provider_error:
        return JSONResponse(
            status_code=400, content={"detail": provider_error}
        )
    upstream_url = f"{provider_url.rstrip('/')}{endpoint}"
    logger.info(
        "Passthrough %s %s -> %s (model=%s)",
        method,
        endpoint,
        upstream_url,
        model,
    )

    if state.http_client is None:
        return JSONResponse(
            status_code=503, content={"error": "Proxy not initialized"}
        )
    try:
        if method == "GET":
            resp = await state.http_client.get(upstream_url, headers=headers)
        else:
            headers["Content-Type"] = request.headers.get(
                "content-type", "application/json"
            )
            is_stream = False
            if body_bytes:
                try:
                    body_json = json.loads(body_bytes)
                    is_stream = body_json.get("stream", False)
                    if "model" in body_json:
                        body_json["model"] = translate_model_name(
                            body_json["model"], provider_url
                        )
                        body_bytes = json.dumps(body_json).encode()
                except (json.JSONDecodeError, AttributeError):
                    pass

            if is_stream:

                async def stream_generator():
                    async with state.http_client.stream(
                        method,
                        upstream_url,
                        headers=headers,
                        content=body_bytes,
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
                resp = await state.http_client.request(
                    method,
                    upstream_url,
                    headers=headers,
                    content=body_bytes,
                )

        latency_ms = (time.monotonic() - t_start) * 1000
        logger.info(
            "Passthrough %s completed: %d in %.0fms (model=%s)",
            endpoint,
            resp.status_code,
            latency_ms,
            model,
        )

        try:
            await state.cache_manager.log_request(
                prompt_hash="",
                prompt_text=(
                    f"[passthrough] {prompt_text}"
                    if prompt_text
                    else f"[passthrough] {endpoint}"
                ),
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
            content={
                "error": {"message": "Upstream error", "type": "proxy_error"}
            },
        )
