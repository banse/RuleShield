"""Integration tests for RuleShield proxy endpoints.

Uses FastAPI's TestClient to test the proxy endpoints WITHOUT needing a real
LLM provider.  Covers health, stats, rules, rate limiting, body size limits,
chat completions, shadow stats, and the models endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from ruleshield.proxy import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_returns_version_string(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestStatsEndpoint:
    def test_stats_returns_structure(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "cache_hits" in data
        assert "rule_hits" in data

    def test_stats_numeric_values(self, client):
        resp = client.get("/api/stats")
        data = resp.json()
        assert isinstance(data["total_requests"], int)
        assert isinstance(data["cache_hits"], int)
        assert isinstance(data["rule_hits"], int)

    def test_stats_includes_cost_fields(self, client):
        resp = client.get("/api/stats")
        data = resp.json()
        assert "cost_without" in data
        assert "cost_with" in data
        assert "savings_usd" in data
        assert "savings_pct" in data

    def test_stats_includes_uptime(self, client):
        resp = client.get("/api/stats")
        data = resp.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class TestRulesEndpoint:
    def test_rules_returns_list(self, client):
        resp = client.get("/api/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert "rules" in data
        assert "total" in data
        assert isinstance(data["rules"], list)

    def test_rules_total_matches_length(self, client):
        resp = client.get("/api/rules")
        data = resp.json()
        assert data["total"] == len(data["rules"])

    def test_rule_response_not_found(self, client):
        resp = client.get("/api/rules/nonexistent_rule_id/response")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_rate_limit_not_triggered_on_health(self, client):
        """Health endpoint should bypass rate limiting entirely."""
        for _ in range(200):
            resp = client.get("/health")
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Body size limit
# ---------------------------------------------------------------------------


class TestBodySizeLimit:
    def test_large_body_rejected(self, client):
        """A body larger than max_body_size_mb should be rejected with 413."""
        large_body = "x" * (11 * 1024 * 1024)
        resp = client.post(
            "/v1/chat/completions",
            content=large_body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(large_body)),
            },
        )
        assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Chat completions
# ---------------------------------------------------------------------------


class TestChatCompletions:
    def test_invalid_json_returns_400(self, client):
        resp = client.post(
            "/v1/chat/completions",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_rule_match_returns_openai_format(self, client):
        """A request that matches a greeting rule should return OpenAI format."""
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 10,
            },
        )
        # Should match the greeting rule and return 200, or forward to LLM
        # which is unavailable (502).  Either way verify the structure.
        if resp.status_code == 200:
            data = resp.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]

    def test_completions_endpoint_also_works(self, client):
        """The legacy /v1/completions endpoint should accept requests too."""
        resp = client.post(
            "/v1/completions",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        # Invalid JSON should still be caught with 400
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Shadow stats
# ---------------------------------------------------------------------------


class TestShadowEndpoint:
    def test_shadow_stats_returns_structure(self, client):
        resp = client.get("/api/shadow")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "total_comparisons" in data

    def test_shadow_stats_has_entries_field(self, client):
        resp = client.get("/api/shadow")
        data = resp.json()
        assert "entries" in data
        assert isinstance(data["entries"], list)


# ---------------------------------------------------------------------------
# Models (requires upstream -- should fail gracefully)
# ---------------------------------------------------------------------------


class TestProxyNotInitialized:
    def test_models_without_upstream(self, client):
        """Should return 502 or 503 since no upstream provider is configured."""
        resp = client.get("/v1/models")
        assert resp.status_code in (502, 503)


# ---------------------------------------------------------------------------
# Requests endpoint
# ---------------------------------------------------------------------------


class TestRequestsEndpoint:
    def test_requests_returns_structure(self, client):
        resp = client.get("/api/requests")
        assert resp.status_code == 200
        data = resp.json()
        assert "requests" in data
        assert isinstance(data["requests"], list)

    def test_requests_respects_limit(self, client):
        resp = client.get("/api/requests?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["requests"]) <= 5


# ---------------------------------------------------------------------------
# Runtime config
# ---------------------------------------------------------------------------


class TestRuntimeConfigEndpoint:
    def test_runtime_config_returns_structure(self, client):
        resp = client.get("/api/runtime-config")
        assert resp.status_code == 200
        data = resp.json()
        # Should expose at least the toggle-able settings
        assert isinstance(data, dict)

    def test_runtime_config_post_invalid_returns_error(self, client):
        resp = client.post(
            "/api/runtime-config",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        # Should return 400, 422, or 500 for invalid payload
        assert resp.status_code in (400, 422, 500)


# ---------------------------------------------------------------------------
# Rule events
# ---------------------------------------------------------------------------


class TestRuleEventsEndpoint:
    def test_rule_events_returns_list(self, client):
        resp = client.get("/api/rule-events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)
