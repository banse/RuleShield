"""Condition tree evaluator for rulecore."""
from __future__ import annotations

import logging
import re
from typing import Any

from rulecore.types import ScoringConfig

logger = logging.getLogger("rulecore.conditions")

MAX_TREE_DEPTH = 10

_regex_cache: dict[str, re.Pattern] = {}


def get_regex(pattern: str) -> re.Pattern:
    """Return a compiled regex, caching for performance."""
    compiled = _regex_cache.get(pattern)
    if compiled is None:
        compiled = re.compile(pattern, re.IGNORECASE)
        if len(_regex_cache) > 1024:
            _regex_cache.clear()
        _regex_cache[pattern] = compiled
    return compiled


def resolve_field(field: str, context: dict[str, Any]) -> Any:
    """Resolve a field name against the context dict."""
    if field not in context:
        return ""
    return context[field]


def validate_condition_tree(node: dict[str, Any]) -> bool:
    """Validate a condition tree structure recursively."""
    if not isinstance(node, dict):
        return False
    if "all" in node:
        children = node["all"]
        if not isinstance(children, list) or len(children) == 0:
            return False
        return all(validate_condition_tree(c) for c in children)
    if "any" in node:
        children = node["any"]
        if not isinstance(children, list) or len(children) == 0:
            return False
        return all(validate_condition_tree(c) for c in children)
    if "not" in node:
        child = node["not"]
        if not isinstance(child, dict):
            return False
        return validate_condition_tree(child)
    if "type" not in node:
        return False
    return True


def evaluate_condition_tree(
    node: dict[str, Any],
    context: dict[str, Any],
    scoring: ScoringConfig,
    depth: int = 0,
) -> tuple[bool, float, list[str], list[str]]:
    """Evaluate a nested condition tree. Returns (passed, score, matched_keywords, matched_patterns)."""
    if depth > MAX_TREE_DEPTH:
        logger.warning("Condition tree exceeded max depth %d", MAX_TREE_DEPTH)
        return (False, 0.0, [], [])

    if "all" in node:
        total_score = 0.0
        all_kw: list[str] = []
        all_pat: list[str] = []
        for child in node["all"]:
            passed, sc, kw, pat = evaluate_condition_tree(child, context, scoring, depth + 1)
            if not passed:
                return (False, 0.0, [], [])
            total_score += sc
            all_kw.extend(kw)
            all_pat.extend(pat)
        return (True, total_score, all_kw, all_pat)

    if "any" in node:
        any_passed = False
        total_score = 0.0
        all_kw: list[str] = []
        all_pat: list[str] = []
        for child in node["any"]:
            passed, sc, kw, pat = evaluate_condition_tree(child, context, scoring, depth + 1)
            if passed:
                any_passed = True
                total_score += sc
                all_kw.extend(kw)
                all_pat.extend(pat)
        if not any_passed:
            return (False, 0.0, [], [])
        return (True, total_score, all_kw, all_pat)

    if "not" in node:
        passed, _sc, _kw, _pat = evaluate_condition_tree(node["not"], context, scoring, depth + 1)
        if passed:
            return (False, 0.0, [], [])
        return (True, 0.0, [], [])

    return evaluate_leaf(node, context, scoring)


def evaluate_leaf(
    node: dict[str, Any],
    context: dict[str, Any],
    scoring: ScoringConfig,
) -> tuple[bool, float, list[str], list[str]]:
    """Evaluate a single leaf node against the context."""
    ptype = node.get("type", "")
    value = node.get("value", "")
    raw_field = resolve_field(node.get("field", ""), context)

    field_text = str(raw_field) if raw_field != "" else ""
    text_lower = field_text.lower()
    value_str = str(value) if isinstance(value, (str, int, float)) else ""
    value_lower = value_str.lower()

    if ptype == "contains":
        if value_lower and value_lower in text_lower:
            return (True, scoring.keyword_weight, [value_str], [])
        return (False, 0.0, [], [])

    if ptype == "startswith":
        if value_lower and text_lower.startswith(value_lower):
            return (True, scoring.keyword_weight, [value_str], [])
        return (False, 0.0, [], [])

    if ptype == "exact":
        if text_lower == value_lower:
            return (True, scoring.exact_weight, [], [value_str])
        return (False, 0.0, [], [])

    if ptype == "regex":
        try:
            if get_regex(value_str).search(field_text):
                return (True, scoring.pattern_weight, [], [value_str])
        except re.error:
            pass
        return (False, 0.0, [], [])

    if ptype == "word_boundary":
        regex_pat = rf"\b{re.escape(value_str)}\b"
        try:
            if get_regex(regex_pat).search(field_text):
                return (True, scoring.keyword_weight, [value_str], [])
        except re.error:
            pass
        return (False, 0.0, [], [])

    if ptype == "not_contains":
        if value_lower and value_lower in text_lower:
            return (False, 0.0, [], [])
        return (True, 0.0, [], [])

    if ptype == "max_length":
        if len(field_text) > int(value):
            return (False, 0.0, [], [])
        return (True, scoring.condition_weight, [], [])

    if ptype == "min_length":
        if len(field_text) < int(value):
            return (False, 0.0, [], [])
        return (True, scoring.condition_weight, [], [])

    if ptype in ("max_value", "max_messages"):
        numeric_field = int(raw_field) if isinstance(raw_field, (int, float)) else 0
        if numeric_field > int(value):
            return (False, 0.0, [], [])
        return (True, scoring.condition_weight, [], [])

    return (False, 0.0, [], [])
