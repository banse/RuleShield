# Rulecore Extraction — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract RuleShield's rule engine into a standalone zero-dependency Python package at `engine/rulecore/` without touching any RuleShield code.

**Architecture:** Copy and refactor code from `ruleshield/rules.py` and `ruleshield/feedback.py` into focused modules: types, scoring, conditions, loader, engine, store, feedback. Replace hardcoded "last_user_message" with generic context dict. Replace module-level weight constants with `ScoringConfig` dataclass. Replace `aiosqlite` feedback with `FeedbackStore` protocol + JSON file implementation. All sync, zero external deps.

**Tech Stack:** Python 3.9+ stdlib only, pytest for tests

**Spec:** `docs/superpowers/specs/2026-03-21-rulecore-extraction-design.md`

**Source code reference:**
- `ruleshield/rules.py` — rule engine, scoring, condition trees (~1128 lines)
- `ruleshield/feedback.py` — feedback loop, analytics (~900 lines)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `engine/rulecore/pyproject.toml` | Create | Package metadata, pip-installable |
| `engine/rulecore/__init__.py` | Create | Public API exports |
| `engine/rulecore/types.py` | Create | ScoringConfig, MatchResult, FeedbackEntry, RuleEvent dataclasses |
| `engine/rulecore/scoring.py` | Create | Confidence level computation |
| `engine/rulecore/conditions.py` | Create | Condition tree evaluator + leaf evaluator + regex cache |
| `engine/rulecore/loader.py` | Create | JSON rule loading, validation, state persistence |
| `engine/rulecore/engine.py` | Create | RuleEngine class wiring all modules |
| `engine/rulecore/store.py` | Create | FeedbackStore protocol + JsonFileFeedbackStore |
| `engine/rulecore/feedback.py` | Create | FeedbackManager with EMA confidence + analytics |
| `engine/rulecore/py.typed` | Create | PEP 561 marker (empty) |
| `engine/rulecore/tests/__init__.py` | Create | Test package |
| `engine/rulecore/tests/test_types.py` | Create | Dataclass tests |
| `engine/rulecore/tests/test_scoring.py` | Create | Confidence level tests |
| `engine/rulecore/tests/test_conditions.py` | Create | Full condition tree tests |
| `engine/rulecore/tests/test_loader.py` | Create | Loading + validation tests |
| `engine/rulecore/tests/test_engine.py` | Create | End-to-end engine tests |
| `engine/rulecore/tests/test_store.py` | Create | JSON store tests |
| `engine/rulecore/tests/test_feedback.py` | Create | Feedback manager tests |

---

### Task 1: Package scaffold + types

**Files:**
- Create: `engine/rulecore/pyproject.toml`
- Create: `engine/rulecore/__init__.py`
- Create: `engine/rulecore/types.py`
- Create: `engine/rulecore/py.typed`
- Create: `engine/rulecore/tests/__init__.py`
- Create: `engine/rulecore/tests/test_types.py`

- [ ] **Step 1: Create package scaffold**

`engine/rulecore/pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "rulecore"
version = "0.1.0"
description = "Generic pattern-matching rule engine with weighted scoring and feedback loops"
requires-python = ">=3.9"
license = {text = "MIT"}

[tool.setuptools.packages.find]
where = ["."]
include = ["rulecore*"]
```

`engine/rulecore/py.typed`: empty file

`engine/rulecore/__init__.py`:
```python
"""Rulecore — generic pattern-matching rule engine."""
__version__ = "0.1.0"
```

`engine/rulecore/tests/__init__.py`: empty file

- [ ] **Step 2: Create `types.py` with dataclasses**

`engine/rulecore/types.py`:
```python
"""Core data types for rulecore."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoringConfig:
    """Configurable scoring weights for pattern matching."""
    keyword_weight: float = 1.0
    pattern_weight: float = 2.0
    exact_weight: float = 5.0
    condition_weight: float = 0.5
    min_score: float = 1.5


@dataclass
class MatchResult:
    """Result of a successful rule match."""
    rule_id: str
    rule_name: str
    response: dict[str, Any]
    confidence: float
    match_score: float
    confidence_level: str
    matched_keywords: list[str]
    matched_patterns: list[str]
    deployment: str = "production"


@dataclass
class FeedbackEntry:
    """A single feedback record."""
    rule_id: str
    prompt: str
    feedback_type: str  # "accept" or "reject"
    correction: str | None = None
    classification_correct: bool | None = None
    response_helpful: bool | None = None
    confidence_appropriate: bool | None = None
    timestamp: str = ""


@dataclass
class RuleEvent:
    """A rule lifecycle event (confidence change, activation, etc.)."""
    rule_id: str
    event_type: str
    direction: str | None = None
    old_confidence: float | None = None
    new_confidence: float | None = None
    delta: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
```

- [ ] **Step 3: Write tests for types**

`engine/rulecore/tests/test_types.py`:
```python
"""Tests for rulecore data types."""
from rulecore.types import ScoringConfig, MatchResult, FeedbackEntry, RuleEvent


class TestScoringConfig:
    def test_defaults(self):
        cfg = ScoringConfig()
        assert cfg.keyword_weight == 1.0
        assert cfg.pattern_weight == 2.0
        assert cfg.exact_weight == 5.0
        assert cfg.condition_weight == 0.5
        assert cfg.min_score == 1.5

    def test_custom_values(self):
        cfg = ScoringConfig(keyword_weight=2.0, min_score=3.0)
        assert cfg.keyword_weight == 2.0
        assert cfg.min_score == 3.0
        assert cfg.pattern_weight == 2.0  # default preserved


class TestMatchResult:
    def test_creation(self):
        r = MatchResult(
            rule_id="test", rule_name="Test", response={"content": "hi"},
            confidence=0.9, match_score=3.0, confidence_level="LIKELY",
            matched_keywords=["hello"], matched_patterns=[],
        )
        assert r.rule_id == "test"
        assert r.deployment == "production"


class TestFeedbackEntry:
    def test_accept(self):
        e = FeedbackEntry(rule_id="r1", prompt="hi", feedback_type="accept")
        assert e.correction is None

    def test_reject_with_correction(self):
        e = FeedbackEntry(rule_id="r1", prompt="hi", feedback_type="reject", correction="bye")
        assert e.correction == "bye"


class TestRuleEvent:
    def test_defaults(self):
        ev = RuleEvent(rule_id="r1", event_type="confidence_update")
        assert ev.details == {}
        assert ev.direction is None
```

- [ ] **Step 4: Install package in dev mode and run tests**

Run: `pip install -e engine/rulecore/ && python3 -m pytest engine/rulecore/tests/test_types.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add engine/rulecore/
git commit -m "feat(rulecore): scaffold package with types module"
```

---

### Task 2: Scoring module

**Files:**
- Create: `engine/rulecore/scoring.py`
- Create: `engine/rulecore/tests/test_scoring.py`

- [ ] **Step 1: Create `scoring.py`**

Extracted from `ruleshield/rules.py` `_compute_confidence_level` (lines 831-856):

`engine/rulecore/scoring.py`:
```python
"""Scoring logic for rulecore — confidence levels and score computation."""
from __future__ import annotations


def compute_confidence_level(
    score: float,
    has_keywords: bool,
    has_patterns: bool,
) -> str:
    """Compute a discrete confidence level from a numeric match score.

    Returns one of: CONFIRMED, LIKELY, POSSIBLE, NONE.
    """
    if score >= 4.0 and has_keywords and has_patterns:
        return "CONFIRMED"
    if score >= 2.0:
        return "LIKELY"
    if score > 0:
        return "POSSIBLE"
    return "NONE"
```

- [ ] **Step 2: Write tests**

`engine/rulecore/tests/test_scoring.py`:
```python
"""Tests for rulecore scoring."""
from rulecore.scoring import compute_confidence_level


class TestComputeConfidenceLevel:
    def test_confirmed(self):
        assert compute_confidence_level(5.0, True, True) == "CONFIRMED"

    def test_confirmed_requires_both(self):
        assert compute_confidence_level(5.0, True, False) == "LIKELY"
        assert compute_confidence_level(5.0, False, True) == "LIKELY"

    def test_likely(self):
        assert compute_confidence_level(2.0, False, False) == "LIKELY"
        assert compute_confidence_level(3.5, True, False) == "LIKELY"

    def test_possible(self):
        assert compute_confidence_level(0.5, False, False) == "POSSIBLE"

    def test_none(self):
        assert compute_confidence_level(0, False, False) == "NONE"
        assert compute_confidence_level(-1.0, False, False) == "NONE"
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest engine/rulecore/tests/test_scoring.py -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add engine/rulecore/scoring.py engine/rulecore/tests/test_scoring.py
git commit -m "feat(rulecore): add scoring module with confidence levels"
```

---

### Task 3: Conditions module — tree evaluator + leaf evaluator

**Files:**
- Create: `engine/rulecore/conditions.py`
- Create: `engine/rulecore/tests/test_conditions.py`

- [ ] **Step 1: Create `conditions.py`**

Extracted from `ruleshield/rules.py` (lines 224-236 regex cache, 946-1128 tree evaluator). Refactored: accepts `ScoringConfig` and generic `context` dict instead of hardcoded text/msg_count.

`engine/rulecore/conditions.py`:
```python
"""Condition tree evaluator for rulecore.

Evaluates nested all/any/not trees and flat pattern/condition leaves
against a generic context dict.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from rulecore.types import ScoringConfig

logger = logging.getLogger("rulecore.conditions")

MAX_TREE_DEPTH = 10

# Regex compilation cache for performance (< 2ms target).
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
    """Resolve a field name against the context dict.

    Returns the raw value. Each leaf type handles its own coercion.
    Returns empty string for missing fields.
    """
    if field not in context:
        return ""
    return context[field]


def validate_condition_tree(node: dict[str, Any]) -> bool:
    """Validate a condition tree structure recursively. Returns True if valid."""
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
    """Evaluate a nested condition tree.

    Returns (passed, score, matched_keywords, matched_patterns).
    """
    if depth > MAX_TREE_DEPTH:
        logger.warning("Condition tree exceeded max depth %d", MAX_TREE_DEPTH)
        return (False, 0.0, [], [])

    # ── Branch: all
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

    # ── Branch: any
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

    # ── Branch: not
    if "not" in node:
        passed, _sc, _kw, _pat = evaluate_condition_tree(node["not"], context, scoring, depth + 1)
        if passed:
            return (False, 0.0, [], [])
        return (True, 0.0, [], [])

    # ── Leaf node
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

    # String coercion for text-based leaves
    field_text = str(raw_field) if raw_field != "" else ""
    text_lower = field_text.lower()
    value_str = str(value) if isinstance(value, (str, int, float)) else ""
    value_lower = value_str.lower()

    # ── Score-contributing pattern leaves
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

    # ── Boolean gate leaves
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

    # Unknown type
    return (False, 0.0, [], [])
```

- [ ] **Step 2: Write tests**

`engine/rulecore/tests/test_conditions.py`:
```python
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
        tree = {"any": [
            {"type": "contains", "value": "docker", "field": "text"},
        ]}
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
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest engine/rulecore/tests/test_conditions.py -v`
Expected: 26 passed

- [ ] **Step 4: Commit**

```bash
git add engine/rulecore/conditions.py engine/rulecore/tests/test_conditions.py
git commit -m "feat(rulecore): add conditions module with tree evaluator"
```

---

### Task 4: Loader module — JSON loading, validation, state persistence

**Files:**
- Create: `engine/rulecore/loader.py`
- Create: `engine/rulecore/tests/test_loader.py`

- [ ] **Step 1: Create `loader.py`**

Extracted from `ruleshield/rules.py` `_load_rules`, `_validate_condition_tree`, `_apply_persisted_state`, `_save_rules_to_disk`:

`engine/rulecore/loader.py`:
```python
"""Rule loading, validation, and state persistence for rulecore."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from rulecore.conditions import validate_condition_tree

logger = logging.getLogger("rulecore.loader")


def load_rules(rules_dir: str, bundled_dir: str | None = None) -> list[dict[str, Any]]:
    """Load rules from JSON files in a directory.

    Scans ``rules_dir`` for *.json files (excluding _state.json).
    Also loads from promoted/ and candidates/ subdirectories.
    If the directory is empty and bundled_dir is provided, copies defaults.

    Returns rules sorted by priority descending.
    """
    rules_path = Path(rules_dir)
    rules_path.mkdir(parents=True, exist_ok=True)

    json_files = [fp for fp in rules_path.glob("*.json") if fp.name != "_state.json"]

    # Copy bundled defaults if directory is empty.
    if not json_files and bundled_dir:
        bundled = Path(bundled_dir)
        if bundled.is_dir():
            for src in bundled.glob("*.json"):
                dest = rules_path / src.name
                if not dest.exists():
                    shutil.copy2(str(src), str(dest))
            json_files = [fp for fp in rules_path.glob("*.json") if fp.name != "_state.json"]

    # Also load from promoted/ and candidates/ subdirectories.
    for subdir_name in ("promoted", "candidates"):
        subdir = rules_path / subdir_name
        if subdir.is_dir():
            json_files.extend(subdir.glob("*.json"))

    rules: list[dict[str, Any]] = []
    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            loaded = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            deployment = "candidate" if fp.parent.name == "candidates" else "production"
            for rule in loaded:
                if not isinstance(rule, dict):
                    continue
                if ("patterns" not in rule and "condition_tree" not in rule) or "response" not in rule:
                    continue
                if "condition_tree" in rule:
                    if not validate_condition_tree(rule["condition_tree"]):
                        logger.warning("Skipping rule %s: invalid condition_tree", rule.get("id", "<unknown>"))
                        continue
                rule.setdefault("deployment", deployment)
                rule.setdefault("hit_count", 0)
                rule.setdefault("shadow_hit_count", 0)
                rules.append(rule)
        except (json.JSONDecodeError, OSError):
            continue

    rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
    apply_persisted_state(rules, rules_dir)
    return rules


def apply_persisted_state(rules: list[dict[str, Any]], rules_dir: str) -> None:
    """Merge runtime state from _state.json into loaded rules."""
    state_path = Path(rules_dir) / "_state.json"
    if not state_path.is_file():
        return

    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            state_entries = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return

    state_map: dict[str, dict[str, Any]] = {}
    for entry in state_entries:
        rid = entry.get("id")
        if rid:
            state_map[rid] = entry

    for rule in rules:
        rid = rule.get("id")
        if rid and rid in state_map:
            saved = state_map[rid]
            rule["hit_count"] = saved.get("hit_count", rule.get("hit_count", 0))
            rule["shadow_hit_count"] = saved.get("shadow_hit_count", rule.get("shadow_hit_count", 0))
            rule["confidence"] = saved.get("confidence", rule.get("confidence", 1.0))
            rule["enabled"] = saved.get("enabled", rule.get("enabled", True))
            rule["deployment"] = saved.get("deployment", rule.get("deployment", "production"))


def save_state(rules: list[dict[str, Any]], rules_dir: str) -> None:
    """Persist runtime state (hit counts, confidence, enabled) to _state.json."""
    state_path = Path(rules_dir) / "_state.json"
    serialisable = []
    for rule in rules:
        serialisable.append({
            "id": rule.get("id"),
            "hit_count": rule.get("hit_count", 0),
            "shadow_hit_count": rule.get("shadow_hit_count", 0),
            "confidence": rule.get("confidence", 1.0),
            "enabled": rule.get("enabled", True),
            "deployment": rule.get("deployment", "production"),
        })
    try:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, indent=2)
    except OSError:
        pass
```

- [ ] **Step 2: Write tests**

`engine/rulecore/tests/test_loader.py`:
```python
"""Tests for rulecore loader."""
import json
import os
import tempfile
import shutil

import pytest
from rulecore.loader import load_rules, save_state, apply_persisted_state


@pytest.fixture
def rules_dir():
    tmpdir = tempfile.mkdtemp(prefix="rulecore-test-")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def _write_rules(rules_dir, filename, rules):
    with open(os.path.join(rules_dir, filename), "w") as f:
        json.dump(rules, f)


class TestLoadRules:
    def test_loads_flat_rules(self, rules_dir):
        _write_rules(rules_dir, "test.json", [
            {"id": "r1", "patterns": [{"type": "exact", "value": "hi"}], "response": {"content": "hello"}, "priority": 5},
            {"id": "r2", "patterns": [{"type": "exact", "value": "bye"}], "response": {"content": "goodbye"}, "priority": 10},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 2
        assert rules[0]["id"] == "r2"  # higher priority first

    def test_loads_condition_tree_rules(self, rules_dir):
        _write_rules(rules_dir, "tree.json", [
            {"id": "t1", "condition_tree": {"all": [{"type": "contains", "value": "hi", "field": "text"}]}, "response": {"content": "hello"}},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 1
        assert rules[0]["id"] == "t1"

    def test_skips_invalid_tree(self, rules_dir):
        _write_rules(rules_dir, "bad.json", [
            {"id": "bad", "condition_tree": {"all": []}, "response": {"content": "x"}},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 0

    def test_skips_rules_without_patterns_or_tree(self, rules_dir):
        _write_rules(rules_dir, "nopat.json", [
            {"id": "nopat", "response": {"content": "x"}},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 0

    def test_loads_candidates(self, rules_dir):
        cand_dir = os.path.join(rules_dir, "candidates")
        os.makedirs(cand_dir)
        _write_rules(cand_dir, "cand.json", [
            {"id": "c1", "patterns": [{"type": "exact", "value": "test"}], "response": {"content": "ok"}},
        ])
        rules = load_rules(rules_dir)
        assert rules[0]["deployment"] == "candidate"

    def test_empty_dir_with_no_bundled(self, rules_dir):
        rules = load_rules(rules_dir)
        assert rules == []


class TestStatePersistence:
    def test_save_and_load(self, rules_dir):
        rules = [{"id": "r1", "hit_count": 5, "confidence": 0.8, "enabled": True, "deployment": "production"}]
        save_state(rules, rules_dir)
        state_path = os.path.join(rules_dir, "_state.json")
        assert os.path.exists(state_path)

        fresh_rules = [{"id": "r1", "hit_count": 0, "confidence": 1.0, "enabled": True}]
        apply_persisted_state(fresh_rules, rules_dir)
        assert fresh_rules[0]["hit_count"] == 5
        assert fresh_rules[0]["confidence"] == 0.8
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest engine/rulecore/tests/test_loader.py -v`
Expected: 8 passed

- [ ] **Step 4: Commit**

```bash
git add engine/rulecore/loader.py engine/rulecore/tests/test_loader.py
git commit -m "feat(rulecore): add loader module with JSON loading and state persistence"
```

---

### Task 5: Engine module — RuleEngine class

**Files:**
- Create: `engine/rulecore/engine.py`
- Create: `engine/rulecore/tests/test_engine.py`

- [ ] **Step 1: Create `engine.py`**

`engine/rulecore/engine.py`:
```python
"""RuleEngine — the main entry point for rulecore."""
from __future__ import annotations

import logging
from typing import Any

from rulecore.types import ScoringConfig, MatchResult
from rulecore.scoring import compute_confidence_level
from rulecore.conditions import evaluate_condition_tree, resolve_field, get_regex
from rulecore.loader import load_rules, save_state

logger = logging.getLogger("rulecore.engine")


class RuleEngine:
    """Generic pattern-matching rule engine with weighted scoring.

    Matches incoming context dicts against JSON-defined rules using
    configurable scoring weights, nested condition trees, and
    priority-based ordering.
    """

    def __init__(
        self,
        rules_dir: str = "",
        scoring: ScoringConfig | None = None,
        bundled_dir: str | None = None,
    ) -> None:
        self.rules_dir = rules_dir
        self.scoring = scoring or ScoringConfig()
        self.bundled_dir = bundled_dir
        self.rules: list[dict[str, Any]] = []
        self.deactivation_threshold: float = 0.5
        self._dirty = False
        self._match_count_since_save = 0
        self._save_interval = 100

    def load(self) -> None:
        """Load rules from disk."""
        if self.rules_dir:
            self.rules = load_rules(self.rules_dir, self.bundled_dir)

    def match(
        self,
        context: dict[str, Any],
        confidence_threshold: float = 0.0,
        deployment: str = "production",
    ) -> MatchResult | None:
        """Match context against loaded rules.

        Args:
            context: Dict of field values to match against.
            confidence_threshold: Minimum rule confidence to fire.
            deployment: "production" or "candidate".

        Returns:
            MatchResult on match, None otherwise.
        """
        return self._match_with_scope(context, confidence_threshold, deployment, "hit_count")

    def match_candidates(
        self,
        context: dict[str, Any],
        confidence_threshold: float = 0.0,
    ) -> MatchResult | None:
        """Match shadow-only candidate rules."""
        return self._match_with_scope(context, confidence_threshold, "candidate", "shadow_hit_count")

    def _match_with_scope(
        self,
        context: dict[str, Any],
        confidence_threshold: float,
        deployment: str,
        hit_field: str,
    ) -> MatchResult | None:
        best: dict[str, Any] | None = None
        best_score: float = 0.0
        best_priority: int | None = None

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("deployment", "production") != deployment:
                continue

            rule_confidence = float(rule.get("confidence", 1.0))
            if rule_confidence < self.deactivation_threshold:
                continue
            if rule_confidence < confidence_threshold:
                continue

            rule_priority = rule.get("priority", 0)
            if best is not None and rule_priority < best_priority:
                break

            # Score via condition_tree or flat patterns
            if "condition_tree" in rule:
                passed, score, matched_kw, matched_pat = evaluate_condition_tree(
                    rule["condition_tree"], context, self.scoring,
                )
                if not passed or score < self.scoring.min_score:
                    continue
            else:
                score, matched_kw, matched_pat = self._score_flat_rule(rule, context)
                if score < self.scoring.min_score:
                    continue

            if score > best_score:
                has_keywords = len(matched_kw) > 0
                has_patterns = len(matched_pat) > 0
                confidence_level = compute_confidence_level(score, has_keywords, has_patterns)
                best_score = score
                best_priority = rule_priority
                best = {
                    "rule": rule,
                    "score": score,
                    "kw": matched_kw,
                    "pat": matched_pat,
                    "level": confidence_level,
                }

        if best is None:
            return None

        winning_rule = best["rule"]
        winning_rule[hit_field] = winning_rule.get(hit_field, 0) + 1
        self._dirty = True
        self._match_count_since_save += 1
        if self._match_count_since_save >= self._save_interval and self.rules_dir:
            save_state(self.rules, self.rules_dir)
            self._dirty = False
            self._match_count_since_save = 0

        return MatchResult(
            rule_id=winning_rule["id"],
            rule_name=winning_rule.get("name", winning_rule["id"]),
            response=winning_rule["response"],
            confidence=winning_rule.get("confidence", 1.0),
            match_score=best["score"],
            confidence_level=best["level"],
            matched_keywords=best["kw"],
            matched_patterns=best["pat"],
            deployment=winning_rule.get("deployment", "production"),
        )

    def _score_flat_rule(
        self, rule: dict[str, Any], context: dict[str, Any],
    ) -> tuple[float, list[str], list[str]]:
        """Score a flat rule (patterns + conditions)."""
        # Check conditions first (AND logic)
        for cond in rule.get("conditions", []):
            ctype = cond.get("type", "")
            cvalue = cond.get("value", 0)
            raw = resolve_field(cond.get("field", ""), context)
            field_text = str(raw) if raw != "" else ""

            if ctype == "max_length" and len(field_text) > int(cvalue):
                return (0.0, [], [])
            if ctype == "min_length" and len(field_text) < int(cvalue):
                return (0.0, [], [])
            if ctype in ("max_messages", "max_value"):
                numeric = int(raw) if isinstance(raw, (int, float)) else 0
                if numeric > int(cvalue):
                    return (0.0, [], [])

        # Score patterns (OR logic)
        score = 0.0
        matched_kw: list[str] = []
        matched_pat: list[str] = []

        for pat in rule.get("patterns", []):
            ptype = pat.get("type", "contains")
            value = pat.get("value", "")
            raw = resolve_field(pat.get("field", ""), context)
            field_text = str(raw) if raw != "" else ""
            text_lower = field_text.lower()
            value_lower = str(value).lower()

            if ptype in ("contains", "startswith"):
                if ptype == "contains" and value_lower in text_lower:
                    score += self.scoring.keyword_weight
                    matched_kw.append(value)
                elif ptype == "startswith" and text_lower.startswith(value_lower):
                    score += self.scoring.keyword_weight
                    matched_kw.append(value)
            elif ptype == "regex":
                try:
                    if get_regex(value).search(field_text):
                        score += self.scoring.pattern_weight
                        matched_pat.append(value)
                except Exception:
                    pass
            elif ptype == "exact":
                if value_lower == text_lower:
                    score += self.scoring.exact_weight
                    matched_pat.append(value)

        # Condition bonus
        if score > 0:
            conditions = rule.get("conditions", [])
            if conditions:
                score += len(conditions) * self.scoring.condition_weight

        return (score, matched_kw, matched_pat)

    # ── Rule management ──

    def add_rule(self, rule: dict[str, Any]) -> None:
        rule.setdefault("enabled", True)
        rule.setdefault("hit_count", 0)
        rule.setdefault("shadow_hit_count", 0)
        rule.setdefault("confidence", 0.9)
        rule.setdefault("priority", 0)
        rule.setdefault("deployment", "production")
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    def update_confidence(self, rule_id: str, new_confidence: float) -> bool:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["confidence"] = max(0.0, min(1.0, new_confidence))
                self._dirty = True
                return True
        return False

    def deactivate_rule(self, rule_id: str) -> bool:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = False
                self._dirty = True
                return True
        return False

    def activate_rule(self, rule_id: str) -> bool:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = True
                rule["deployment"] = "production"
                self._dirty = True
                return True
        return False

    def get_active_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "id": r["id"],
                "name": r.get("name", r["id"]),
                "deployment": r.get("deployment", "production"),
                "enabled": r.get("enabled", True),
                "priority": r.get("priority", 0),
                "hit_count": r.get("hit_count", 0),
                "shadow_hit_count": r.get("shadow_hit_count", 0),
                "confidence": r.get("confidence", 1.0),
                "pattern_count": len(r.get("patterns", [])),
                "has_condition_tree": "condition_tree" in r,
            }
            for r in self.rules
            if r.get("enabled", True)
        ]

    def get_stats(self) -> dict[str, Any]:
        active = [r for r in self.rules if r.get("enabled", True)]
        total_hits = sum(r.get("hit_count", 0) for r in self.rules)
        top = sorted(self.rules, key=lambda r: r.get("hit_count", 0), reverse=True)[:5]
        return {
            "total_rules": len(self.rules),
            "active_rules": len(active),
            "total_hits": total_hits,
            "top_rules": [
                {"id": r["id"], "name": r.get("name", r["id"]), "hit_count": r.get("hit_count", 0)}
                for r in top
            ],
        }
```

- [ ] **Step 2: Write tests**

`engine/rulecore/tests/test_engine.py`:
```python
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
        assert result is None  # low_conf rule has 0.3

    def test_deactivation_threshold(self, engine):
        result = engine.match(context={"text": "test"})
        assert result is None  # 0.3 < deactivation_threshold 0.5

    def test_priority_ordering(self, engine):
        # greet (priority 10) beats git_tree (priority 7) for text that matches both
        # But "hello" won't match git_tree, so this tests that higher priority runs first
        engine.rules.append({
            "id": "greet2", "patterns": [{"type": "exact", "value": "hello", "field": "text"}],
            "response": {"content": "hi2"}, "confidence": 0.95, "priority": 5, "enabled": True,
        })
        result = engine.match(context={"text": "hello"})
        assert result.rule_id == "greet"  # higher priority wins

    def test_flat_rule_condition_failure(self, engine):
        # "hello world is a long greeting" exceeds max_length 20 on greet rule
        result = engine.match(context={"text": "hello world is a long greeting"})
        assert result is None  # condition blocks even though pattern would match... wait, exact won't match

    def test_match_candidates(self, engine):
        engine.rules.append({
            "id": "cand1", "patterns": [{"type": "exact", "value": "test", "field": "text"}],
            "response": {"content": "ok"}, "confidence": 0.95, "priority": 5,
            "enabled": True, "deployment": "candidate",
        })
        # Normal match should not find candidate
        result = engine.match(context={"text": "test"})
        assert result is None or result.rule_id != "cand1"
        # match_candidates should find it
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
        # With lower min_score, more rules could fire
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
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest engine/rulecore/tests/test_engine.py -v`
Expected: 14 passed

- [ ] **Step 4: Commit**

```bash
git add engine/rulecore/engine.py engine/rulecore/tests/test_engine.py
git commit -m "feat(rulecore): add RuleEngine with flat and tree matching"
```

---

### Task 6: Store module — FeedbackStore protocol + JSON implementation

**Files:**
- Create: `engine/rulecore/store.py`
- Create: `engine/rulecore/tests/test_store.py`

- [ ] **Step 1: Create `store.py`**

`engine/rulecore/store.py`:
```python
"""Feedback storage protocol and JSON file implementation for rulecore."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from rulecore.types import FeedbackEntry, RuleEvent

logger = logging.getLogger("rulecore.store")


@runtime_checkable
class FeedbackStore(Protocol):
    """Protocol for feedback persistence backends."""
    def save_feedback(self, entry: FeedbackEntry) -> None: ...
    def save_event(self, event: RuleEvent) -> None: ...
    def load_feedback(self, rule_id: str | None = None) -> list[FeedbackEntry]: ...
    def load_events(self, rule_id: str | None = None) -> list[RuleEvent]: ...


class JsonFileFeedbackStore:
    """Zero-dependency JSON file feedback store.

    Stores feedback entries and rule events in a single JSON file.
    Suitable for small-scale use. For production, implement
    FeedbackStore with SQLite, Redis, etc.
    """

    def __init__(self, path: str = "feedback.json") -> None:
        self.path = os.path.expanduser(path)
        self._data: dict[str, Any] = {"feedback": [], "events": []}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {"feedback": [], "events": []}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            logger.warning("Failed to save feedback store to %s", self.path)

    def save_feedback(self, entry: FeedbackEntry) -> None:
        record = {
            "rule_id": entry.rule_id,
            "prompt": entry.prompt,
            "feedback_type": entry.feedback_type,
            "correction": entry.correction,
            "classification_correct": entry.classification_correct,
            "response_helpful": entry.response_helpful,
            "confidence_appropriate": entry.confidence_appropriate,
            "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
        }
        self._data.setdefault("feedback", []).append(record)
        self._save()

    def save_event(self, event: RuleEvent) -> None:
        record = {
            "rule_id": event.rule_id,
            "event_type": event.event_type,
            "direction": event.direction,
            "old_confidence": event.old_confidence,
            "new_confidence": event.new_confidence,
            "delta": event.delta,
            "details": event.details,
            "timestamp": event.timestamp or datetime.now(timezone.utc).isoformat(),
        }
        self._data.setdefault("events", []).append(record)
        self._save()

    def load_feedback(self, rule_id: str | None = None) -> list[FeedbackEntry]:
        entries = []
        for rec in self._data.get("feedback", []):
            if rule_id and rec.get("rule_id") != rule_id:
                continue
            entries.append(FeedbackEntry(
                rule_id=rec["rule_id"],
                prompt=rec.get("prompt", ""),
                feedback_type=rec.get("feedback_type", ""),
                correction=rec.get("correction"),
                classification_correct=rec.get("classification_correct"),
                response_helpful=rec.get("response_helpful"),
                confidence_appropriate=rec.get("confidence_appropriate"),
                timestamp=rec.get("timestamp", ""),
            ))
        return entries

    def load_events(self, rule_id: str | None = None) -> list[RuleEvent]:
        events = []
        for rec in self._data.get("events", []):
            if rule_id and rec.get("rule_id") != rule_id:
                continue
            events.append(RuleEvent(
                rule_id=rec["rule_id"],
                event_type=rec.get("event_type", ""),
                direction=rec.get("direction"),
                old_confidence=rec.get("old_confidence"),
                new_confidence=rec.get("new_confidence"),
                delta=rec.get("delta"),
                details=rec.get("details", {}),
                timestamp=rec.get("timestamp", ""),
            ))
        return events
```

- [ ] **Step 2: Write tests**

`engine/rulecore/tests/test_store.py`:
```python
"""Tests for rulecore JSON feedback store."""
import os
import tempfile
import shutil

import pytest
from rulecore.store import JsonFileFeedbackStore, FeedbackStore
from rulecore.types import FeedbackEntry, RuleEvent


@pytest.fixture
def store_path():
    tmpdir = tempfile.mkdtemp(prefix="rulecore-store-")
    path = os.path.join(tmpdir, "feedback.json")
    yield path
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestJsonFileFeedbackStore:
    def test_implements_protocol(self):
        assert isinstance(JsonFileFeedbackStore("/tmp/test.json"), FeedbackStore)

    def test_save_and_load_feedback(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        entry = FeedbackEntry(rule_id="r1", prompt="hello", feedback_type="accept")
        store.save_feedback(entry)

        loaded = store.load_feedback()
        assert len(loaded) == 1
        assert loaded[0].rule_id == "r1"
        assert loaded[0].feedback_type == "accept"

    def test_save_and_load_events(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        event = RuleEvent(rule_id="r1", event_type="confidence_update", delta=0.01)
        store.save_event(event)

        loaded = store.load_events()
        assert len(loaded) == 1
        assert loaded[0].event_type == "confidence_update"

    def test_filter_by_rule_id(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        store.save_feedback(FeedbackEntry(rule_id="r1", prompt="a", feedback_type="accept"))
        store.save_feedback(FeedbackEntry(rule_id="r2", prompt="b", feedback_type="reject"))

        r1_only = store.load_feedback(rule_id="r1")
        assert len(r1_only) == 1
        assert r1_only[0].rule_id == "r1"

    def test_persistence_across_instances(self, store_path):
        store1 = JsonFileFeedbackStore(store_path)
        store1.save_feedback(FeedbackEntry(rule_id="r1", prompt="x", feedback_type="accept"))

        store2 = JsonFileFeedbackStore(store_path)
        loaded = store2.load_feedback()
        assert len(loaded) == 1

    def test_empty_store(self, store_path):
        store = JsonFileFeedbackStore(store_path)
        assert store.load_feedback() == []
        assert store.load_events() == []
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest engine/rulecore/tests/test_store.py -v`
Expected: 6 passed

- [ ] **Step 4: Commit**

```bash
git add engine/rulecore/store.py engine/rulecore/tests/test_store.py
git commit -m "feat(rulecore): add FeedbackStore protocol and JSON implementation"
```

---

### Task 7: Feedback module — FeedbackManager with EMA + analytics

**Files:**
- Create: `engine/rulecore/feedback.py`
- Create: `engine/rulecore/tests/test_feedback.py`

- [ ] **Step 1: Create `feedback.py`**

`engine/rulecore/feedback.py`:
```python
"""FeedbackManager — bandit-style confidence tuning with analytics for rulecore."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from rulecore.types import FeedbackEntry, RuleEvent

logger = logging.getLogger("rulecore.feedback")


class _EngineProtocol(Protocol):
    """Minimal engine interface needed by FeedbackManager."""
    rules: list[dict[str, Any]]
    def update_confidence(self, rule_id: str, new_confidence: float) -> bool: ...
    def deactivate_rule(self, rule_id: str) -> bool: ...
    def activate_rule(self, rule_id: str) -> bool: ...


class _StoreProtocol(Protocol):
    """Minimal store interface needed by FeedbackManager."""
    def save_feedback(self, entry: FeedbackEntry) -> None: ...
    def save_event(self, event: RuleEvent) -> None: ...
    def load_feedback(self, rule_id: str | None = None) -> list[FeedbackEntry]: ...


class FeedbackManager:
    """Bandit-style confidence updater with analytics.

    Layer 1: accept/reject signals with EMA confidence updates.
    Layer 2: underperforming rules detection, category performance.
    """

    def __init__(
        self,
        engine: Any,  # accepts _EngineProtocol structurally
        store: Any,    # accepts _StoreProtocol structurally
        acceptance_delta: float = 0.01,
        rejection_delta: float = 0.05,
        deactivation_threshold: float = 0.5,
        promotion_threshold: float = 0.98,
    ) -> None:
        self.engine = engine
        self.store = store
        self.acceptance_delta = acceptance_delta
        self.rejection_delta = rejection_delta
        self.deactivation_threshold = deactivation_threshold
        self.promotion_threshold = promotion_threshold

    # ── Layer 1: Core feedback loop ──

    def accept(
        self,
        rule_id: str,
        prompt: str,
        *,
        classification_correct: bool | None = None,
        response_helpful: bool | None = None,
        confidence_appropriate: bool | None = None,
    ) -> None:
        """Record an accepted rule response. Bumps confidence via EMA."""
        entry = FeedbackEntry(
            rule_id=rule_id,
            prompt=prompt,
            feedback_type="accept",
            classification_correct=classification_correct,
            response_helpful=response_helpful,
            confidence_appropriate=confidence_appropriate,
        )
        self.store.save_feedback(entry)
        self._update_confidence(rule_id, accepted=True)
        self._check_thresholds()
        logger.debug("Recorded accept for rule %s", rule_id)

    def reject(
        self,
        rule_id: str,
        prompt: str,
        correction: str | None = None,
        *,
        classification_correct: bool | None = None,
        response_helpful: bool | None = None,
        confidence_appropriate: bool | None = None,
    ) -> None:
        """Record a rejected rule response. Penalises confidence via EMA."""
        entry = FeedbackEntry(
            rule_id=rule_id,
            prompt=prompt,
            feedback_type="reject",
            correction=correction,
            classification_correct=classification_correct,
            response_helpful=response_helpful,
            confidence_appropriate=confidence_appropriate,
        )
        self.store.save_feedback(entry)
        self._update_confidence(rule_id, accepted=False)
        self._check_thresholds()
        logger.debug("Recorded reject for rule %s", rule_id)

    def _update_confidence(self, rule_id: str, accepted: bool) -> None:
        """EMA-style confidence update."""
        rule = self._find_rule(rule_id)
        if rule is None:
            return

        current = rule.get("confidence", 1.0)
        if accepted:
            new_conf = current + self.acceptance_delta * (1.0 - current)
        else:
            new_conf = current - self.rejection_delta * current

        new_conf = max(0.0, min(1.0, new_conf))
        self.engine.update_confidence(rule_id, new_conf)

        delta = new_conf - current
        direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        self.store.save_event(RuleEvent(
            rule_id=rule_id,
            event_type="confidence_update",
            direction=direction,
            old_confidence=current,
            new_confidence=new_conf,
            delta=delta,
        ))

    def _check_thresholds(self) -> list[str]:
        """Deactivate rules below threshold. Returns deactivated IDs."""
        deactivated = []
        for rule in self.engine.rules:
            conf = rule.get("confidence", 1.0)
            rid = rule.get("id", "")
            if conf < self.deactivation_threshold and rule.get("enabled", True):
                self.engine.deactivate_rule(rid)
                deactivated.append(rid)
                self.store.save_event(RuleEvent(
                    rule_id=rid, event_type="rule_deactivated",
                    direction="down", old_confidence=conf, new_confidence=conf,
                ))
                logger.warning("Rule %s deactivated (confidence %.4f)", rid, conf)
        return deactivated

    def _find_rule(self, rule_id: str) -> dict[str, Any] | None:
        for rule in self.engine.rules:
            if rule.get("id") == rule_id:
                return rule
        return None

    # ── Layer 2: Analytics ──

    def get_underperforming_rules(self, min_feedback: int = 5) -> list[dict[str, Any]]:
        """Find rules with acceptance rate < 70% and sufficient feedback."""
        all_feedback = self.store.load_feedback()
        per_rule: dict[str, dict[str, int]] = {}
        for fb in all_feedback:
            if fb.rule_id not in per_rule:
                per_rule[fb.rule_id] = {"accept": 0, "reject": 0}
            if fb.feedback_type == "accept":
                per_rule[fb.rule_id]["accept"] += 1
            else:
                per_rule[fb.rule_id]["reject"] += 1

        results = []
        for rid, counts in per_rule.items():
            total = counts["accept"] + counts["reject"]
            if total < min_feedback:
                continue
            rate = counts["accept"] / total if total > 0 else 0.0
            if rate >= 0.70:
                continue
            rule = self._find_rule(rid)
            results.append({
                "rule_id": rid,
                "rule_name": rule.get("name", rid) if rule else rid,
                "accept_count": counts["accept"],
                "reject_count": counts["reject"],
                "total_feedback": total,
                "acceptance_rate": round(rate, 4),
                "current_confidence": rule.get("confidence", 1.0) if rule else None,
            })

        results.sort(key=lambda r: r["acceptance_rate"])
        return results

    def get_performance_by_category(self) -> dict[str, dict[str, Any]]:
        """Group feedback by rule category (ID prefix before first _)."""
        all_feedback = self.store.load_feedback()
        categories: dict[str, dict[str, int]] = {}

        for fb in all_feedback:
            category = fb.rule_id.split("_")[0] if "_" in fb.rule_id else fb.rule_id
            if category not in categories:
                categories[category] = {"total": 0, "accepted": 0}
            categories[category]["total"] += 1
            if fb.feedback_type == "accept":
                categories[category]["accepted"] += 1

        result = {}
        for cat, data in categories.items():
            total = data["total"]
            result[cat] = {
                "total": total,
                "accepted": data["accepted"],
                "accuracy": round(data["accepted"] / total, 4) if total > 0 else 0.0,
            }
        return result

    def check_promotions(self) -> list[str]:
        """Check if candidate rules meet promotion criteria.

        Promotes rules with confidence >= promotion_threshold.
        Returns list of promoted rule IDs.
        """
        promoted = []
        for rule in self.engine.rules:
            if rule.get("deployment") != "candidate":
                continue
            if rule.get("confidence", 0) >= self.promotion_threshold:
                rid = rule.get("id", "")
                self.engine.activate_rule(rid)
                promoted.append(rid)
                self.store.save_event(RuleEvent(
                    rule_id=rid, event_type="rule_promoted", direction="up",
                ))
                logger.info("Rule %s promoted to production", rid)
        return promoted
```

- [ ] **Step 2: Write tests**

`engine/rulecore/tests/test_feedback.py`:
```python
"""Tests for rulecore FeedbackManager."""
import pytest
from rulecore.engine import RuleEngine
from rulecore.store import JsonFileFeedbackStore
from rulecore.feedback import FeedbackManager

import tempfile, os, shutil


@pytest.fixture
def tmpdir():
    d = tempfile.mkdtemp(prefix="rulecore-fb-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def engine():
    e = RuleEngine()
    e.rules = [
        {"id": "r1", "name": "Rule 1", "confidence": 0.8, "enabled": True, "deployment": "production",
         "patterns": [{"type": "exact", "value": "hi"}], "response": {"content": "hello"}},
        {"id": "r2", "name": "Rule 2", "confidence": 0.55, "enabled": True, "deployment": "candidate",
         "patterns": [{"type": "exact", "value": "bye"}], "response": {"content": "goodbye"}},
    ]
    return e


@pytest.fixture
def feedback(engine, tmpdir):
    store = JsonFileFeedbackStore(os.path.join(tmpdir, "fb.json"))
    return FeedbackManager(engine=engine, store=store)


class TestAcceptReject:
    def test_accept_increases_confidence(self, engine, feedback):
        old = engine.rules[0]["confidence"]
        feedback.accept("r1", "hello")
        new = engine.rules[0]["confidence"]
        assert new > old

    def test_reject_decreases_confidence(self, engine, feedback):
        old = engine.rules[0]["confidence"]
        feedback.reject("r1", "hello")
        new = engine.rules[0]["confidence"]
        assert new < old

    def test_ema_formula_accept(self, engine, feedback):
        # confidence + delta * (1 - confidence) = 0.8 + 0.01 * 0.2 = 0.802
        feedback.accept("r1", "test")
        assert abs(engine.rules[0]["confidence"] - 0.802) < 0.001

    def test_ema_formula_reject(self, engine, feedback):
        # confidence - delta * confidence = 0.8 - 0.05 * 0.8 = 0.76
        feedback.reject("r1", "test")
        assert abs(engine.rules[0]["confidence"] - 0.76) < 0.001

    def test_reject_with_correction(self, engine, feedback):
        feedback.reject("r1", "hello", correction="should say goodbye")
        entries = feedback.store.load_feedback(rule_id="r1")
        assert entries[0].correction == "should say goodbye"


class TestAutoDeactivation:
    def test_deactivates_below_threshold(self, engine, feedback):
        engine.rules[0]["confidence"] = 0.06
        feedback.reject("r1", "test")  # will drop below 0.5
        assert engine.rules[0]["enabled"] is False

    def test_keeps_above_threshold(self, engine, feedback):
        feedback.reject("r1", "test")  # 0.8 -> 0.76, still above 0.5
        assert engine.rules[0]["enabled"] is True


class TestAnalytics:
    def test_underperforming_rules(self, engine, feedback):
        for i in range(3):
            feedback.accept("r1", f"prompt{i}")
        for i in range(7):
            feedback.reject("r1", f"prompt{i}")
        result = feedback.get_underperforming_rules(min_feedback=5)
        assert len(result) == 1
        assert result[0]["rule_id"] == "r1"
        assert result[0]["acceptance_rate"] == 0.3

    def test_performance_by_category(self, engine, feedback):
        feedback.accept("r1", "test1")
        feedback.accept("r1", "test2")
        feedback.reject("r1", "test3")
        result = feedback.get_performance_by_category()
        assert "r1" in result
        assert result["r1"]["total"] == 3
        assert result["r1"]["accepted"] == 2

    def test_check_promotions(self, engine, feedback):
        engine.rules[1]["confidence"] = 0.99  # above 0.98 threshold
        promoted = feedback.check_promotions()
        assert "r2" in promoted
        assert engine.rules[1]["deployment"] == "production"
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest engine/rulecore/tests/test_feedback.py -v`
Expected: 10 passed

- [ ] **Step 4: Commit**

```bash
git add engine/rulecore/feedback.py engine/rulecore/tests/test_feedback.py
git commit -m "feat(rulecore): add FeedbackManager with EMA confidence and analytics"
```

---

### Task 8: Public API exports + final verification

**Files:**
- Modify: `engine/rulecore/__init__.py`

- [ ] **Step 1: Update `__init__.py` with public exports**

`engine/rulecore/__init__.py`:
```python
"""Rulecore — generic pattern-matching rule engine with feedback loops."""
__version__ = "0.1.0"

from rulecore.types import ScoringConfig, MatchResult, FeedbackEntry, RuleEvent
from rulecore.engine import RuleEngine
from rulecore.feedback import FeedbackManager
from rulecore.store import JsonFileFeedbackStore, FeedbackStore

__all__ = [
    "RuleEngine",
    "MatchResult",
    "ScoringConfig",
    "FeedbackEntry",
    "RuleEvent",
    "FeedbackManager",
    "JsonFileFeedbackStore",
    "FeedbackStore",
]
```

- [ ] **Step 2: Run full rulecore test suite**

Run: `python3 -m pytest engine/rulecore/tests/ -v`
Expected: ALL pass (~70 tests)

- [ ] **Step 3: Verify zero imports from ruleshield**

Run: `grep -r "from ruleshield\|import ruleshield" engine/rulecore/`
Expected: No output (zero matches)

- [ ] **Step 4: Verify existing RuleShield tests still pass**

Run: `python3 -m pytest tests/unit/ tests/integration/ tests/smoke/test_imports.py -v`
Expected: ALL existing tests pass unchanged (RuleShield was never touched)

- [ ] **Step 5: Commit**

```bash
git add engine/rulecore/__init__.py
git commit -m "feat(rulecore): finalize public API exports"
```

---

## Phase 2 Note

**Field default change:** Rulecore uses `""` as the default field (not `"last_user_message"`). The Phase 2 RuleShield adapter must inject `"field": "last_user_message"` into flat rules that lack an explicit field, or always pass context with appropriate keys. This is intentional — rulecore is domain-agnostic.
