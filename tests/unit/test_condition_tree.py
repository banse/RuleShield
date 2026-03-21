"""Unit tests for RuleEngine._evaluate_condition_tree."""

import asyncio
import pytest
from ruleshield.rules import RuleEngine, KEYWORD_WEIGHT, PATTERN_WEIGHT, EXACT_WEIGHT, CONDITION_WEIGHT


@pytest.fixture
def engine():
    """Create a RuleEngine without loading rules from disk."""
    e = RuleEngine(rules_dir="/tmp/ruleshield-test-empty")
    e.rules = []
    e._loaded = True
    return e


class TestAllNode:
    def test_all_passes_when_all_children_pass(self, engine):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "help", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT * 2
        assert kw == ["git", "help"]
        assert pat == []

    def test_all_fails_when_one_child_fails(self, engine):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "docker", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is False
        assert score == 0
        assert kw == []

    def test_all_short_circuits_on_failure(self, engine):
        """all should not evaluate remaining children after a failure."""
        tree = {"all": [
            {"type": "contains", "value": "nope", "field": "last_user_message"},
            {"type": "contains", "value": "git", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is False
