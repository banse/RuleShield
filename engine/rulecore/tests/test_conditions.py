"""Tests for rulecore condition tree evaluator."""
from rulecore.types import ScoringConfig
from rulecore.conditions import (
    evaluate_condition_tree, evaluate_leaf, validate_condition_tree, resolve_field,
)

CFG = ScoringConfig()
CTX = {"text": "git push origin main", "msg_count": 3}


class TestResolveField:
    def test_existing_field(self):
        assert resolve_field("text", CTX) == "git push origin main"

    def test_missing_field(self):
        assert resolve_field("nope", CTX) == ""

    def test_numeric_field(self):
        assert resolve_field("msg_count", CTX) == 3


class TestValidation:
    def test_valid_tree(self):
        assert validate_condition_tree(
            {"all": [{"type": "contains", "value": "git", "field": "text"}]}
        ) is True

    def test_empty_all(self):
        assert validate_condition_tree({"all": []}) is False

    def test_not_with_list(self):
        assert validate_condition_tree({"not": [{"type": "contains", "value": "x"}]}) is False

    def test_missing_type(self):
        assert validate_condition_tree({"value": "hi"}) is False

    def test_unknown_key(self):
        assert validate_condition_tree({"xor": []}) is False


class TestAllNode:
    def test_passes(self):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "text"},
            {"type": "contains", "value": "push", "field": "text"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is True
        assert score == CFG.keyword_weight * 2

    def test_fails_one_child(self):
        tree = {"all": [
            {"type": "contains", "value": "git", "field": "text"},
            {"type": "contains", "value": "docker", "field": "text"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is False


class TestAnyNode:
    def test_passes_one(self):
        tree = {"any": [
            {"type": "contains", "value": "git", "field": "text"},
            {"type": "contains", "value": "docker", "field": "text"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is True
        assert score == CFG.keyword_weight

    def test_sums_passing(self):
        tree = {"any": [
            {"type": "contains", "value": "git", "field": "text"},
            {"type": "contains", "value": "push", "field": "text"},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is True
        assert score == CFG.keyword_weight * 2

    def test_fails_none(self):
        tree = {"any": [{"type": "contains", "value": "docker", "field": "text"}]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is False


class TestNotNode:
    def test_inverts_pass(self):
        tree = {"not": {"type": "contains", "value": "git", "field": "text"}}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is False

    def test_inverts_fail(self):
        tree = {"not": {"type": "contains", "value": "docker", "field": "text"}}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is True
        assert score == 0


class TestNesting:
    def test_three_deep(self):
        tree = {"all": [
            {"any": [
                {"type": "contains", "value": "git", "field": "text"},
                {"type": "regex", "value": "\\bpush\\b", "field": "text"},
            ]},
            {"not": {"type": "contains", "value": "docker", "field": "text"}},
        ]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is True
        assert score == CFG.keyword_weight + CFG.pattern_weight


class TestDepthLimit:
    def test_exceeds_max(self):
        leaf = {"type": "contains", "value": "git", "field": "text"}
        tree = leaf
        for _ in range(11):
            tree = {"all": [tree]}
        passed, score, kw, pat = evaluate_condition_tree(tree, CTX, CFG)
        assert passed is False


class TestLeafTypes:
    def test_contains(self):
        p, s, kw, pat = evaluate_leaf({"type": "contains", "value": "git", "field": "text"}, CTX, CFG)
        assert p is True and s == CFG.keyword_weight

    def test_startswith(self):
        p, s, kw, pat = evaluate_leaf({"type": "startswith", "value": "git", "field": "text"}, CTX, CFG)
        assert p is True

    def test_exact(self):
        ctx = {"text": "hello"}
        p, s, kw, pat = evaluate_leaf({"type": "exact", "value": "hello", "field": "text"}, ctx, CFG)
        assert p is True and s == CFG.exact_weight

    def test_regex(self):
        p, s, kw, pat = evaluate_leaf({"type": "regex", "value": "\\bgit\\b", "field": "text"}, CTX, CFG)
        assert p is True and s == CFG.pattern_weight

    def test_word_boundary(self):
        p, s, kw, pat = evaluate_leaf({"type": "word_boundary", "value": "push", "field": "text"}, CTX, CFG)
        assert p is True and s == CFG.keyword_weight

    def test_word_boundary_rejects_partial(self):
        ctx = {"text": "repush the code"}
        p, s, kw, pat = evaluate_leaf({"type": "word_boundary", "value": "push", "field": "text"}, ctx, CFG)
        assert p is False

    def test_not_contains_blocks(self):
        p, s, kw, pat = evaluate_leaf({"type": "not_contains", "value": "git", "field": "text"}, CTX, CFG)
        assert p is False and s == 0

    def test_not_contains_passes(self):
        p, s, kw, pat = evaluate_leaf({"type": "not_contains", "value": "docker", "field": "text"}, CTX, CFG)
        assert p is True and s == 0

    def test_max_length(self):
        p, s, kw, pat = evaluate_leaf({"type": "max_length", "value": 100, "field": "text"}, CTX, CFG)
        assert p is True and s == CFG.condition_weight

    def test_min_length(self):
        p, s, kw, pat = evaluate_leaf({"type": "min_length", "value": 3, "field": "text"}, CTX, CFG)
        assert p is True

    def test_max_value(self):
        p, s, kw, pat = evaluate_leaf({"type": "max_value", "value": 10, "field": "msg_count"}, CTX, CFG)
        assert p is True and s == CFG.condition_weight

    def test_max_value_fails(self):
        p, s, kw, pat = evaluate_leaf({"type": "max_value", "value": 2, "field": "msg_count"}, CTX, CFG)
        assert p is False

    def test_max_messages_alias(self):
        p, s, kw, pat = evaluate_leaf({"type": "max_messages", "value": 10, "field": "msg_count"}, CTX, CFG)
        assert p is True

    def test_custom_scoring_config(self):
        cfg = ScoringConfig(keyword_weight=5.0, exact_weight=10.0)
        p, s, kw, pat = evaluate_leaf({"type": "contains", "value": "git", "field": "text"}, CTX, cfg)
        assert s == 5.0
