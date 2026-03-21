"""Tests for rulecore RuleEngine."""
import json
import os
import tempfile
import shutil

import pytest
from rulecore.engine import RuleEngine
from rulecore.types import ScoringConfig, MatchResult


@pytest.fixture
def rules_dir():
    tmpdir = tempfile.mkdtemp(prefix="rulecore-test-")
    rules = [
        {"id": "greet", "patterns": [{"type": "exact", "value": "hello", "field": "text"}],
         "conditions": [{"type": "max_length", "value": 20, "field": "text"}],
         "response": {"content": "hi!"}, "confidence": 0.95, "priority": 10, "enabled": True},
        {"id": "git_tree", "condition_tree": {"all": [
            {"type": "contains", "value": "git", "field": "text"},
            {"type": "regex", "value": "\\b(push|pull|commit)\\b", "field": "text"},
            {"not": {"type": "contains", "value": "actions", "field": "text"}},
        ]}, "response": {"content": "git help"}, "confidence": 0.88, "priority": 7, "enabled": True},
        {"id": "low_conf", "patterns": [{"type": "exact", "value": "test", "field": "text"}],
         "response": {"content": "tested"}, "confidence": 0.3, "priority": 5, "enabled": True},
    ]
    with open(os.path.join(tmpdir, "rules.json"), "w") as f:
        json.dump(rules, f)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def engine(rules_dir):
    e = RuleEngine(rules_dir=rules_dir)
    e.load()
    return e


class TestMatch:
    def test_exact_match(self, engine):
        result = engine.match(context={"text": "hello"})
        assert result is not None
        assert isinstance(result, MatchResult)
        assert result.rule_id == "greet"

    def test_condition_tree_match(self, engine):
        result = engine.match(context={"text": "git push"})
        assert result is not None
        assert result.rule_id == "git_tree"

    def test_condition_tree_blocked_by_not(self, engine):
        result = engine.match(context={"text": "git actions workflow"})
        assert result is None

    def test_no_match(self, engine):
        result = engine.match(context={"text": "something random that matches nothing"})
        assert result is None

    def test_confidence_threshold_filters(self, engine):
        result = engine.match(context={"text": "test"}, confidence_threshold=0.5)
        assert result is None

    def test_deactivation_threshold(self, engine):
        result = engine.match(context={"text": "test"})
        assert result is None

    def test_priority_ordering(self, engine):
        engine.rules.append({
            "id": "greet2", "patterns": [{"type": "exact", "value": "hello", "field": "text"}],
            "response": {"content": "hi2"}, "confidence": 0.95, "priority": 5, "enabled": True,
        })
        result = engine.match(context={"text": "hello"})
        assert result.rule_id == "greet"

    def test_flat_rule_condition_failure(self, engine):
        result = engine.match(context={"text": "hello world is a long greeting"})
        assert result is None

    def test_match_candidates(self, engine):
        engine.rules.append({
            "id": "cand1", "patterns": [{"type": "exact", "value": "test", "field": "text"}],
            "response": {"content": "ok"}, "confidence": 0.95, "priority": 5,
            "enabled": True, "deployment": "candidate",
        })
        result = engine.match(context={"text": "test"})
        assert result is None or result.rule_id != "cand1"
        result = engine.match_candidates(context={"text": "test"})
        assert result is not None
        assert result.rule_id == "cand1"

    def test_hit_count_increments(self, engine):
        engine.match(context={"text": "hello"})
        greet = next(r for r in engine.rules if r["id"] == "greet")
        assert greet["hit_count"] == 1

    def test_custom_scoring(self, rules_dir):
        e = RuleEngine(rules_dir=rules_dir, scoring=ScoringConfig(min_score=0.5))
        e.load()
        assert e.scoring.min_score == 0.5


class TestRuleManagement:
    def test_add_rule(self, engine):
        engine.add_rule({"id": "new", "patterns": [{"type": "exact", "value": "new", "field": "text"}], "response": {"content": "ok"}})
        ids = [r["id"] for r in engine.rules]
        assert "new" in ids

    def test_update_confidence(self, engine):
        engine.update_confidence("greet", 0.5)
        greet = next(r for r in engine.rules if r["id"] == "greet")
        assert greet["confidence"] == 0.5

    def test_deactivate_rule(self, engine):
        engine.deactivate_rule("greet")
        greet = next(r for r in engine.rules if r["id"] == "greet")
        assert greet["enabled"] is False

    def test_get_active_rules(self, engine):
        active = engine.get_active_rules()
        assert all(r["enabled"] for r in active)
        tree_rule = next((r for r in active if r["id"] == "git_tree"), None)
        if tree_rule:
            assert tree_rule["has_condition_tree"] is True

    def test_get_stats(self, engine):
        stats = engine.get_stats()
        assert "total_rules" in stats
        assert "total_hits" in stats
