"""Integration tests: free model enforcement + rulecore adapter with Hermes flow.

Validates that:
1. RuleShield's rulecore adapter still matches rules correctly
2. Smart Router enforces free models for OpenRouter provider
3. Codex/expensive model requests get rewritten to free models
4. End-to-end proxy flow uses free models only
"""

import asyncio
import json
import os
import tempfile
import shutil

import pytest
from ruleshield.rules import RuleEngine, _get_model_threshold, _extract_last_user_message
from ruleshield.router import SmartRouter, ComplexityClassifier


# ---------------------------------------------------------------------------
# Free model constants
# ---------------------------------------------------------------------------

FREE_PRIMARY = "nvidia/nemotron-3-super-120b-a12b:free"
FREE_FALLBACK = "minimax/minimax-m2.5:free"
EXPENSIVE_CODEX = "gpt-5.3-codex"
EXPENSIVE_OPUS = "claude-opus-4-6"


# ---------------------------------------------------------------------------
# Test: Rulecore adapter still works correctly
# ---------------------------------------------------------------------------


class TestRulecoreAdapterMatch:
    """Verify the rulecore-backed RuleEngine matches identically to before."""

    @pytest.fixture
    def engine(self):
        e = RuleEngine(rules_dir="/tmp/ruleshield-test-empty")
        e.rules = [
            {
                "id": "greeting",
                "patterns": [
                    {"type": "exact", "value": "hello", "field": "last_user_message"},
                    {"type": "exact", "value": "hi", "field": "last_user_message"},
                ],
                "conditions": [
                    {"type": "max_length", "value": 10, "field": "last_user_message"},
                ],
                "response": {"content": "Hello! How can I help?", "model": "ruleshield-rule"},
                "confidence": 0.95,
                "priority": 10,
                "enabled": True,
                "deployment": "production",
            },
            {
                "id": "git_tree",
                "condition_tree": {
                    "all": [
                        {"any": [
                            {"type": "contains", "value": "git", "field": "last_user_message"},
                            {"type": "regex", "value": "\\b(push|pull|commit)\\b", "field": "last_user_message"},
                        ]},
                        {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
                    ]
                },
                "response": {"content": "I can help with git.", "model": "ruleshield-rule"},
                "confidence": 0.88,
                "priority": 7,
                "enabled": True,
                "deployment": "production",
            },
        ]
        e._loaded = True
        return e

    def test_flat_rule_matches(self, engine):
        """Rulecore adapter matches flat rules with exact same API."""
        result = engine.match("hello", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "greeting"
        assert result["response"]["content"] == "Hello! How can I help?"
        assert isinstance(result, dict)  # NOT MatchResult dataclass

    def test_condition_tree_matches(self, engine):
        """Rulecore adapter matches condition_tree rules."""
        result = engine.match("git push origin main", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "git_tree"

    def test_condition_tree_not_blocks(self, engine):
        """Not node in condition_tree blocks correctly."""
        result = engine.match("setup github actions for git", model="gpt-4o-mini")
        assert result is None

    def test_model_threshold_applied(self, engine):
        """Model-aware thresholds filter rules by confidence."""
        # Opus requires 0.90 threshold, git_tree has 0.88 confidence
        result = engine.match("git push", model="claude-opus-4-6")
        assert result is None  # 0.88 < 0.90 threshold

    def test_async_match_works(self, engine):
        """Async wrapper still works after rulecore migration."""
        result = asyncio.run(
            engine.async_match("hello", model="gpt-4o-mini")
        )
        assert result is not None
        assert result["rule_id"] == "greeting"

    def test_returns_dict_not_dataclass(self, engine):
        """Match result must be a plain dict for proxy.py compat."""
        result = engine.match("hello", model="gpt-4o-mini")
        assert isinstance(result, dict)
        assert "rule_id" in result
        assert "response" in result
        assert "match_score" in result
        assert "model_threshold" in result

    def test_hit_count_tracks(self, engine):
        """Hit counting works through rulecore adapter."""
        engine.match("hello", model="gpt-4o-mini")
        engine.match("hello", model="gpt-4o-mini")
        greeting = next(r for r in engine.rules if r["id"] == "greeting")
        assert greeting["hit_count"] == 2


# ---------------------------------------------------------------------------
# Test: Free model enforcement in Smart Router
# ---------------------------------------------------------------------------


class TestFreeModelEnforcement:
    """Verify the router enforces free models and blocks expensive ones."""

    @pytest.fixture
    def router(self):
        return SmartRouter(config={
            "model_map": {
                "openrouter": {
                    "cheap": FREE_PRIMARY,
                    "mid": FREE_PRIMARY,
                    "premium": FREE_FALLBACK,
                },
            },
            "free_model_enforcement": {
                "enabled": True,
                "allowed_models": [FREE_PRIMARY, FREE_FALLBACK],
                "default_model": FREE_PRIMARY,
            },
        })

    def test_simple_prompt_gets_free_model(self, router):
        """Simple prompts route to cheap free model."""
        result = router.route(
            "hello", None, EXPENSIVE_CODEX,
            provider_url="https://openrouter.ai/api/v1",
        )
        assert result["routed"] is True
        assert result["model"] == FREE_PRIMARY

    def test_complex_prompt_gets_free_fallback(self, router):
        """Complex prompts route to free fallback, not expensive model."""
        complex_prompt = (
            "Analyze the entire codebase, find all security vulnerabilities, "
            "compare with OWASP top 10, create a detailed remediation plan "
            "with priority levels and estimated effort for each finding. "
            "First review auth, then data validation, then API endpoints."
        )
        result = router.route(
            complex_prompt, None, EXPENSIVE_CODEX,
            provider_url="https://openrouter.ai/api/v1",
        )
        # Should route to free model regardless of complexity
        assert result["model"] in (FREE_PRIMARY, FREE_FALLBACK)

    def test_codex_model_gets_replaced(self, router):
        """gpt-5.3-codex must be replaced with free model."""
        result = router.route(
            "what is python?", None, EXPENSIVE_CODEX,
            provider_url="https://openrouter.ai/api/v1",
        )
        assert result["model"] != EXPENSIVE_CODEX
        assert result["model"] in (FREE_PRIMARY, FREE_FALLBACK)

    def test_opus_model_gets_replaced(self, router):
        """claude-opus must be replaced with free model."""
        result = router.route(
            "hello", None, EXPENSIVE_OPUS,
            provider_url="https://openrouter.ai/api/v1",
        )
        assert result["model"] != EXPENSIVE_OPUS

    def test_already_free_model_not_rerouted(self, router):
        """If model is already free, don't change it."""
        result = router.route(
            "hello", None, FREE_PRIMARY,
            provider_url="https://openrouter.ai/api/v1",
        )
        # Either not routed (kept as-is) or routed to same model
        if result["routed"]:
            assert result["model"] == FREE_PRIMARY

    def test_enforcement_blocks_unknown_expensive_model(self):
        """Free model enforcement blocks ANY model not in allowlist."""
        router = SmartRouter(config={
            "free_model_enforcement": {
                "enabled": True,
                "allowed_models": [FREE_PRIMARY, FREE_FALLBACK],
                "default_model": FREE_PRIMARY,
            },
        })
        # Even without model_map override, enforcement catches it
        result = router.route(
            "hello", None, "some-random-expensive-model",
            provider_url="https://openrouter.ai/api/v1",
        )
        assert result["routed"] is True
        assert result["model"] == FREE_PRIMARY
        assert "FREE ENFORCEMENT" in result["reason"]

    def test_enforcement_disabled_allows_expensive(self):
        """When enforcement is disabled, expensive models pass through."""
        router = SmartRouter(config={
            "free_model_enforcement": {
                "enabled": False,
                "allowed_models": [FREE_PRIMARY],
                "default_model": FREE_PRIMARY,
            },
        })
        result = router.route(
            "hello", None, EXPENSIVE_CODEX,
            provider_url="https://openrouter.ai/api/v1",
        )
        # Without enforcement, router may or may not route based on model_map
        # but it won't force to free model
        if result["routed"]:
            assert "FREE ENFORCEMENT" not in result["reason"]


# ---------------------------------------------------------------------------
# Test: Model threshold functions preserved
# ---------------------------------------------------------------------------


class TestModelThresholds:
    """Verify _get_model_threshold still works after adapter migration."""

    def test_free_nvidia_model_threshold(self):
        """Free nvidia model should get a reasonable threshold."""
        threshold = _get_model_threshold(FREE_PRIMARY)
        assert 0.4 <= threshold <= 0.9

    def test_codex_model_threshold(self):
        threshold = _get_model_threshold("gpt-5.3-codex")
        assert threshold == 0.70

    def test_opus_threshold(self):
        threshold = _get_model_threshold("claude-opus-4-6")
        assert threshold == 0.90

    def test_haiku_threshold(self):
        threshold = _get_model_threshold("claude-haiku-4-5")
        assert threshold == 0.60


class TestExtractLastUserMessage:
    """Verify _extract_last_user_message works after adapter migration."""

    def test_simple_messages(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hello"},
        ]
        assert _extract_last_user_message(messages) == "hello"

    def test_multipart_content(self):
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "describe this"},
                {"type": "image_url", "image_url": {"url": "http://..."}},
            ]},
        ]
        assert _extract_last_user_message(messages) == "describe this"

    def test_empty_messages(self):
        assert _extract_last_user_message(None) == ""
        assert _extract_last_user_message([]) == ""


# ---------------------------------------------------------------------------
# Test: End-to-end rule loading with rulecore
# ---------------------------------------------------------------------------


class TestEndToEndRuleLoading:
    """Verify rules load from JSON files through rulecore adapter."""

    @pytest.fixture
    def rules_dir(self):
        tmpdir = tempfile.mkdtemp(prefix="ruleshield-e2e-")
        rules = [
            {
                "id": "e2e_greeting",
                "patterns": [{"type": "exact", "value": "hi", "field": "last_user_message"}],
                "conditions": [{"type": "max_length", "value": 5, "field": "last_user_message"}],
                "response": {"content": "Hey!", "model": "ruleshield-rule"},
                "confidence": 0.95, "priority": 10, "enabled": True,
            },
            {
                "id": "e2e_tree_rule",
                "condition_tree": {
                    "all": [
                        {"type": "word_boundary", "value": "help", "field": "last_user_message"},
                        {"type": "max_length", "value": 50, "field": "last_user_message"},
                    ]
                },
                "response": {"content": "How can I help?", "model": "ruleshield-rule"},
                "confidence": 0.90, "priority": 5, "enabled": True,
            },
        ]
        with open(os.path.join(tmpdir, "test_rules.json"), "w") as f:
            json.dump(rules, f)
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_load_and_match_flat(self, rules_dir):
        engine = RuleEngine(rules_dir=rules_dir)
        asyncio.run(engine.init(rules_dir))
        result = engine.match("hi", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "e2e_greeting"

    def test_load_and_match_tree(self, rules_dir):
        engine = RuleEngine(rules_dir=rules_dir)
        asyncio.run(engine.init(rules_dir))
        result = engine.match("I need help please", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "e2e_tree_rule"

    def test_get_active_rules(self, rules_dir):
        engine = RuleEngine(rules_dir=rules_dir)
        asyncio.run(engine.init(rules_dir))
        active = engine.get_active_rules()
        assert len(active) == 2
        tree_rule = next(r for r in active if r["id"] == "e2e_tree_rule")
        assert tree_rule["has_condition_tree"] is True

    def test_get_stats(self, rules_dir):
        engine = RuleEngine(rules_dir=rules_dir)
        asyncio.run(engine.init(rules_dir))
        engine.match("hi", model="gpt-4o-mini")
        stats = engine.get_stats()
        assert stats["total_rules"] == 2
        assert stats["total_hits"] == 1
