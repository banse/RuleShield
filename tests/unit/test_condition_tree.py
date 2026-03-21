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
