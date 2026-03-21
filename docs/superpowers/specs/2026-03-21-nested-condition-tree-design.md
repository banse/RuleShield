# Nested Condition Tree for RuleShield Rule Engine

**Date:** 2026-03-21
**Status:** Approved
**Scope:** `ruleshield/rules.py` only

## Summary

Port json-rules-engine's nested `all`/`any`/`not` condition model into RuleShield's Python rule engine. This makes rules far more expressive (AND, OR, NOT combinations at any depth) without adding a JS dependency, while preserving weighted scoring, confidence thresholds, model-aware gating, and shadow deployment.

## Approach

**Wrap-around (Option B):** Add an optional `condition_tree` field to the rule JSON format. When present, it overrides the flat `patterns` + `conditions` arrays. When absent, the existing matching path runs unchanged. Zero migration needed for 75 existing rules.

## Rule JSON Format

### Existing (unchanged)

```json
{
  "id": "greeting_simple",
  "patterns": [
    {"type": "exact", "value": "hello", "field": "last_user_message"}
  ],
  "conditions": [
    {"type": "max_length", "value": 20, "field": "last_user_message"}
  ],
  "response": {"content": "Hello!", "model": "ruleshield-rule"},
  "confidence": 0.95,
  "priority": 10,
  "enabled": true
}
```

### New `condition_tree` format

```json
{
  "id": "complex_git_help",
  "name": "Git Help (not CI)",
  "condition_tree": {
    "all": [
      {"any": [
        {"type": "contains", "value": "git", "field": "last_user_message"},
        {"type": "word_boundary", "value": "commit", "field": "last_user_message"},
        {"type": "regex", "value": "\\b(push|pull|merge|rebase)\\b", "field": "last_user_message"}
      ]},
      {"not": {"type": "contains", "value": "github actions", "field": "last_user_message"}},
      {"type": "max_length", "value": 200, "field": "last_user_message"}
    ]
  },
  "response": {"content": "I can help with that git operation...", "model": "ruleshield-rule"},
  "confidence": 0.88,
  "priority": 7,
  "enabled": true
}
```

## Branch Nodes

| Node | Value | Passes when | Score |
|------|-------|-------------|-------|
| `all` | Array of children | ALL children pass | Sum of all child scores |
| `any` | Array of children | At least ONE child passes | Sum of all *passing* children's scores |
| `not` | Single child dict | Child FAILS | Always 0 (boolean gate) |

## Leaf Node Types

### Score-contributing (pattern leaves)

| Type | Weight | Behavior |
|------|--------|----------|
| `contains` | 1.0 (KEYWORD_WEIGHT) | Case-insensitive substring match |
| `startswith` | 1.0 (KEYWORD_WEIGHT) | Case-insensitive prefix match |
| `exact` | 5.0 (EXACT_WEIGHT) | Case-insensitive exact match |
| `regex` | 2.0 (PATTERN_WEIGHT) | Case-insensitive regex search |
| `word_boundary` | 1.0 (KEYWORD_WEIGHT) | **New.** Auto-wraps value in `\b...\b`. Matches whole words only. |

### Boolean gates (condition leaves, score = 0)

| Type | Behavior |
|------|----------|
| `max_length` | Fails if text length > value |
| `min_length` | Fails if text length < value |
| `max_messages` | Fails if message count > value |
| `not_contains` | **New.** Fails if value is present (substring). Convenience for `{"not": {"type": "contains", ...}}` |

## Evaluation Logic

### Entry point change in `_match_with_scope`

```python
if "condition_tree" in rule:
    passed, score, matched_kw, matched_pat = self._evaluate_condition_tree(
        rule["condition_tree"], last_user_msg, msg_count
    )
    if not passed or score < self.min_score_threshold:
        continue
else:
    # Existing flat path — completely unchanged
    if not self._conditions_met(rule, last_user_msg, msg_count):
        continue
    score, matched_kw, matched_pat = self._score_rule(rule, last_user_msg)
    if score > 0:
        conditions = rule.get("conditions", [])
        if conditions:
            score += len(conditions) * CONDITION_WEIGHT
    if score < self.min_score_threshold:
        continue
```

### Recursive evaluator

```python
def _evaluate_condition_tree(
    self, node: dict, text: str, msg_count: int, depth: int = 0
) -> tuple[bool, float, list[str], list[str]]:
    """Evaluate a nested condition tree.

    Returns (passed, score, matched_keywords, matched_patterns).
    """
```

**`all` node:** Evaluate every child. If any child fails → `(False, 0, [], [])`. Otherwise return `(True, sum_scores, merged_kw, merged_pat)`.

**`any` node:** Evaluate every child (don't short-circuit — need scores from all passing children). If no child passes → `(False, 0, [], [])`. Otherwise return `(True, sum_of_passing_scores, merged_kw, merged_pat)`.

**`not` node:** Evaluate single child. If child passed → `(False, 0, [], [])`. If child failed → `(True, 0, [], [])`. Never contributes score.

**Leaf node:** Resolve field via `_resolve_field`. Evaluate based on `type`:
- Pattern types: return `(matched, weight, [value] or [], [value] or [])`
- Condition types: return `(passed, 0, [], [])`

**Depth limit:** Max 10. Beyond that, return `(False, 0, [], [])` and log a warning.

## `word_boundary` Implementation

```python
regex_pat = rf"\b{re.escape(value)}\b"
if _get_regex(regex_pat).search(field_text):
    return (True, KEYWORD_WEIGHT, [value], [])
```

Uses `re.escape` so users write plain words, not regex. Cached via existing `_get_regex`.

## `not_contains` Implementation

```python
if value_lower in text_lower:
    return (False, 0, [], [])  # present = fail
return (True, 0, [], [])       # absent = pass, no score
```

## Validation on Load

In `_load_rules`, validate `condition_tree` when present:
- Must be a dict with exactly one key from: `all`, `any`, `not`, or a leaf `type`
- `all`/`any` values must be non-empty lists
- `not` value must be a dict (not a list)
- Leaf nodes must have `type` and `value` keys (except `max_messages` which uses msg_count)
- Invalid rules are skipped with a logged warning (no crash)

~30 lines, pure dict validation, no schema library.

## Testing

### Unit tests for `_evaluate_condition_tree`

1. `all` passes when all children pass, fails when one fails
2. `any` passes when one child passes, fails when none pass
3. `not` inverts child result, contributes zero score
4. Nested 3-deep: `all` > `any` > `not` evaluates correctly
5. Score accumulation: `any` with 3 matching children sums all 3 scores
6. Depth limit: 11-deep tree returns `(False, 0, [], [])` gracefully
7. `word_boundary`: "commit" matches "git commit" but not "recommit"
8. `not_contains`: blocks when value present, passes when absent

### Integration test

Load a rule JSON file with `condition_tree`, run through `match()`, verify correct rule fires with expected score.

### Backward compatibility

Run the full existing test suite unchanged — all 75 flat rules must match identically.

## Out of Scope

- No changes to proxy, cache, feedback, router, or any other module
- No dashboard changes (tree display is a future enhancement)
- No migration of existing rules to tree format
- No new API endpoints

## Example Rules (reference only, not auto-loaded)

A `rules/examples_nested.json` file with 2-3 rules demonstrating `condition_tree` usage for documentation purposes.
