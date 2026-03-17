"""RuleShield Hermes -- FastAPI application factory.

Creates the FastAPI app, configures middleware, registers all route
modules, and manages the startup/shutdown lifespan.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ruleshield import state
from ruleshield.config import load_settings
from ruleshield.helpers import rate_limiter
from ruleshield.router import SmartRouter

from ruleshield.routes import api_routes, codex_routes, cron_routes, proxy_routes, test_routes

logger = logging.getLogger("ruleshield.proxy")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    state.settings = load_settings()

    logging.basicConfig(
        level=getattr(logging, state.settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "RuleShield Hermes proxy starting -- provider=%s port=%s",
        state.settings.provider_url,
        state.settings.port,
    )

    # Initialise subsystems.
    await state.cache_manager.init()
    await state.rule_engine.init(rules_dir=state.settings.rules_dir)
    await state.extractor.init()
    await state.metrics.init()

    from ruleshield.feedback import RuleFeedback

    state.feedback_manager = RuleFeedback(state.rule_engine)
    await state.feedback_manager.init()

    if state.settings.router_enabled:
        state.smart_router = SmartRouter(config=state.settings.router_config or None)
        logger.info("Smart Router enabled -- complexity-based model routing active")

    if state.settings.slack_webhook:
        from ruleshield.integrations.slack import SlackNotifier

        state.slack_notifier = SlackNotifier(webhook_url=state.settings.slack_webhook)
        logger.info("Slack notifications enabled")

    state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )

    yield

    # Shutdown.
    if state.feedback_manager is not None:
        await state.feedback_manager.close()
    if state.cache_manager is not None:
        await state.cache_manager.close()
    if state.http_client:
        await state.http_client.aclose()
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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(ip):
        logger.warning("Rate limit exceeded for %s", ip)
        return JSONResponse(
            status_code=429, content={"error": "Rate limit exceeded"}
        )
    return await call_next(request)


@app.middleware("http")
async def body_size_middleware(request: Request, call_next):
    cl = request.headers.get("content-length")
    max_bytes = getattr(state.settings, "max_body_size_mb", 10) * 1024 * 1024
    if cl and int(cl) > max_bytes:
        return JSONResponse(
            status_code=413, content={"error": "Request body too large"}
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Mount route modules
# ---------------------------------------------------------------------------
# IMPORTANT: Order matters for route matching. More specific routes must be
# registered before catch-all routes. proxy_routes (/v1/chat/completions,
# /v1/completions, /v1/models) must come before codex_routes which has the
# catch-all /v1/{path:path}.

app.include_router(api_routes.router)
app.include_router(test_routes.router)
app.include_router(cron_routes.router)
app.include_router(proxy_routes.router)
app.include_router(codex_routes.router)  # Must be last (has catch-all routes)
