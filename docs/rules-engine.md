# RuleShield Rules Engine and Feedback Loop

This document is the technical reference for the current `RuleShield Hermes` rules engine implementation.

It covers:

- rule schema and rule storage
- rule loading and persisted runtime state
- production vs candidate rule scopes
- weighted matching and score computation
- model-aware confidence thresholds
- live interception vs shadow evaluation
- shadow comparison mechanics
- feedback recording and confidence update math
- deactivation and promotion behavior
- current rule inventory on disk
- known limitations and operational interpretation

## Source of Truth

The implementation described here is based on these runtime modules:

- [rules.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/rules.py)
- [feedback.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/feedback.py)
- [proxy.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/proxy.py)
- [cache.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cache.py)

The active local rule packs referenced below come from:

- [default_hermes.json](/Users/banse/.ruleshield/rules/default_hermes.json)
- [hermes_advanced.json](/Users/banse/.ruleshield/rules/hermes_advanced.json)
- [suggested.json](/Users/banse/.ruleshield/rules/suggested.json)
- [shadow_control_rules.json](/Users/banse/.ruleshield/rules/candidates/shadow_control_rules.json)

## Runtime Role in the Proxy

The rule engine sits between cache lookup and the upstream LLM provider.

Request flow:

```text
incoming request
  -> cache lookup
  -> production rule evaluation
  -> candidate rule evaluation (shadow mode only)
  -> upstream passthrough if needed
  -> optional shadow comparison
  -> optional automatic feedback update
  -> optional promotion readiness tracking
```

This means the rule engine is not a standalone classifier. It is part of a control loop around real LLM traffic.

## Rule Storage Model

Rules are JSON objects. The engine loads them from the user rule directory:

- `~/.ruleshield/rules/*.json`
- `~/.ruleshield/rules/promoted/*.json`
- `~/.ruleshield/rules/candidates/*.json`

At runtime, mutable state is also merged from:

- `~/.ruleshield/rules/_state.json`

That `_state.json` file stores fields that evolve during use:

- `hit_count`
- `shadow_hit_count`
- `confidence`
- `enabled`
- `deployment`

So there are effectively two layers of state:

1. static rule definition JSON
2. mutable runtime state snapshot

## Rule Schema

Typical rule shape:

```json
{
  "id": "greeting_simple",
  "name": "Simple Greeting",
  "description": "Intercepts basic greetings like hello, hi, hey.",
  "patterns": [
    { "type": "exact", "value": "hello", "field": "last_user_message" },
    { "type": "contains", "value": "hello", "field": "last_user_message" },
    { "type": "regex", "value": "^(hi|hey)$", "field": "last_user_message" }
  ],
  "conditions": [
    { "type": "max_length", "value": 20, "field": "last_user_message" }
  ],
  "response": {
    "content": "Hello! How can I help?",
    "model": "ruleshield-rule"
  },
  "confidence": 0.95,
  "priority": 10,
  "enabled": true,
  "deployment": "production"
}
```

Core fields:

- `id`
- `name`
- `description`
- `patterns`
- `conditions`
- `response`
- `confidence`
- `priority`
- `enabled`
- `deployment`

Runtime fields:

- `hit_count`
- `shadow_hit_count`

## Rule Scopes

The engine separates rules into two scopes.

### Production rules

- `deployment = "production"`
- can intercept live requests
- increment `hit_count`
- can replace the live LLM response

### Candidate rules

- `deployment = "candidate"`
- never replace the live LLM response
- increment `shadow_hit_count`
- only participate in shadow comparison

This is one of the most important architectural boundaries in the current system.

## Rule Loading

`RuleEngine.init()` does the following:

1. expands the configured rules directory
2. ensures the directory exists
3. copies bundled defaults if no base JSON rule files exist
4. loads:
   - base rules
   - promoted rules
   - candidate rules
5. sorts all rules by descending priority
6. merges persisted runtime state from `_state.json`

`RuleEngine.reload()` repeats the same loading logic without reinitializing the object.

## Pattern Types

The current engine supports these pattern types:

- `contains`
- `startswith`
- `exact`
- `regex`

### `contains`

Case-insensitive substring match.

Example:

```json
{ "type": "contains", "value": "hello", "field": "last_user_message" }
```

### `startswith`

Case-insensitive prefix match.

### `exact`

Case-insensitive full-string equality.

This is the highest-specificity built-in matcher.

### `regex`

Case-insensitive regular expression, compiled through an internal regex cache.

Regexes are weighted more heavily because they are assumed to express more specific intent.

## Conditions

Conditions are evaluated separately from patterns.

Supported condition types:

- `max_length`
- `min_length`
- `max_messages`

Current field resolution is intentionally narrow:

- only `last_user_message` is effectively supported by `_resolve_field(...)`

Condition semantics:

- all conditions must pass
- if any condition fails, the rule is skipped

This is strict AND logic.

## Matching Semantics

The engine uses:

- OR logic for patterns
- AND logic for conditions

But it does not stop at boolean matching. It computes a weighted score and picks the best rule in the highest active priority tier.

### Entry points

- `match(...)` for production
- `match_candidates(...)` for candidates

Both delegate to:

```text
_match_with_scope(prompt_text, messages, model, deployment, hit_field)
```

The only scope-specific difference is which deployment is allowed and which counter is incremented.

## Weighted Scoring Algorithm

The rules engine uses weighted pattern scoring.

Weights:

```text
contains / startswith = 1.0
regex                 = 2.0
exact                 = 5.0
condition bonus       = 0.5 per satisfied condition
minimum score         = 1.5
```

### Why this matters

This prevents overly weak matches from firing.

Examples:

- a single exact match is usually enough to fire
- a single `contains` hit alone may be too weak
- conditions only strengthen a real match, they do not create one

### Important guard

Conditions only add bonus if a pattern already matched.

That prevents rules like:

- `max_length <= 20`

from accidentally matching all short prompts.

## Match Selection Logic

The engine iterates through rules in descending priority order.

Selection behavior:

1. skip disabled rules
2. skip rules from the wrong deployment scope
3. skip rules below the deactivation threshold
4. skip rules below the current model threshold
5. skip rules whose conditions fail
6. compute weighted score
7. reject scores below the minimum score threshold
8. keep the best-scoring rule within the highest active priority tier

Tie-breaking model:

- priority first
- score second

Once a best rule exists in a high-priority tier, lower tiers are ignored.

## Match Metadata

A successful match returns a structured object with:

- `response`
- `rule_id`
- `rule_name`
- `deployment`
- `confidence`
- `match_score`
- `confidence_level`
- `matched_keywords`
- `matched_patterns`
- `model_threshold`

This is useful because the engine does not just say “matched” or “not matched”. It also exposes why it matched.

## Confidence: Two Different Meanings

There are two confidence systems in the engine.

### 1. Numeric rule confidence

This is the mutable trust score stored on the rule itself.

Examples:

- `0.95`
- `0.78`
- `0.52`

This value changes over time through the feedback loop.

### 2. Discrete confidence level

This is derived from match structure and score.

Buckets:

- `CONFIRMED`
- `LIKELY`
- `POSSIBLE`
- `NONE`

Current logic:

- `CONFIRMED`
  - score `>= 4.0`
  - and both keyword + pattern evidence
- `LIKELY`
  - score `>= 2.0`
- `POSSIBLE`
  - score `> 0`
- `NONE`
  - no usable match

The discrete level is descriptive. The numeric confidence controls actual runtime eligibility.

## Model-Aware Confidence Thresholds

One of the most important algorithms in the engine is `_get_model_threshold(model)`.

It determines the minimum rule confidence required for the current model path.

Examples from the current threshold map:

- `gpt-5.1-codex-mini` -> `0.60`
- `gpt-5.2-codex` -> `0.70`
- `gpt-5.3-codex` -> `0.70`
- `gpt-5.1-codex-max` -> `0.80`
- `claude-haiku-*` -> `0.60`
- `claude-sonnet-*` -> `0.75`
- `claude-opus-*` -> `0.90`

Fallback logic:

1. exact model name match
2. provider prefix stripping
3. partial / heuristic match
4. size-based heuristic
5. final fallback to `0.70`

### Runtime effect

A rule with confidence `0.65`:

- may fire on `gpt-5.1-codex-mini`
- may be skipped on `gpt-5.3-codex`
- will definitely be skipped on `claude-opus-*`

This makes the rules engine risk-aware by model cost/quality tier.

## Hit Counters and Persistence

After a winning rule is chosen:

- `hit_count` is incremented for production matches
- `shadow_hit_count` is incremented for candidate matches

Runtime state is periodically flushed to `_state.json`.

This means:

- confidence changes persist across restarts
- disabled/promoted state persists
- hit history persists

## Shadow Mode

Shadow mode is implemented in the proxy, not inside the pure rule matcher.

Behavior:

1. the engine identifies a rule that would match
2. instead of intercepting, the request still goes to the real LLM
3. when the LLM response completes, the system compares:
   - rule response
   - real LLM response
4. the comparison is logged
5. strong results may trigger automatic feedback

This happens for:

- normal chat/completions
- Codex/Hermes `/responses`
- streamed responses
- tool/search-heavy response event sequences

## Shadow Comparison Algorithm

Shadow comparison is currently implemented by `_shadow_compare(...)`.

It extracts:

- rule text
- LLM text

Then computes:

### Jaccard similarity

```text
similarity = intersection(rule_words, llm_words) / union(rule_words, llm_words)
```

The comparison is based on lowercase word sets.

Strengths:

- deterministic
- cheap
- no embeddings required
- easy to audit

Weaknesses:

- harsh on paraphrase
- harsh on multilingual answers
- harsh on style changes
- harsh on emoji or punctuation differences

### Length ratio

```text
length_ratio = min(rule_len, llm_len) / max(rule_len, llm_len)
```

This is stored for analysis and diagnostics.

### Match quality bucket

- `good` if similarity `>= 0.8`
- `partial` if similarity `>= 0.4`
- `poor` otherwise

These buckets are used in reporting and to support promotion logic.

## Codex/Hermes Stream Extraction

For Hermes/Codex traffic, the proxy has to reconstruct final assistant text from streamed `/responses` events.

It now extracts text from multiple event types:

- `response.output_text.delta`
- `response.output_text.done`
- `response.content_part.done`
- `response.output_item.done`
- `response.completed`

Then it selects the best available assistant text instead of blindly relying on delta-only streams.

This matters because tool/search-heavy Codex flows do not always emit simple `delta` text.

## Shadow Log

Every shadow comparison is written to `shadow_log` with:

- `rule_id`
- `prompt_text`
- `rule_response`
- `llm_response`
- `similarity`
- `length_ratio`
- `match_quality`
- `created_at`

This table powers:

- `/api/shadow`
- the Shadow Lab dashboard
- `ruleshield shadow-stats`
- tuning workflows
- promotion checks

## Feedback Loop Overview

The feedback loop is implemented in `RuleFeedback`.

Its current job is:

- record accepts/rejects
- update numeric confidence
- deactivate weak rules
- identify promotable candidate rules

It does not yet rewrite rule patterns or response text automatically.

## Feedback Sources

Feedback can come from:

### Explicit feedback

Manual or external acceptance / rejection input.

### Automatic shadow feedback

Derived from shadow comparison results.

Current thresholds in `_apply_shadow_feedback(...)`:

- `accept` if similarity `>= 0.85`
- `reject` if similarity `< 0.50`
- otherwise:
  - log comparison
  - do not adjust confidence automatically

This middle band is intentionally conservative.

## Feedback Storage

Feedback is stored in `rule_feedback`.

Columns:

- `rule_id`
- `prompt_text`
- `rule_response`
- `feedback`
  - `accept`
  - `reject`
  - `correct`
- `correction`
- `classification_correct`
- `response_helpful`
- `confidence_appropriate`
- `created_at`

The boolean component columns are optional and support more fine-grained future evaluation.

## Confidence Update Algorithm in Detail

This is the core runtime adaptation mechanism.

Current parameters:

```text
acceptance_delta   = 0.01
rejection_delta    = 0.05
deactivation_threshold = 0.5
promotion_threshold    = 0.98
```

### Accept update

```text
new_confidence = current + acceptance_delta * (1 - current)
```

Behavior:

- bounded in `[0, 1]`
- approaches `1.0` asymptotically
- each additional accept has a smaller marginal effect

Example:

```text
current = 0.90
new = 0.90 + 0.01 * 0.10 = 0.901
```

### Reject update

```text
new_confidence = current - rejection_delta * current
```

Behavior:

- multiplicative decay
- stronger rules lose more in absolute terms per rejection
- repeated rejections push the rule downward quickly

Example:

```text
current = 0.90
new = 0.90 - 0.05 * 0.90 = 0.855
```

### Interpretation

The algorithm is safety-biased:

- rewards are small
- penalties are materially larger

That makes sense for a system whose job is to avoid false confident interception.

## Deactivation Logic

After every confidence update, `check_deactivations()` runs.

If:

```text
confidence < 0.5
```

then:

```text
enabled = false
```

This removes the rule from further matching.

Operationally:

- production rules stop intercepting
- candidate rules stop participating in shadow testing

This is a hard runtime consequence of poor performance.

## Promotion Logic

Promotion is currently conservative and candidate-only.

`check_promotions()` requires:

- `deployment == "candidate"`
- at least `10` shadow comparisons
- average shadow similarity `>= 0.80`
- acceptance rate `>= 0.85`
  - or no explicit feedback yet, if shadow evidence is already strong

When promoted through engine activation:

- `enabled = true`
- `deployment = "production"`

This changes the rule’s runtime scope from observation-only to live interception.

## Promotion Candidate Inspection

The feedback layer can compute richer promotion candidate data:

- current confidence
- shadow comparison count
- average shadow similarity
- feedback total
- acceptance rate
- `promotable` boolean

This is the basis for CLI and dashboard promotion workflows.

## Analytics Exposed by the Feedback Layer

The feedback module also exposes analysis helpers:

### Per-rule feedback stats

- accept count
- reject count
- total feedback
- acceptance rate
- current confidence

### Underperforming rules

Rules with:

- at least `min_feedback`
- acceptance rate below `70%`

### Performance by category

Categories are derived from the prefix before the first underscore in `rule_id`.

Example:

- `greeting_simple` -> `greeting`

### Component accuracy

Across:

- `classification_correct`
- `response_helpful`
- `confidence_appropriate`

These are not yet the primary live control signal, but they are already implemented for analysis.

## Current Local Rule Inventory

The following reflects the rules currently on disk in the local test environment.

### Default production rules

From [default_hermes.json](/Users/banse/.ruleshield/rules/default_hermes.json):

- `greeting_simple`
  - greetings like `hello`, `hi`, `hey`, `hallo`
- `status_check`
  - availability or status prompts like `are you there`, `ping`
- `acknowledgment`
  - short acknowledgments like `ok`, `thanks`, `got it`
- `simple_confirmation`
  - yes/no/proceed/continue style confirmations
- `capabilities_question`
  - `help`, `what can you do`, `how can you help`
- `goodbye`
  - `bye`, `goodbye`, `quit`
- `repeat_request`
  - `again`, `repeat that`, `one more time`
- `simple_math_counting`
  - regex-detected simple counting or arithmetic prompts

### Advanced production rules

From [hermes_advanced.json](/Users/banse/.ruleshield/rules/hermes_advanced.json):

- `file_listing_request`
  - file listing / directory listing prompts
- `read_file_request`
  - file reading / viewing prompts
- `run_command_confirmation`
  - short confirmations to run/execute
- `task_completion_ack`
  - done/finished/nothing-else style closers
- `error_retry_request`
  - retry/redo/try-again prompts
- `show_explain_error`
  - what-went-wrong / show-error prompts
- `undo_revert_request`
  - undo / revert / go back requests
- `save_commit_request`
  - save / commit / git commit prompts
- `show_diff_changes`
  - diff / what changed
- `skip_next_request`
  - skip / next / move on
- `wait_pause_request`
  - wait / hold on / pause / one sec
- `clarification_request`
  - general clarification-like short prompts

### Suggested production rules

From [suggested.json](/Users/banse/.ruleshield/rules/suggested.json):

- `suggested_3a9fb9a0`
  - CPU acronym explanation
- `suggested_ec8ee852`
  - boiling point of water

These come from observed request similarity and represent auto-suggested, still human-readable rule artifacts.

### Candidate rules

From [shadow_control_rules.json](/Users/banse/.ruleshield/rules/candidates/shadow_control_rules.json):

- `shadow_control_any_model`
  - control candidate used for stable shadow diagnostics
- `shadow_model_threshold_probe`
  - candidate designed to probe model-threshold-dependent matching behavior

These are specifically useful in testing and shadow-mode diagnostics rather than as end-user production rules.

## Productive Interpretation of the Current Design

The engine is best understood as a deterministic matcher with adaptive gating.

Deterministic core:

- weighted pattern scoring
- priority tiers
- explicit conditions
- explicit rule responses

Adaptive shell:

- model-aware confidence thresholds
- shadow comparison
- feedback-driven confidence updates
- auto-deactivation
- candidate promotion

That makes the system neither static nor fully generative. It is a controlled adaptive rules system.

## Known Limitations

Important current limitations:

1. Similarity is lexical, not semantic
   - paraphrases can score low
   - multilingual answers can score near zero

2. Feedback tunes confidence only
   - it does not rewrite rule text automatically

3. Condition support is intentionally narrow
   - little conversation-state awareness today

4. Candidate promotion is conservative by design
   - good for safety
   - slow for rapid iteration

5. Rule responses must match real assistant style
   - otherwise the feedback loop will correctly push them downward

## Operational Guidance

When interpreting shadow or feedback behavior:

- low similarity does not always mean wrong intent
- it often means style mismatch or language mismatch
- repeated rejects near the `0.5` threshold should be taken seriously
- candidate rules are the safe place to test new response shapes
- production rules should only stay active if they match real assistant behavior closely enough

## Summary

The current RuleShield engine is a weighted, priority-driven rule system with:

- deterministic matching
- model-aware gating
- shadow-mode observation
- conservative confidence updates
- automatic deactivation for weak rules
- promotion logic for proven candidates

The feedback algorithm is deliberately asymmetric:

- good evidence increases confidence slowly
- bad evidence decreases confidence faster

That asymmetry is the main safety mechanism of the current engine.
