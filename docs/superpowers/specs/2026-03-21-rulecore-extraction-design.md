# Rulecore: Standalone Rule Engine Extraction

**Date:** 2026-03-21
**Status:** Approved
**Scope:** New `engine/rulecore/` package + Phase 2 migration of `ruleshield/`

## Summary

Extract RuleShield's pattern-matching rule engine and feedback loop into a standalone, zero-dependency Python package called `rulecore`. The engine handles weighted scoring, nested condition trees (`all`/`any`/`not`), configurable thresholds, and bandit-style feedback — with no ties to LLMs, HTTP, or any specific application domain.

Phase 1 copies and refactors into `engine/rulecore/` without touching RuleShield. Phase 2 migrates RuleShield to import from rulecore.

## Approach

**Subfolder extraction with protocol interfaces.** Code is copied from `ruleshield/rules.py` and `ruleshield/feedback.py` into `engine/rulecore/`, refactored to be domain-agnostic, and tested independently. RuleShield continues running on its own code until Phase 2 rewires imports.

## Package Structure

```
engine/rulecore/
├── __init__.py          # Public API: RuleEngine, MatchResult, Rule, ScoringConfig
├── engine.py            # RuleEngine class (matching, scoring dispatch, rule management)
├── scoring.py           # ScoringConfig, weight constants, confidence level computation
├── conditions.py        # Condition tree evaluator (all/any/not branches, leaf nodes)
├── feedback.py          # FeedbackManager: accept/reject, confidence deltas, analytics
├── store.py             # FeedbackStore protocol + JsonFileFeedbackStore
├── loader.py            # Rule loading from JSON, validation, state persistence
├── types.py             # TypedDicts/dataclasses: Rule, MatchResult, FeedbackEntry, RuleEvent
├── py.typed             # PEP 561 marker
└── tests/
    ├── __init__.py
    ├── test_engine.py
    ├── test_conditions.py
    ├── test_feedback.py
    ├── test_loader.py
    └── test_store.py
```

**Dependencies: zero.** Pure Python 3.9+ stdlib only.

## Public API

```python
from rulecore import RuleEngine, MatchResult, Rule, ScoringConfig
from rulecore.feedback import FeedbackManager
from rulecore.store import JsonFileFeedbackStore

# Initialize with configurable scoring
config = ScoringConfig(
    keyword_weight=1.0,
    pattern_weight=2.0,
    exact_weight=5.0,
    condition_weight=0.5,
    min_score=1.5,
)
engine = RuleEngine(rules_dir="./my_rules/", scoring=config)
engine.load()

# Match — consumer provides threshold and context
result: MatchResult | None = engine.match(
    context={"user_input": "hello there", "message_count": 3},
    confidence_threshold=0.75,
)

# Feedback loop (optional)
store = JsonFileFeedbackStore(path="./feedback.json")
feedback = FeedbackManager(engine=engine, store=store)
feedback.accept(rule_id="greeting_simple", prompt="hello there")
feedback.reject(rule_id="greeting_simple", prompt="hello there", correction="...")

# Analytics
underperforming = feedback.get_underperforming_rules(threshold=0.5)
stats = feedback.get_performance_by_category()
```

## Context Resolution

Rules resolve `"field"` against a generic `context: dict[str, Any]` instead of hardcoded "last_user_message":

```python
# Consumer passes context:
engine.match(context={"user_input": "git push", "channel": "slack", "msg_count": 5})

# Rules resolve fields:
{"type": "contains", "value": "git", "field": "user_input"}
{"type": "max_value", "value": 10, "field": "msg_count"}
{"type": "contains", "value": "slack", "field": "channel"}
```

**Field resolution:**
```python
def _resolve_field(field: str, context: dict[str, Any]) -> Any:
    if field not in context:
        return ""  # missing field = empty string, fails gracefully
    return str(context[field])
```

Existing RuleShield rules work unchanged — RuleShield passes `context={"last_user_message": text, "msg_count": n}`.

## Leaf Type Renaming

| Current (RuleShield) | Rulecore (generic) | Behavior |
|---|---|---|
| `max_messages` | `max_value` | Fails if `int(context[field]) > value` |
| `min_length` | `min_length` | Unchanged — string length check |
| `max_length` | `max_length` | Unchanged — string length check |
| All others | Same name | Unchanged |

`max_messages` is kept as an alias for `max_value` for backward compatibility.

## ScoringConfig

Configurable at engine init, defaults match current RuleShield values:

```python
@dataclass
class ScoringConfig:
    keyword_weight: float = 1.0      # contains, startswith, word_boundary
    pattern_weight: float = 2.0      # regex
    exact_weight: float = 5.0        # exact match
    condition_weight: float = 0.5    # max_length, min_length, max_value
    min_score: float = 1.5           # minimum score to fire a rule
```

## MatchResult

```python
@dataclass
class MatchResult:
    rule_id: str
    rule_name: str
    response: dict[str, Any]
    confidence: float
    match_score: float
    confidence_level: str            # CONFIRMED / LIKELY / POSSIBLE
    matched_keywords: list[str]
    matched_patterns: list[str]
    deployment: str                  # production / candidate
```

## FeedbackManager (Layers 1+2)

### Layer 1 — Core feedback loop
- `accept(rule_id, prompt)` — confidence += 0.01
- `reject(rule_id, prompt, correction=None)` — confidence -= 0.05
- `correct(rule_id, prompt, correction)` — confidence -= 0.03, logs correction
- Auto-deactivation below `deactivation_threshold` (default 0.5)
- Auto-promotion above `promotion_threshold` (default 0.85)
- Per-component tracking: `classification_correct`, `response_helpful`, `confidence_appropriate`

### Layer 2 — Analytics
- `get_underperforming_rules(threshold)` — rules below confidence threshold
- `get_performance_by_category()` — aggregate stats grouped by rule category
- `check_promotions()` — candidate rules meeting promotion criteria

### Layer 3 (NOT included) — RL stubs
`HermesRLInterface` with GRPO/Atropos and DSPy/GEPA placeholders stay in RuleShield app code.

## FeedbackStore Protocol

```python
class FeedbackStore(Protocol):
    def save_feedback(self, entry: FeedbackEntry) -> None: ...
    def save_event(self, event: RuleEvent) -> None: ...
    def load_feedback(self, rule_id: str) -> list[FeedbackEntry]: ...
    def load_events(self, rule_id: str) -> list[RuleEvent]: ...
```

Ships with `JsonFileFeedbackStore` (zero deps, JSON file persistence). RuleShield implements `SqliteFeedbackStore` wrapping `aiosqlite` in its own app code.

## Key Differences from Current RuleShield

| Aspect | RuleShield (current) | Rulecore (new) |
|---|---|---|
| Field resolution | Hardcoded `last_user_message` | Generic `context: dict[str, Any]` |
| Confidence threshold | `MODEL_CONFIDENCE_THRESHOLDS` dict | `confidence_threshold` parameter per `match()` call |
| Scoring weights | Module-level constants | `ScoringConfig` dataclass |
| Match result | Raw `dict` | `MatchResult` dataclass |
| Feedback storage | `aiosqlite` directly | `FeedbackStore` protocol |
| Lifecycle | `async init()` | Sync `load()` |
| Pricing | `pricing.py` bundled | Not included (LLM-specific) |

## What Rulecore Does NOT Include

- `MODEL_CONFIDENCE_THRESHOLDS` — LLM-specific, stays in RuleShield
- `pricing.py` — LLM-specific
- `cache.py` — app-level caching
- `template_optimizer.py` — prompt-specific
- `router.py` — LLM routing
- `proxy.py` — HTTP layer
- `codex_adapter.py` — API format translation
- `HermesRLInterface` — RL training stubs
- Any async code — the engine is synchronous

## Phase 1: Extract into `engine/rulecore/`

1. Create package structure
2. `types.py` — dataclasses for Rule, MatchResult, ScoringConfig, FeedbackEntry, RuleEvent
3. `scoring.py` — ScoringConfig, `compute_confidence_level()`
4. `conditions.py` — `evaluate_condition_tree()`, `evaluate_leaf()` extracted from `rules.py`
5. `loader.py` — rule loading, validation (`_validate_condition_tree`), state persistence
6. `engine.py` — `RuleEngine` class wiring loader + conditions + scoring
7. `store.py` — `FeedbackStore` protocol + `JsonFileFeedbackStore`
8. `feedback.py` — `FeedbackManager` with layers 1+2
9. `__init__.py` — public exports
10. Tests for each module
11. **Verification:** zero imports from `ruleshield/`, all tests pass standalone

RuleShield is completely untouched during Phase 1.

## Phase 2: Migrate RuleShield

1. `ruleshield/rules.py` becomes a thin adapter importing from `rulecore`:
   - Adds `MODEL_CONFIDENCE_THRESHOLDS` and `_get_model_threshold()`
   - Wraps `rulecore.RuleEngine` with async compat layer
   - Passes `context={"last_user_message": text, "msg_count": n}`
   - Same public API — no consumer changes
2. `ruleshield/feedback.py` becomes:
   - `SqliteFeedbackStore` implementing `rulecore.store.FeedbackStore`
   - `HermesRLInterface` stubs (app-specific)
   - Thin adapter wrapping `rulecore.FeedbackManager`
3. Run full RuleShield test suite — must pass identically
4. No logic changes, no behavior changes — pure re-wiring

**Phase 2 success criteria:** All 36 condition tree tests + 22 integration tests + smoke tests pass with the adapter wrappers.

## Testing Strategy

### Rulecore standalone tests
- `test_engine.py` — match, scoring, priority ordering, deployment modes
- `test_conditions.py` — all/any/not branches, all leaf types, depth limit, nesting
- `test_feedback.py` — accept/reject/correct deltas, auto-deactivation, analytics
- `test_loader.py` — JSON loading, validation, state persistence, backward compat
- `test_store.py` — JsonFileFeedbackStore read/write/load

### RuleShield adapter tests (Phase 2)
- Existing test suite runs unchanged against the adapter wrappers
- No new tests needed — existing coverage validates the migration

## Out of Scope

- PyPI publishing (future)
- Other repo integrations (future — after Phase 2 proves the API)
- Changes to proxy, cache, router, dashboard, or any other RuleShield module
- New engine features beyond what exists today
- Async API (engine is sync; consumers wrap if needed)

## Potential Future Consumers

- **RuleShield** — LLM cost optimizer (Phase 2)
- **autopet** (`/Library/Vibes/autopet`) — scheduler with action rules
- **skelgen** (`/Library/Vibes/toolkit/skelgen`) — template engine with generation rules
- Any future project needing configurable pattern matching with feedback
