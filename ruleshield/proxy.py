"""RuleShield Hermes -- FastAPI proxy server (compatibility shim).

This module re-exports the FastAPI ``app`` from ``ruleshield.app`` for
backward compatibility.  All implementation has been refactored into:

    ruleshield/app.py          -- FastAPI app creation, middleware, lifespan
    ruleshield/state.py        -- Shared mutable state (globals)
    ruleshield/helpers.py      -- Utility functions, model translation, metrics
    ruleshield/routes/
        api_routes.py          -- Dashboard API endpoints
        proxy_routes.py        -- /v1/chat/completions, /v1/completions, /v1/models
        codex_routes.py        -- Codex passthrough, /v1/{path} catch-all
        cron_routes.py         -- Cron optimization profile endpoints
        test_routes.py         -- Test monitor endpoints
"""

from __future__ import annotations

# Re-export the app so existing imports continue to work:
#   from ruleshield.proxy import app
from ruleshield.app import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    from ruleshield.config import load_settings

    _settings = load_settings()
    uvicorn.run(app, host="0.0.0.0", port=_settings.port, log_level=_settings.log_level)
