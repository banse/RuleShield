# Nested Condition Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add nested `all`/`any`/`not` condition trees to RuleShield's rule engine, enabling expressive boolean logic while preserving backward compatibility with all 75 existing flat rules.

**Architecture:** Optional `condition_tree` field on rules overrides the flat `patterns`+`conditions` path. A recursive `_evaluate_condition_tree` method walks branch nodes (`all`/`any`/`not`) and evaluates leaf nodes (pattern types + condition types), returning `(passed, score, matched_keywords, matched_patterns)`. Two new leaf types: `word_boundary` and `not_contains`.

**Tech Stack:** Python 3.11+, pytest, no new dependencies

**Spec:** `docs/superpowers/specs/2026-03-21-nested-condition-tree-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `ruleshield/rules.py` | Modify | Add `_evaluate_condition_tree`, `_validate_condition_tree`, update `_load_rules`, `_match_with_scope`, `get_active_rules` |
| `tests/unit/test_condition_tree.py` | Create | All unit tests for the tree evaluator |
| `tests/integration/test_condition_tree_loading.py` | Create | Integration test: load JSON with `condition_tree`, match through full pipeline |
| `rules/examples_nested.json` | Create | 3 example rules demonstrating `condition_tree` (reference only, not auto-loaded by default rules) |

---

### Task 1: Scaffold test file and first failing test — `all` node

**Files:**
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_condition_tree.py`

- [ ] **Step 1: Create test file with `all` pass/fail tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_condition_tree.py -v 2>&1 | tail -10`
Expected: FAIL — `AttributeError: 'RuleEngine' object has no attribute '_evaluate_condition_tree'`

- [ ] **Step 3: Commit test scaffold**

```bash
git add tests/unit/__init__.py tests/unit/test_condition_tree.py
git commit -m "test: add failing tests for condition tree all-node"
```

---

### Task 2: Implement `_evaluate_condition_tree` — core recursive evaluator

**Files:**
- Modify: `ruleshield/rules.py` (after `_conditions_met` method, ~line 920)

- [ ] **Step 1: Add the `_evaluate_condition_tree` method**

Add after `_conditions_met` (line 920) in `ruleshield/rules.py`:

```python
    # ---- condition tree evaluation ----

    _MAX_TREE_DEPTH = 10

    def _evaluate_condition_tree(
        self,
        node: dict[str, Any],
        text: str,
        msg_count: int,
        depth: int = 0,
    ) -> tuple[bool, float, list[str], list[str]]:
        """Evaluate a nested condition tree.

        Returns ``(passed, score, matched_keywords, matched_patterns)``.

        Branch nodes (``all``, ``any``, ``not``) recurse into children.
        Leaf nodes (``type`` key) evaluate a single pattern or condition.
        """
        if depth > self._MAX_TREE_DEPTH:
            import logging
            logging.getLogger("ruleshield.rules").warning(
                "Condition tree exceeded max depth %d", self._MAX_TREE_DEPTH,
            )
            return (False, 0.0, [], [])

        # ── Branch: all ──────────────────────────────────────────────
        if "all" in node:
            children = node["all"]
            total_score = 0.0
            all_kw: list[str] = []
            all_pat: list[str] = []
            for child in children:
                passed, sc, kw, pat = self._evaluate_condition_tree(
                    child, text, msg_count, depth + 1,
                )
                if not passed:
                    return (False, 0.0, [], [])
                total_score += sc
                all_kw.extend(kw)
                all_pat.extend(pat)
            return (True, total_score, all_kw, all_pat)

        # ── Branch: any ──────────────────────────────────────────────
        if "any" in node:
            children = node["any"]
            any_passed = False
            total_score = 0.0
            all_kw: list[str] = []
            all_pat: list[str] = []
            for child in children:
                passed, sc, kw, pat = self._evaluate_condition_tree(
                    child, text, msg_count, depth + 1,
                )
                if passed:
                    any_passed = True
                    total_score += sc
                    all_kw.extend(kw)
                    all_pat.extend(pat)
            if not any_passed:
                return (False, 0.0, [], [])
            return (True, total_score, all_kw, all_pat)

        # ── Branch: not ──────────────────────────────────────────────
        if "not" in node:
            child = node["not"]
            passed, _sc, _kw, _pat = self._evaluate_condition_tree(
                child, text, msg_count, depth + 1,
            )
            if passed:
                return (False, 0.0, [], [])
            return (True, 0.0, [], [])

        # ── Leaf node ────────────────────────────────────────────────
        return self._evaluate_leaf(node, text, msg_count)

    def _evaluate_leaf(
        self,
        node: dict[str, Any],
        text: str,
        msg_count: int,
    ) -> tuple[bool, float, list[str], list[str]]:
        """Evaluate a single leaf node in a condition tree."""
        ptype = node.get("type", "")
        value = node.get("value", "")
        field_text = self._resolve_field(
            node.get("field", "last_user_message"), text,
        )
        text_lower = field_text.lower()
        value_lower = str(value).lower() if isinstance(value, str) else ""

        # ── Score-contributing pattern leaves ─────────────────────────
        if ptype == "contains":
            if value_lower in text_lower:
                return (True, KEYWORD_WEIGHT, [value], [])
            return (False, 0.0, [], [])

        if ptype == "startswith":
            if text_lower.startswith(value_lower):
                return (True, KEYWORD_WEIGHT, [value], [])
            return (False, 0.0, [], [])

        if ptype == "exact":
            if text_lower == value_lower:
                return (True, EXACT_WEIGHT, [], [value])
            return (False, 0.0, [], [])

        if ptype == "regex":
            try:
                if _get_regex(value).search(field_text):
                    return (True, PATTERN_WEIGHT, [], [value])
            except re.error:
                pass
            return (False, 0.0, [], [])

        if ptype == "word_boundary":
            regex_pat = rf"\b{re.escape(value)}\b"
            try:
                if _get_regex(regex_pat).search(field_text):
                    return (True, KEYWORD_WEIGHT, [value], [])
            except re.error:
                pass
            return (False, 0.0, [], [])

        # ── Boolean gate leaves ───────────────────────────────────────
        if ptype == "not_contains":
            if value_lower in text_lower:
                return (False, 0.0, [], [])
            return (True, 0.0, [], [])

        if ptype == "max_length":
            if len(field_text) > int(value):
                return (False, 0.0, [], [])
            return (True, CONDITION_WEIGHT, [], [])

        if ptype == "min_length":
            if len(field_text) < int(value):
                return (False, 0.0, [], [])
            return (True, CONDITION_WEIGHT, [], [])

        if ptype == "max_messages":
            if msg_count > int(value):
                return (False, 0.0, [], [])
            return (True, CONDITION_WEIGHT, [], [])

        # Unknown leaf type — treat as failed.
        return (False, 0.0, [], [])
```

- [ ] **Step 2: Run tests to verify `all` node tests pass**

Run: `python3 -m pytest tests/unit/test_condition_tree.py::TestAllNode -v`
Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add ruleshield/rules.py
git commit -m "feat: add _evaluate_condition_tree recursive evaluator"
```

---

### Task 3: Tests for `any`, `not`, and nesting

**Files:**
- Modify: `tests/unit/test_condition_tree.py`

- [ ] **Step 1: Add `any`, `not`, and nesting test classes**

Append to `tests/unit/test_condition_tree.py`:

```python
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
        # Matches: contains "git" passes, not "github actions" passes
        passed, score, kw, pat = engine._evaluate_condition_tree(tree, "git push origin", 0)
        assert passed is True
        assert score == KEYWORD_WEIGHT + PATTERN_WEIGHT  # "git" + regex "push"
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
```

- [ ] **Step 2: Run all tests**

Run: `python3 -m pytest tests/unit/test_condition_tree.py -v`
Expected: 10 passed

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_condition_tree.py
git commit -m "test: add any, not, and nesting tests for condition tree"
```

---

### Task 4: Tests for new leaf types — `word_boundary` and `not_contains`

**Files:**
- Modify: `tests/unit/test_condition_tree.py`

- [ ] **Step 1: Add leaf type tests**

Append to `tests/unit/test_condition_tree.py`:

```python
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
        # "are" should match as a whole word
        passed1, _, _, _ = engine._evaluate_condition_tree(tree, "are you there", 0)
        assert passed1 is True
        # "are" inside "beware" should NOT match
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
        assert score == 0  # no score contribution
```

- [ ] **Step 2: Run tests**

Run: `python3 -m pytest tests/unit/test_condition_tree.py -v`
Expected: 15 passed

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_condition_tree.py
git commit -m "test: add word_boundary and not_contains leaf tests"
```

---

### Task 5: Tests for edge cases — depth limit, score threshold, condition scoring, max_messages

**Files:**
- Modify: `tests/unit/test_condition_tree.py`

- [ ] **Step 1: Add edge case tests**

Append to `tests/unit/test_condition_tree.py`:

```python
class TestDepthLimit:
    def test_exceeding_depth_returns_false(self, engine):
        """11-deep tree should fail gracefully."""
        # Build a tree 11 levels deep: all > all > all > ... > leaf
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
        assert result is None  # score 0 < min_score_threshold 1.5


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
        # "hello" matches patterns but not tree — should NOT fire
        result_hello = engine.match("hello", model="gpt-4o-mini")
        assert result_hello is None
        # "goodbye" matches tree — should fire
        result_bye = engine.match("goodbye", model="gpt-4o-mini")
        assert result_bye is not None
        assert result_bye["rule_id"] == "both_fields"
```

- [ ] **Step 2: Run tests — expect some failures (entry point not wired yet)**

Run: `python3 -m pytest tests/unit/test_condition_tree.py -v 2>&1 | tail -15`
Expected: `TestAllNode` etc. pass, but `TestScoreThresholdFiltering` and `TestBothFieldsPresent` fail because `_match_with_scope` doesn't handle `condition_tree` yet.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_condition_tree.py
git commit -m "test: add edge case tests — depth, threshold, scoring, both-fields"
```

---

### Task 6: Wire `condition_tree` into `_match_with_scope` and fix `_load_rules`

**Files:**
- Modify: `ruleshield/rules.py:446-487` (`_match_with_scope` scoring block)
- Modify: `ruleshield/rules.py:762-766` (`_load_rules` filter)
- Modify: `ruleshield/rules.py:562-578` (`get_active_rules`)

- [ ] **Step 1: Update `_match_with_scope` to handle `condition_tree`**

In `ruleshield/rules.py`, replace lines 472-487 (the scoring block inside the for-loop) with:

```python
            # ── Scoring: condition_tree path vs flat path ────────────
            if "condition_tree" in rule:
                passed, score, matched_kw, matched_pat = self._evaluate_condition_tree(
                    rule["condition_tree"], last_user_msg, msg_count,
                )
                if not passed or score < self.min_score_threshold:
                    continue
            else:
                if not self._conditions_met(rule, last_user_msg, msg_count):
                    continue

                score, matched_kw, matched_pat = self._score_rule(rule, last_user_msg)

                # Conditions only add bonus if a real pattern matched.
                if score > 0:
                    conditions = rule.get("conditions", [])
                    if conditions:
                        score += len(conditions) * CONDITION_WEIGHT

                if score < self.min_score_threshold:
                    continue
```

- [ ] **Step 2: Relax `_load_rules` filter**

In `ruleshield/rules.py`, change line 765 from:

```python
                    if "patterns" not in rule or "response" not in rule:
```

to:

```python
                    if ("patterns" not in rule and "condition_tree" not in rule) or "response" not in rule:
```

- [ ] **Step 3: Update `get_active_rules` to include `has_condition_tree`**

In `ruleshield/rules.py`, in the `get_active_rules` dict comprehension (~line 574), add after `"pattern_count"`:

```python
                "has_condition_tree": "condition_tree" in r,
```

- [ ] **Step 4: Run all tests**

Run: `python3 -m pytest tests/unit/test_condition_tree.py tests/smoke/ tests/integration/ -v`
Expected: ALL pass (including the edge case tests from Task 5 and all existing tests)

- [ ] **Step 5: Commit**

```bash
git add ruleshield/rules.py
git commit -m "feat: wire condition_tree into match pipeline, relax load filter"
```

---

### Task 7: Add `_validate_condition_tree` and validate on load

**Files:**
- Modify: `ruleshield/rules.py` (add validation method, call in `_load_rules`)
- Modify: `tests/unit/test_condition_tree.py` (validation tests)

- [ ] **Step 1: Add validation tests**

Append to `tests/unit/test_condition_tree.py`:

```python
class TestValidation:
    def test_valid_tree_accepted(self, engine):
        assert engine._validate_condition_tree(
            {"all": [{"type": "contains", "value": "hi", "field": "last_user_message"}]}
        ) is True

    def test_empty_all_rejected(self, engine):
        assert engine._validate_condition_tree({"all": []}) is False

    def test_not_with_list_rejected(self, engine):
        assert engine._validate_condition_tree(
            {"not": [{"type": "contains", "value": "hi", "field": "last_user_message"}]}
        ) is False

    def test_leaf_without_type_rejected(self, engine):
        assert engine._validate_condition_tree({"value": "hi"}) is False

    def test_unknown_branch_key_rejected(self, engine):
        assert engine._validate_condition_tree({"xor": [{"type": "contains", "value": "hi"}]}) is False

    def test_nested_valid_tree(self, engine):
        assert engine._validate_condition_tree({
            "all": [
                {"any": [
                    {"type": "contains", "value": "a", "field": "last_user_message"},
                    {"not": {"type": "exact", "value": "b", "field": "last_user_message"}},
                ]},
                {"type": "max_length", "value": 100, "field": "last_user_message"},
            ]
        }) is True
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/unit/test_condition_tree.py::TestValidation -v`
Expected: FAIL — `_validate_condition_tree` not defined

- [ ] **Step 3: Implement `_validate_condition_tree`**

Add to `RuleEngine` class in `ruleshield/rules.py`, before `_evaluate_condition_tree`:

```python
    @staticmethod
    def _validate_condition_tree(node: dict[str, Any]) -> bool:
        """Validate a condition tree structure recursively.

        Returns True if valid, False otherwise.  Does not raise.
        """
        if not isinstance(node, dict):
            return False

        # Branch nodes
        if "all" in node:
            children = node["all"]
            if not isinstance(children, list) or len(children) == 0:
                return False
            return all(RuleEngine._validate_condition_tree(c) for c in children)

        if "any" in node:
            children = node["any"]
            if not isinstance(children, list) or len(children) == 0:
                return False
            return all(RuleEngine._validate_condition_tree(c) for c in children)

        if "not" in node:
            child = node["not"]
            if not isinstance(child, dict):
                return False
            return RuleEngine._validate_condition_tree(child)

        # Leaf node — must have "type"
        if "type" not in node:
            return False

        # max_messages doesn't need "value" string but does need numeric value
        return True
```

- [ ] **Step 4: Call validation in `_load_rules`**

In `_load_rules`, after the relaxed filter check, add:

```python
                    # Validate condition_tree structure if present.
                    if "condition_tree" in rule:
                        if not self._validate_condition_tree(rule["condition_tree"]):
                            import logging
                            logging.getLogger("ruleshield.rules").warning(
                                "Skipping rule %s: invalid condition_tree",
                                rule.get("id", "<unknown>"),
                            )
                            continue
```

- [ ] **Step 5: Run all tests**

Run: `python3 -m pytest tests/unit/test_condition_tree.py tests/smoke/ tests/integration/ -v`
Expected: ALL pass

- [ ] **Step 6: Commit**

```bash
git add ruleshield/rules.py tests/unit/test_condition_tree.py
git commit -m "feat: add condition_tree validation on load"
```

---

### Task 8: Integration test — load from JSON, match through pipeline

**Files:**
- Create: `tests/integration/test_condition_tree_loading.py`
- Create: `rules/examples_nested.json`

- [ ] **Step 1: Create example rules JSON**

Create `rules/examples_nested.json`:

```json
[
  {
    "id": "nested_git_help",
    "name": "Git Help (not CI)",
    "description": "Matches git questions but excludes CI/Actions topics",
    "condition_tree": {
      "all": [
        {"any": [
          {"type": "word_boundary", "value": "git", "field": "last_user_message"},
          {"type": "regex", "value": "\\b(commit|push|pull|merge|rebase)\\b", "field": "last_user_message"}
        ]},
        {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
        {"type": "max_length", "value": 200, "field": "last_user_message"}
      ]
    },
    "response": {
      "content": "I can help with that git operation. What specifically do you need?",
      "model": "ruleshield-rule"
    },
    "confidence": 0.88,
    "priority": 7,
    "enabled": true,
    "hit_count": 0
  },
  {
    "id": "nested_short_greeting",
    "name": "Short Greeting (not question)",
    "description": "Matches short greetings that are not questions",
    "condition_tree": {
      "all": [
        {"any": [
          {"type": "exact", "value": "hi", "field": "last_user_message"},
          {"type": "exact", "value": "hello", "field": "last_user_message"},
          {"type": "exact", "value": "hey", "field": "last_user_message"}
        ]},
        {"type": "not_contains", "value": "?", "field": "last_user_message"},
        {"type": "max_length", "value": 10, "field": "last_user_message"}
      ]
    },
    "response": {
      "content": "Hey there! How can I help?",
      "model": "ruleshield-rule"
    },
    "confidence": 0.92,
    "priority": 11,
    "enabled": true,
    "hit_count": 0
  },
  {
    "id": "nested_code_review",
    "name": "Code Review Request",
    "description": "Detects code review requests with file context",
    "condition_tree": {
      "all": [
        {"any": [
          {"type": "word_boundary", "value": "review", "field": "last_user_message"},
          {"type": "contains", "value": "code review", "field": "last_user_message"},
          {"type": "contains", "value": "PR review", "field": "last_user_message"}
        ]},
        {"any": [
          {"type": "regex", "value": "\\.(py|js|ts|go|rs)$", "field": "last_user_message"},
          {"type": "contains", "value": "pull request", "field": "last_user_message"},
          {"type": "contains", "value": "diff", "field": "last_user_message"}
        ]}
      ]
    },
    "response": {
      "content": "I'd be happy to help review that code. Let me take a look at the changes.",
      "model": "ruleshield-rule"
    },
    "confidence": 0.85,
    "priority": 6,
    "enabled": true,
    "hit_count": 0
  }
]
```

- [ ] **Step 2: Create integration test**

Create `tests/integration/test_condition_tree_loading.py`:

```python
"""Integration test: load condition_tree rules from JSON, match through full pipeline."""

import asyncio
import json
import os
import tempfile
import shutil

import pytest
from ruleshield.rules import RuleEngine


@pytest.fixture
def rules_dir():
    """Create a temp directory with example nested rules."""
    tmpdir = tempfile.mkdtemp(prefix="ruleshield-test-")
    # Copy the examples_nested.json file
    src = os.path.join(os.path.dirname(__file__), "..", "..", "rules", "examples_nested.json")
    shutil.copy2(src, os.path.join(tmpdir, "examples_nested.json"))
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def engine(rules_dir):
    """Create a RuleEngine loaded from the temp rules dir."""
    e = RuleEngine(rules_dir=rules_dir)
    asyncio.run(e.init())
    return e


class TestConditionTreeLoading:
    def test_tree_rules_loaded(self, engine):
        assert len(engine.rules) == 3
        ids = [r["id"] for r in engine.rules]
        assert "nested_git_help" in ids
        assert "nested_short_greeting" in ids
        assert "nested_code_review" in ids

    def test_git_help_matches(self, engine):
        result = engine.match("how do I git push to remote?", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "nested_git_help"

    def test_git_help_blocked_by_ci(self, engine):
        result = engine.match("setup github actions for git push", model="gpt-4o-mini")
        assert result is None

    def test_short_greeting_matches(self, engine):
        result = engine.match("hi", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "nested_short_greeting"

    def test_greeting_question_blocked(self, engine):
        result = engine.match("hi?", model="gpt-4o-mini")
        # "hi?" fails: exact("hi") != "hi?" in the any-node, so no score.
        # The not_contains("?") would also block, but exact fails first.
        assert result is None

    def test_get_active_rules_shows_tree_flag(self, engine):
        active = engine.get_active_rules()
        tree_rule = next(r for r in active if r["id"] == "nested_git_help")
        assert tree_rule["has_condition_tree"] is True
        assert tree_rule["pattern_count"] == 0
```

- [ ] **Step 3: Run integration test**

Run: `python3 -m pytest tests/integration/test_condition_tree_loading.py -v`
Expected: ALL pass

- [ ] **Step 4: Run full test suite for backward compatibility**

Run: `python3 -m pytest tests/ -v`
Expected: ALL existing tests still pass + new tests pass

- [ ] **Step 5: Commit**

```bash
git add rules/examples_nested.json tests/integration/test_condition_tree_loading.py
git commit -m "feat: add example nested rules and integration tests"
```

---

### Task 9: Final verification and cleanup

**Files:**
- Modify: `ruleshield/rules.py` (docstring update only)

- [ ] **Step 1: Update module docstring**

Update the module docstring at the top of `ruleshield/rules.py` (lines 1-14) to mention condition trees:

```python
"""RuleShield Hermes -- Rule engine.

JSON-based pattern matching that intercepts LLM requests and returns
pre-computed responses, saving API costs for predictable prompts.

Enhanced with weighted matching patterns:
  - Weighted keyword + regex scoring (not just boolean matching).
  - Confidence levels (CONFIRMED/LIKELY/POSSIBLE) instead of simple float.
  - Dual-trigger matching: keyword AND context conditions scored together.
  - Minimum score threshold to prevent weak single-keyword false positives.
  - Score-based tie-breaking within the same priority tier.
  - Nested condition trees (all/any/not) for expressive boolean logic.

Performance target: < 2ms per match call.
"""
```

- [ ] **Step 2: Update `RuleEngine` class docstring**

Update the `RuleEngine` class docstring (~line 263) to mention condition trees:

```python
    """Matches incoming prompts against cost-saving rules.

    Rules are loaded from JSON files in a configurable directory.  On first
    init the engine copies bundled default rules into the user directory if it
    is empty, providing a useful out-of-the-box experience.

    Match semantics (flat rules):
      - Patterns are evaluated with OR logic (any match fires the rule).
      - Conditions are evaluated with AND logic (all must be satisfied).

    Match semantics (condition_tree rules):
      - Nested ``all``/``any``/``not`` boolean logic at any depth.
      - Leaf nodes support all pattern types plus ``word_boundary`` and
        ``not_contains``.
      - Overrides flat ``patterns``/``conditions`` when present.

    Common to both:
      - Rules are tried in descending priority order; first match wins.
      - Each successful match increments the rule's ``hit_count``.
      - Rules with confidence below ``deactivation_threshold`` are skipped.
    """
```

- [ ] **Step 3: Run full test suite one last time**

Run: `python3 -m pytest tests/ -v`
Expected: ALL pass

- [ ] **Step 4: Commit**

```bash
git add ruleshield/rules.py
git commit -m "docs: update rules.py docstrings for condition tree support"
```
