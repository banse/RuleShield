"""Unit tests for condition tree evaluation (via rulecore)."""

import asyncio
import pytest
from rulecore.types import ScoringConfig
from rulecore.conditions import evaluate_condition_tree, validate_condition_tree
from ruleshield.rules import RuleEngine, KEYWORD_WEIGHT, PATTERN_WEIGHT, EXACT_WEIGHT, CONDITION_WEIGHT

_CFG = ScoringConfig()


def _ctx(text, msg_count=0):
    """Build a context dict matching RuleShield's convention."""
    return {"last_user_message": text, "msg_count": msg_count}


@pytest.fixture
def engine():
    """Create a RuleEngine without loading rules from disk."""
    e = RuleEngine(rules_dir="/tmp/ruleshield-test-empty")
    e.rules = []
    e._loaded = True
    return e


class TestAllNode:
    def test_all_passes_when_all_children_pass(self):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "help", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT * 2
        assert kw == ["git", "help"]
        assert pat == []

    def test_all_fails_when_one_child_fails(self):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "docker", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is False
        assert score == 0
        assert kw == []

    def test_all_short_circuits_on_failure(self):
        tree = {"all": [
            {"type": "contains", "value": "nope", "field": "last_user_message"},
            {"type": "contains", "value": "git", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is False


class TestAnyNode:
    def test_any_passes_when_one_child_passes(self):
        tree = {"any": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "docker", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT
        assert kw == ["git"]

    def test_any_fails_when_no_child_passes(self):
        tree = {"any": [
            {"type": "contains", "value": "docker", "field": "last_user_message"},
            {"type": "contains", "value": "k8s", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is False
        assert score == 0

    def test_any_sums_all_passing_children(self):
        tree = {"any": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "contains", "value": "commit", "field": "last_user_message"},
            {"type": "contains", "value": "nope", "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git commit"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT * 2
        assert kw == ["git", "commit"]


class TestNotNode:
    def test_not_inverts_passing_child(self):
        tree = {"not": {"type": "contains", "value": "git", "field": "last_user_message"}}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is False

    def test_not_inverts_failing_child(self):
        tree = {"not": {"type": "contains", "value": "docker", "field": "last_user_message"}}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is True
        assert score == 0
        assert kw == []
        assert pat == []


class TestNesting:
    def test_three_deep_all_any_not(self):
        tree = {"all": [
            {"any": [
                {"type": "contains", "value": "git", "field": "last_user_message"},
                {"type": "regex", "value": "\\b(push|pull)\\b", "field": "last_user_message"},
            ]},
            {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git push origin"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT + PATTERN_WEIGHT
        assert "git" in kw

    def test_three_deep_blocked_by_not(self):
        tree = {"all": [
            {"any": [
                {"type": "contains", "value": "git", "field": "last_user_message"},
            ]},
            {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(
            tree, _ctx("setup github actions workflow"), _CFG,
        )
        assert passed is False


class TestWordBoundary:
    def test_matches_whole_word(self):
        tree = {"type": "word_boundary", "value": "commit", "field": "last_user_message"}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git commit -m fix"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT
        assert kw == ["commit"]
        assert pat == []

    def test_rejects_partial_word(self):
        tree = {"type": "word_boundary", "value": "commit", "field": "last_user_message"}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("recommit the changes"), _CFG)
        assert passed is False

    def test_matches_at_boundaries(self):
        tree = {"type": "word_boundary", "value": "are", "field": "last_user_message"}
        passed1, _, _, _ = evaluate_condition_tree(tree, _ctx("are you there"), _CFG)
        assert passed1 is True
        passed2, _, _, _ = evaluate_condition_tree(tree, _ctx("beware of dogs"), _CFG)
        assert passed2 is False


class TestStartsWith:
    def test_startswith_leaf_matches(self):
        tree = {"type": "startswith", "value": "hey", "field": "last_user_message"}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("hey there"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT
        assert kw == ["hey"]

    def test_startswith_leaf_fails(self):
        tree = {"type": "startswith", "value": "hey", "field": "last_user_message"}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("oh hey"), _CFG)
        assert passed is False


class TestNotContains:
    def test_blocks_when_value_present(self):
        tree = {"type": "not_contains", "value": "secret", "field": "last_user_message"}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("tell me the secret"), _CFG)
        assert passed is False
        assert score == 0

    def test_passes_when_value_absent(self):
        tree = {"type": "not_contains", "value": "secret", "field": "last_user_message"}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("hello world"), _CFG)
        assert passed is True
        assert score == 0


class TestDepthLimit:
    def test_exceeding_depth_returns_false(self):
        leaf = {"type": "contains", "value": "hello", "field": "last_user_message"}
        tree = leaf
        for _ in range(11):
            tree = {"all": [tree]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("hello"), _CFG)
        assert passed is False
        assert score == 0


class TestScoreThresholdFiltering:
    def test_tree_passes_but_score_below_threshold(self, engine):
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
    def test_max_length_contributes_condition_weight(self):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "last_user_message"},
            {"type": "max_length", "value": 100, "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is True
        assert score == KEYWORD_WEIGHT + CONDITION_WEIGHT

    def test_min_length_contributes_condition_weight(self):
        tree = {"all": [
            {"type": "regex", "value": "\\bgit\\b", "field": "last_user_message"},
            {"type": "min_length", "value": 3, "field": "last_user_message"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, _ctx("git help"), _CFG)
        assert passed is True
        assert score == PATTERN_WEIGHT + CONDITION_WEIGHT


class TestMaxMessages:
    def test_max_messages_uses_msg_count(self):
        tree = {"type": "max_messages", "value": 5, "field": "msg_count"}
        passed, score, _, _ = evaluate_condition_tree(tree, _ctx("anything", 3), _CFG)
        assert passed is True
        assert score == CONDITION_WEIGHT

    def test_max_messages_fails_when_exceeded(self):
        tree = {"type": "max_messages", "value": 5, "field": "msg_count"}
        passed, score, _, _ = evaluate_condition_tree(tree, _ctx("anything", 10), _CFG)
        assert passed is False


class TestBothFieldsPresent:
    def test_condition_tree_takes_priority_over_patterns(self, engine):
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


class TestValidation:
    def test_valid_tree_accepted(self):
        assert validate_condition_tree(
            {"all": [{"type": "contains", "value": "hi", "field": "last_user_message"}]}
        ) is True

    def test_empty_all_rejected(self):
        assert validate_condition_tree({"all": []}) is False

    def test_not_with_list_rejected(self):
        assert validate_condition_tree(
            {"not": [{"type": "contains", "value": "hi", "field": "last_user_message"}]}
        ) is False

    def test_leaf_without_type_rejected(self):
        assert validate_condition_tree({"value": "hi"}) is False

    def test_unknown_branch_key_rejected(self):
        assert validate_condition_tree({"xor": [{"type": "contains", "value": "hi"}]}) is False

    def test_nested_valid_tree(self):
        assert validate_condition_tree({
            "all": [
                {"any": [
                    {"type": "contains", "value": "a", "field": "last_user_message"},
                    {"not": {"type": "exact", "value": "b", "field": "last_user_message"}},
                ]},
                {"type": "max_length", "value": 100, "field": "last_user_message"},
            ]
        }) is True
