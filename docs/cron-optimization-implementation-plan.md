# Cron Optimization Implementation Plan

This document turns the cron optimization spec into a concrete implementation plan.

It is organized around:

- target architecture
- new artifacts and modules
- CLI and API changes
- storage model
- validation flow
- phased implementation
- testing and rollout

This plan assumes the architectural direction from [cron-optimization-spec.md](/Users/banse/codex/hermes/ruleshield-hermes/docs/cron-optimization-spec.md):

- do not treat recurring jobs as ordinary rules
- introduce a `Cron Optimization Profile`
- optimize by decomposition, compact prompting, and shadow validation

## Goals

The first implementation should make it possible to:

1. detect recurring cron-like prompts
2. generate a structured optimization draft
3. estimate savings
4. compare original and optimized execution in shadow
5. keep activation explicit and reversible

## Non-Goals for V1

Do not build these in the first version:

- a general-purpose scheduler
- direct mailbox or SaaS integrations for every source
- full autonomous prompt-to-workflow conversion
- production auto-activation without operator review
- complex UI-heavy workflow editing

## Target Architecture

The feature should add a parallel artifact type next to rules:

```text
rules/
  production rules
  candidate rules

cron_profiles/
  draft profiles
  active profiles
  state / validation metadata
```

Runtime model:

```text
request_log
  -> recurring workflow detection
  -> decomposition
  -> cron optimization profile
  -> optional shadow validation
  -> optional activation
```

## New Artifact: Cron Optimization Profile

### Proposed storage location

Use:

```text
~/.ruleshield/cron_profiles/
```

Subdirectories:

```text
~/.ruleshield/cron_profiles/drafts/
~/.ruleshield/cron_profiles/active/
```

Optional later:

```text
~/.ruleshield/cron_profiles/_state.json
```

### Proposed schema

```json
{
  "id": "mail_digest_daily",
  "name": "Daily Mail Digest",
  "status": "draft",
  "source": {
    "prompt_hash": "abc123...",
    "prompt_text": "please check my mails every day at 8 am ..."
  },
  "detection": {
    "occurrences": 12,
    "estimated_family_size": 1,
    "schedule_like": true
  },
  "decomposition": {
    "control_steps": [
      "schedule daily at 08:00",
      "fetch mailbox"
    ],
    "preprocess_steps": [
      "strip signatures",
      "group by category"
    ],
    "llm_task": "Summarize these categorized emails in the required output format.",
    "postprocess_steps": [
      "render markdown digest"
    ]
  },
  "optimized_execution": {
    "input_binding": "categorized_mail_batch",
    "prompt_template": "Summarize this categorized email content in the following format: ...",
    "expected_output_format": "markdown_digest"
  },
  "estimates": {
    "token_reduction_pct": 62.0,
    "cost_reduction_pct": 58.0,
    "tool_reduction_pct": 50.0
  },
  "validation": {
    "shadow_runs": 0,
    "avg_similarity": 0.0,
    "acceptance_rate": 0.0,
    "optimization_confidence": 0.0
  },
  "created_at": "2026-03-15T00:00:00Z"
}
```

## New Runtime Concepts

### 1. Workflow candidate

An entry detected from request logs that looks cron-like or recurring enough to be worth optimization.

### 2. Optimization profile

A structured draft or active optimized recurring workflow.

### 3. Optimization confidence

A validation score for the optimized workflow, distinct from rule confidence.

This should represent:

- output fidelity
- structure correctness
- operator acceptance
- consistency across runs

## Files and Modules

## New Python modules

### `ruleshield/cron_optimizer.py`

Responsibilities:

- recurring workflow detection
- prompt family analysis
- decomposition into control/preprocess/llm/postprocess
- profile creation and loading
- savings estimation

Main classes / functions:

- `CronOptimizationProfile`
- `CronOptimizer`
- `detect_recurring_workflows(...)`
- `suggest_profile(...)`
- `estimate_profile_savings(...)`

### `ruleshield/cron_validation.py`

Responsibilities:

- shadow comparison between original and optimized execution
- validation run logging
- optimization confidence calculation

Main classes / functions:

- `CronValidationRunner`
- `compare_original_vs_optimized(...)`
- `compute_optimization_confidence(...)`

### `ruleshield/hermes_runner.py`

Responsibilities:

- minimal Hermes Python library execution wrapper
- compact prompt invocation
- consistent parameter defaults for cron-like tasks

Main classes / functions:

- `HermesRunner`
- `run_compact_task(...)`

This wrapper is especially useful if we want:

- `quiet_mode=True`
- `skip_memory=True`
- `skip_context_files=True`
- restricted toolsets for recurring jobs

## Existing files to extend

### [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)

Add commands:

- `analyze-crons --structured`
- `suggest-cron-profile`
- `list-cron-profiles`
- `show-cron-profile`
- `run-cron-shadow`
- `activate-cron-profile`

### [mcp_server.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/mcp_server.py)

Add tools:

- `ruleshield_suggest_cron_profile`
- `ruleshield_list_cron_profiles`
- `ruleshield_run_cron_shadow`

### [proxy.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/proxy.py)

Add endpoints:

- `GET /api/cron-profiles`
- `GET /api/cron-profiles/{id}`
- `POST /api/cron-profiles/suggest`
- `POST /api/cron-profiles/{id}/shadow-run`
- `POST /api/cron-profiles/{id}/activate`

### Dashboard

Potential later pages:

- `/cron-lab`
- profile detail page
- validation history view

For V1, CLI-first is enough.

## Storage Model

## File storage

Use JSON files for profile definitions.

Why:

- matches the existing rules workflow
- easy to diff and inspect
- easy to review manually
- low implementation overhead

## SQLite storage

Use SQLite for validation runs and metrics.

### Proposed new table: `cron_profile_validation`

```sql
CREATE TABLE IF NOT EXISTS cron_profile_validation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    source_prompt_hash TEXT,
    original_prompt TEXT,
    optimized_prompt TEXT,
    original_output TEXT,
    optimized_output TEXT,
    similarity REAL,
    length_ratio REAL,
    structure_ok BOOLEAN,
    accepted BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Optional later:

### `cron_profile_runs`

For execution stats and savings over time.

## Detection Algorithm

V1 detection should remain simple and auditable.

### Inputs

- `request_log`
- prompt occurrence count
- prompt hash frequency
- repeated text skeletons

### Detection heuristics

A recurring workflow candidate is more likely when:

- the prompt appears multiple times
- it contains schedule-related phrases
- it contains multiple imperative verbs
- it looks like orchestration rather than a simple question

Suggested schedule-like keyword set:

- `every day`
- `daily`
- `every morning`
- `every week`
- `at 8 am`
- `at 9`
- `each day`
- `schedule`
- `check my`
- `send me`
- `summarize and send`

### Output

Detection result should classify a prompt as:

- `static recurring prompt`
- `dynamic recurring workflow`
- `not enough evidence`

That split is important because:

- static recurring prompts fit `promote-rule`
- dynamic workflows fit cron profiles

## Decomposition Algorithm

The decomposition step should be conservative.

V1 should not try to infer arbitrary logic trees.

Instead, it should classify segments into:

- control language
- data acquisition language
- preprocessing language
- LLM reasoning request
- output formatting language

### Initial approach

Heuristic decomposition using keyword families and clause splitting.

Example:

```text
please check my mails every day at 8 am and then sort them by category and summarize every category and return with a formatted output
```

Possible decomposition:

- control:
  - every day at 8 am
- fetch:
  - check my mails
- preprocess:
  - sort them by category
- llm task:
  - summarize every category
- postprocess:
  - return with formatted output

### Future approach

Use a model-assisted decomposition step if heuristics are too weak.

But V1 should keep decomposition inspectable and debuggable.

## Savings Estimation

The profile generator should estimate:

- original prompt length
- compact prompt length
- expected token reduction
- expected cost reduction
- expected reduction in unnecessary tool orchestration

### Estimation model

V1 can be simple:

```text
token_reduction_pct =
  (original_prompt_tokens - optimized_prompt_tokens) / original_prompt_tokens
```

Tool reduction can be estimated heuristically:

- if deterministic fetch/preprocess/postprocess steps are removed from the LLM path, count them as avoided orchestration steps

This estimate does not need to be perfect to be useful.

## Shadow Validation for Cron Profiles

This is the most important safety mechanism.

### Execution model

For a profile shadow run:

1. execute the original full prompt path
2. execute the optimized compact path
3. compare outputs
4. store validation evidence

### Comparison model

V1 can reuse the same current comparison primitives:

- Jaccard similarity
- length ratio
- simple structure checks

But it should add one more signal:

- output format check

For example:

- expected headings
- expected category count
- expected markdown block structure

### Optimization confidence proposal

Initial formula:

```text
optimization_confidence =
  0.6 * similarity
  + 0.2 * structure_score
  + 0.2 * acceptance_rate
```

This should be stored separately from rule confidence.

## CLI Plan

## Phase 1 commands

### `ruleshield analyze-crons --structured`

Purpose:

- detect recurring workflow-like prompts
- classify them as static or dynamic

Output:

- occurrences
- cache/rule rate
- workflow-likeness
- recommendation

### `ruleshield suggest-cron-profile <prompt-hash-or-text>`

Purpose:

- create a draft optimization profile from a recurring prompt

Output:

- saved profile path
- decomposition preview
- savings estimate

## Phase 2 commands

### `ruleshield list-cron-profiles`

Purpose:

- list draft and active profiles

### `ruleshield show-cron-profile <id>`

Purpose:

- inspect profile details

### `ruleshield run-cron-shadow <id>`

Purpose:

- execute original vs optimized flow side by side

## Phase 3 commands

### `ruleshield activate-cron-profile <id>`

Purpose:

- explicitly activate a validated optimized profile

## API Plan

V1 API should be thin and map closely to the CLI.

### `GET /api/cron-profiles`

Return:

- all profiles with status and validation summary

### `GET /api/cron-profiles/{id}`

Return:

- full profile document

### `POST /api/cron-profiles/suggest`

Input:

- prompt hash or text selector

Return:

- created draft profile

### `POST /api/cron-profiles/{id}/shadow-run`

Return:

- comparison result
- validation summary

### `POST /api/cron-profiles/{id}/activate`

Return:

- updated profile status

## Hermes Python Library Integration Plan

The compact execution path should use a dedicated wrapper instead of ad hoc calls.

### Why

Recurring tasks usually want:

- less chatter
- less memory/context accumulation
- narrower tool access

### Suggested defaults for compact recurring tasks

- `quiet_mode=True`
- `skip_memory=True`
- `skip_context_files=True`
- optional explicit `enabled_toolsets`

### Wrapper responsibilities

- create Hermes agent instance
- inject compact task prompt
- pass normalized payload
- return normalized result object

## Phase Breakdown

## Phase 1: Structured Cron Analysis

### Scope

- extend `analyze-crons`
- detect workflow-like recurring prompts
- output recommendations

### Files

- [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)
- [mcp_server.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/mcp_server.py)
- new [cron_optimizer.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cron_optimizer.py)

### Deliverable

- useful analysis without changing runtime behavior

## Phase 2: Draft Profile Generation

### Scope

- define profile schema
- create draft profile files
- estimate savings

### Files

- new [cron_optimizer.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cron_optimizer.py)
- optional helpers in `config.py` for profile dirs
- [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)

### Deliverable

- `suggest-cron-profile`
- draft profile artifacts on disk

## Phase 3: Shadow Validation

### Scope

- run original and optimized execution paths
- compare results
- persist validation

### Files

- new [cron_validation.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cron_validation.py)
- new [hermes_runner.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/hermes_runner.py)
- [cache.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cache.py) or a neighboring DB helper
- [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)

### Deliverable

- shadow comparison for cron profiles

## Phase 4: Activation

### Scope

- explicit activation flow
- active profile storage
- runtime status tracking

### Files

- [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)
- [proxy.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/proxy.py) if API activation is added

### Deliverable

- validated optimized cron path can be used in practice

## Phase 5: Dashboard Support

### Scope

- profile list
- validation metrics
- savings view

### Files

- dashboard routes and pages

### Deliverable

- operator-friendly visibility

## Testing Plan

## Unit tests

Test:

- recurring workflow detection
- decomposition heuristics
- profile serialization
- savings estimation
- optimization confidence math

## Integration tests

Test:

- `suggest-cron-profile`
- shadow validation end to end
- activation state transitions

## Demo scenario tests

Use representative recurring jobs:

- daily email digest
- daily system summary
- recurring report summarizer
- repeated file-based status aggregation

## Rollout Plan

### Stage 1

Analysis only

- no runtime switching
- no activation

### Stage 2

Draft profiles + shadow validation

- still no automatic replacement

### Stage 3

Explicit activation for selected profiles

### Stage 4

Optional future auto-activation only after strong evidence

## Risks and Safeguards

### Risk: profile overreach

A prompt may be decomposed incorrectly.

Safeguard:

- draft-only first
- explicit review

### Risk: optimized prompt drops critical context

Safeguard:

- original vs optimized shadow comparison

### Risk: too much surface area in V1

Safeguard:

- keep V1 CLI-first
- no scheduler ownership
- no broad connector framework

## Recommended Build Order

If implemented now, the best order is:

1. `cron_optimizer.py`
2. `analyze-crons --structured`
3. `suggest-cron-profile`
4. profile storage + schema
5. `hermes_runner.py`
6. `cron_validation.py`
7. `run-cron-shadow`
8. activation path
9. dashboard support

## Summary

The first implementation should not try to be a universal automation platform.

It should be a focused optimizer for recurring agent jobs:

- detect repeated workflow prompts
- split deterministic and non-deterministic work
- create a compact execution profile
- validate optimized execution in shadow
- allow explicit activation only when proven

That is the smallest implementation that matches the product idea while staying aligned with RuleShield’s existing architecture and safety model.
