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


class TestAnyNode:
    def test_any_passes_when_one_child_passes(self, engine):
        tree = {"any": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "docker", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT
        assert kw == ["git"]

    def test_any_fails_when_no_child_passes(self, engine):
        tree = {"any": [
            {"type": "contains", "value": "docker", "field": "last_user_message"},
            {"type": "contains", "value": "k8s", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is False
        assert score == 0

    def test_any_sums_all_passing_children(self, engine):
        tree = {"any": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "commit", "field": "last_user_message"},
            {"type": "contains", "value": "nope", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git commit", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT * 2
        assert kw == ["git", "commit"]


class TestNotNode:
    def test_not_inverts_passing_child(self, engine):
        tree = {"not": {"type": "contains", "value": "git", "field": "last_user_message"}}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is False

    def test_not_inverts_failing_child(self, engine):
        tree = {"not": {"type": "contains", "value": "docker", "field": "last_user_message"}}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is True
        assert score == 0
        assert kw == []
        assert pat == []


class TestNesting:
    def test_three_deep_all_any_not(self, engine):
        """all > any > not evaluates correctly."""
        tree = {"all": [
            {"any": [
                {"type": "contains", "value": "git", "field": "last_user_message"},
                {"type": "regex", "value": "\\b(push|pull)\\b", "field": "last_user_message"},
            ]},
            {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git push origin", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT + PATTERN_WEIGHT
        assert "git" in kw

    def test_three_deep_blocked_by_not(self, engine):
        tree = {"all": [
            {"any": [
                {"type": "contains", "value": "git", "field": "last_user_message"},
            ]},
            {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(
            tree, "setup github actions workflow", 0,
        )
        assert passed is False


class TestWordBoundary:
    def test_matches_whole_word(self, engine):
        tree = {"type": "word_boundary", "value": "commit", "field": "last_user_message"}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git commit -m fix", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT
        assert kw == ["commit"]
        assert pat == []

    def test_rejects_partial_word(self, engine):
        tree = {"type": "word_boundary", "value": "commit", "field": "last_user_message"}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "recommit the changes", 0)
        assert passed is False

    def test_matches_at_boundaries(self, engine):
        tree = {"type": "word_boundary", "value": "are", "field": "last_user_message"}
        passed1, _, _, _ = engine._evaluate_condition_tree(tree, "are you there", 0)
        assert passed1 is True
        passed2, _, _, _ = engine._evaluate_condition_tree(tree, "beware of dogs", 0)
        assert passed2 is False


class TestStartsWith:
    def test_startswith_leaf_matches(self, engine):
        tree = {"type": "startswith", "value": "hey", "field": "last_user_message"}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "hey there", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT
        assert kw == ["hey"]

    def test_startswith_leaf_fails(self, engine):
        tree = {"type": "startswith", "value": "hey", "field": "last_user_message"}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "oh hey", 0)
        assert passed is False


class TestNotContains:
    def test_blocks_when_value_present(self, engine):
        tree = {"type": "not_contains", "value": "secret", "field": "last_user_message"}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "tell me the secret", 0)
        assert passed is False
        assert score == 0

    def test_passes_when_value_absent(self, engine):
        tree = {"type": "not_contains", "value": "secret", "field": "last_user_message"}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "hello world", 0)
        assert passed is True
        assert score == 0


class TestDepthLimit:
    def test_exceeding_depth_returns_false(self, engine):
        """11-deep tree should fail gracefully."""
        leaf = {"type": "contains", "value": "hello", "field": "last_user_message"}
        tree = leaf
        for _ in range(11):
            tree = {"all": [tree]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "hello", 0)
        assert passed is False
        assert score == 0


class TestScoreThresholdFiltering:
    def test_tree_passes_but_score_below_threshold(self, engine):
        """A tree of only not-gates passes with score 0 — should not fire."""
        rule = {
            "id": "only_not",
            "condition_tree": {
                "all": [
                    {"not": {"type": "contains", "value": "bad", "field": "last_user_message"}},
                ]
            },
            "response": {"content": "matched", "model": "ruleshield-rule"},
            "confidence": 0.95,
            "priority": 10,
            "enabled": True,
            "deployment": "production",
        }
        engine.rules = [rule]
        result = engine.match("hello world", model="gpt-4o-mini")
        assert result is None


class TestConditionLeafScoring:
    def test_max_length_contributes_condition_weight(self, engine):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "max_length", "value": 100, "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT + CONDITION_WEIGHT

    def test_min_length_contributes_condition_weight(self, engine):
        tree = {"all": [
            {"type": "regex", "value": "\\bgit\\b", "field": "last_user_message"},
            {"type": "min_length", "value": 3, "field": "last_user_message"},
        ]}
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git help", 0)
        assert passed is True
        assert score == PATTERN_WEIGHT + CONDITION_WEIGHT


class TestMaxMessages:
    def test_max_messages_uses_msg_count(self, engine):
        tree = {"type": "max_messages", "value": 5, "field": "last_user_message"}
        passed, score, _, _ = engine._evaluate_condition_tree(tree, "anything", 3)
        assert passed is True
        assert score == CONDITION_WEIGHT

    def test_max_messages_fails_when_exceeded(self, engine):
        tree = {"type": "max_messages", "value": 5, "field": "last_user_message"}
        passed, score, _, _ = engine._evaluate_condition_tree(tree, "anything", 10)
        assert passed is False


class TestBothFieldsPresent:
    def test_condition_tree_takes_priority_over_patterns(self, engine):
        """When both condition_tree and patterns exist, tree wins."""
        rule = {
            "id": "both_fields",
            "patterns": [
                {"type": "exact", "value": "hello", "field": "last_user_message"},
            ],
            "condition_tree": {
                "all": [
                    {"type": "exact", "value": "goodbye", "field": "last_user_message"},
                ]
            },
            "response": {"content": "tree wins", "model": "ruleshield-rule"},
            "confidence": 0.95,
            "priority": 10,
            "enabled": True,
            "deployment": "production",
        }
        engine.rules = [rule]
        result_hello = engine.match("hello", model="gpt-4o-mini")
        assert result_hello is None
        result_bye = engine.match("goodbye", model="gpt-4o-mini")
        assert result_bye is not None
        assert result_bye["rule_id"] == "both_fields"
