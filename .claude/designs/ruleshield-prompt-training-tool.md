# RuleShield Prompt Training Tool - Design Document

**Mode**: Standard
**Date**: 2026-03-15
**Status**: Final

## Problem Statement

We need an automated training tool for **RuleShield**, not for Hermes itself.

The tool should drive Hermes through its Python API so Hermes behaves like a realistic coding assistant, while RuleShield observes that traffic in shadow mode and learns from it. The goal is to generate compact, repeatable, realistic prompt traffic that improves RuleShield’s rule quality, feedback loop usefulness, and future rule-pack tuning.

This is a data-generation and calibration problem:

- generate realistic traffic through Hermes
- keep runtime short
- keep Hermes token cost low
- make the traffic useful for RuleShield shadow comparisons and feedback
- isolate all file changes to a dedicated test workspace

## Understanding

### Facts

- RuleShield already supports:
  - shadow mode
  - rule feedback
  - confidence updates
  - rule event logging
  - request logging
- We already have a manual realism baseline in [rules-engine-operations.md](/Users/banse/codex/hermes/ruleshield-hermes/docs/rules-engine-operations.md).
- We already have a dedicated operator-facing day-in-the-life guide in [dashboard/src/routes/docs/day-in-life/+page.svelte](/Users/banse/codex/hermes/ruleshield-hermes/dashboard/src/routes/docs/day-in-life/+page.svelte).
- Hermes Python API usage patterns already exist locally in [ruleshield/hermes_bridge.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/hermes_bridge.py).
- Hermes is the actor generating realistic assistant behavior.
- RuleShield is the system being trained and evaluated.

### Context

- Manual day-in-the-life testing is realistic but expensive and slow.
- Pure synthetic prompt replay is cheap but often not realistic enough.
- The training tool should sit between those extremes:
  - realistic enough to stress RuleShield
  - cheap enough to run often
  - deterministic enough to compare runs
- The user wants the first scenario to feel like a vibecoder building a small dashboard.

### Constraints

- Runtime should be in minutes, not hours.
- Hermes cost should stay minimal.
- The scenario should still feel like normal usage.
- The test should run in a dedicated project directory.
- Hermes should not write or modify files outside that directory during the run.
- The design should stay simple and KISS-oriented.

### Unknowns (Resolved)

- [x] Can Hermes be driven from Python in a lightweight way?
  - Yes, local code already uses `AIAgent(...)` with cost-saving flags.
- [x] Do we have a realistic prompt-family baseline already?
  - Yes, current RuleShield operations docs already define realistic day-in-the-life families.

### Unknowns (Open)

- [ ] Exact Hermes Python API details we should lock to for V1 runner construction.
- [ ] Whether Hermes still writes additional runtime state under `HOME` even with memory/context skipping enabled.
- [ ] Whether filesystem isolation needs only env/cwd controls or a stronger sandbox in practice.

## Research & Input

Two local design signals matter most:

1. RuleShield testing philosophy:
   - realism beats synthetic perfection
   - prompt families matter more than one repeated phrase
   - shadow mode and feedback movement are the main outputs

2. Hermes embedding pattern:
   - Hermes can be run as a Python-driven agent
   - `quiet_mode=True`, `skip_context_files=True`, and `skip_memory=True` are already part of the local low-cost pattern

The official Hermes Python library guide at [hermes-agent.nousresearch.com/docs/guides/python-library](https://hermes-agent.nousresearch.com/docs/guides/python-library) should remain the external alignment point for the actual implementation.

## What We Are Actually Building

We are not building a Hermes benchmark.

We are building a **RuleShield traffic trainer** that uses Hermes as the prompt-driven worker.

The tool should:

- create a fresh workspace
- route Hermes through RuleShield proxy with shadow mode enabled
- run a realistic short scenario
- collect RuleShield outputs:
  - shadow comparisons
  - feedback entries
  - confidence changes
  - rule events
- produce a compact training report

The first scenario should be:

**Vibecoder builds a small useful dashboard**

Recommended dashboard use case:

**Personal Work Session Dashboard**

The seeded project contains local synthetic fixture data for:

- focus sessions
- tasks by category
- weekly completion trend

Later, the same dashboard concept can be repointed to real personal exports if useful.

## Solutions Considered

### Option A: Static Prompt Replay Through Hermes

**Approach**:
Run a fixed list of prompts through Hermes and let RuleShield observe.

**Pros**:

- easiest to implement
- cheapest to run
- deterministic

**Cons**:

- weak realism
- poor adaptive flow
- limited value for RuleShield tuning because prompts are too rigid

**Sacrifices**:

- realistic workflow shape
- rich rule-family coverage

### Option B: Full Synthetic Operator Simulator

**Approach**:
Build an adaptive test harness that inspects the workspace after every Hermes answer and dynamically generates the next human-like prompt.

**Pros**:

- highest realism
- stronger workflow continuity
- good future extensibility

**Cons**:

- much more complexity
- harder to keep deterministic
- higher run cost
- likely too large for V1

**Sacrifices**:

- simplicity
- speed to ship
- low cost

### Option C: Compact Scenario Graph Through Hermes

**Approach**:
Use a scripted-but-branchable scenario graph:

- ordered steps
- fallback prompts
- lightweight success heuristics
- small prompt budget

Hermes does real work inside the workspace, and RuleShield gets realistic traffic from that sequence.

**Pros**:

- best balance of realism and cost
- deterministic enough for repeated training
- much simpler than a full simulator
- directly useful for RuleShield traffic generation

**Cons**:

- less adaptive than a full operator simulator
- needs careful scenario authoring

**Sacrifices**:

- maximum realism
- open-ended exploration

## Tradeoffs Matrix

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Simplicity | Best | Worst | Good |
| Realism | Weak | Best | Good |
| Cost | Best | Worst | Good |
| Runtime | Best | Worst | Good |
| Determinism | Best | Weak | Good |
| RuleShield usefulness | Weak | Best | Best enough |
| Time to implement | Best | Worst | Good |

## Recommendation

### Recommended Approach: Option C - Compact Scenario Graph Through Hermes

This best matches the actual problem.

We want **RuleShield-relevant traffic**, not a perfect human simulator and not a toy replay list. Option C gives us realistic enough interactions to produce:

- shadow comparisons
- feedback entries
- confidence movement
- repeated prompt-family evidence

without turning the project into an expensive benchmark framework.

## Proposed V1 Architecture

### 1. Dedicated Run Workspace

Each run gets a fresh directory:

```text
test-runs/ruleshield-training/<run-id>/
```

Layout:

```text
test-runs/ruleshield-training/<run-id>/
  project/
  fixtures/
  runtime-home/
  reports/
    transcript.json
    ruleshield-summary.json
    ruleshield-summary.md
```

### 2. Hermes-as-Driver Model

Hermes is the worker that produces realistic agent traffic.

RuleShield is enabled in front of Hermes for the whole run:

- Hermes Python API sends prompts
- Hermes routes through RuleShield proxy
- RuleShield logs:
  - requests
  - shadow comparisons
  - feedback
  - rule events

The harness itself should not try to mimic RuleShield internals. It should only generate realistic use.

### 3. Isolation Model

We should assume prompt instructions alone are not enough.

V1 isolation should use:

1. `cwd = run_dir/project`
2. `HOME = run_dir/runtime-home`
3. `TMPDIR = run_dir/runtime-home/tmp`
4. Hermes flags:
   - `quiet_mode=True`
   - `skip_context_files=True`
   - `skip_memory=True`
   - low `max_iterations`
5. explicit system instruction in the scenario:
   - only read/write files inside the current project directory

Optional V2 hardening:

- subprocess-level sandbox
- path allowlist enforcement at the tool layer

### 4. Scenario Graph

Each scenario contains:

- metadata
- workspace seed template
- ordered steps
- fallback prompts
- lightweight validation hints

Example:

```json
{
  "id": "vibecoder_stats_dashboard",
  "max_prompts": 14,
  "steps": [
    {
      "id": "inspect",
      "prompt": "Inspect this project and propose a small dashboard worth building from the local data.",
      "fallback_prompt": "Keep it simple and only use files in this project."
    }
  ]
}
```

### 5. RuleShield-Oriented Reporting

The main output is not “did Hermes perform amazingly?”

The main output is:

- which RuleShield rules got exercised
- what shadow comparisons were produced
- where feedback loop pressure increased
- which prompt families are worth tuning

So the report should emphasize:

- prompt/response transcript
- RuleShield request counts by resolution type
- shadow comparison summary
- feedback summary
- confidence movement summary
- workspace diff summary

## First Scenario Design

### Scenario Name

`vibecoder_stats_dashboard`

### Scenario Goal

Generate realistic coding-assistant traffic for RuleShield by having Hermes build a small dashboard from seeded local files.

### Why This Scenario Works for RuleShield

It naturally creates:

- planning prompts
- file listing prompts
- read/explain prompts
- change/fix prompts
- status and follow-up prompts
- “show me what changed” style prompts

These are exactly the kinds of prompt families RuleShield currently needs to observe better.

### Seed Project

Keep V1 small and deterministic:

- static HTML
- one CSS file
- one JS file
- local JSON/CSV fixture data

No package install step in V1.

This keeps runtime and cost down.

### Suggested User-Relevant Dashboard

**Personal Work Session Dashboard**

Widgets:

- total focus minutes
- tasks completed this week
- breakdown by category
- busiest day
- optional simple “streak” card

This is still useful later, because the fixture structure can be swapped for real exported personal data.

### Scenario Phases

#### Phase 1: Orientation

Prompts:

- inspect the project
- explain the available data
- propose a simple dashboard plan

#### Phase 2: Build

Prompts:

- implement the dashboard
- connect the fixture data
- keep it simple and readable

#### Phase 3: Refine

Prompts:

- improve layout
- add one useful insight card
- fix one obvious issue

#### Phase 4: Explain

Prompts:

- summarize what changed
- explain remaining limitations

### Prompt Budget

Target budget:

- 10 to 16 prompts
- 1 short fallback at most per failed step
- no long pauses between prompts

This keeps the run short while still resembling a compact vibecoder session.

## Success Criteria

The V1 tool is successful when:

1. a run completes in roughly 5-15 minutes
2. Hermes cost stays low enough to run repeatedly
3. all workspace mutations remain inside the run directory
4. RuleShield receives meaningful, realistic traffic
5. the run produces:
   - shadow comparisons
   - feedback entries or rule-event movement when applicable
   - an actionable summary of what RuleShield learned

## Metrics to Capture

### Run Metrics

- run duration
- prompts sent
- steps completed
- fallback prompts used

### Hermes Cost Metrics

- tokens in/out if available
- estimated run cost
- average cost per prompt

### RuleShield Training Metrics

- total requests observed
- resolution types:
  - cache
  - rule
  - routed
  - passthrough
- shadow comparisons created
- average similarity
- per-rule comparison counts
- feedback rows created
- confidence deltas by rule

### Workspace Metrics

- files created
- files modified
- out-of-scope write count

## Implementation Plan

### Phase 1: Core Runner

1. Add a new module:
   - `ruleshield/prompt_training.py`
2. Add workspace creation helpers.
3. Add scenario schema and one built-in scenario.
4. Add one CLI command:
   - `python -m ruleshield.cli run-prompt-training`

### Phase 2: Hermes Driver

1. Add a thin Hermes runner wrapper around `AIAgent`.
2. Force low-cost defaults.
3. Route Hermes through RuleShield proxy.
4. Capture transcript data.

### Phase 3: Isolation

1. Dedicated cwd
2. Redirected home/tmp
3. Post-run path audit
4. Hard fail if the run escapes workspace boundaries

### Phase 4: RuleShield Summary

1. Query RuleShield APIs after the run:
   - `/api/stats`
   - `/api/requests`
   - `/api/shadow`
   - `/api/feedback`
   - `/api/rule-events`
2. Produce:
   - `ruleshield-summary.json`
   - `ruleshield-summary.md`

### Phase 5: Iteration Surface

1. Allow multiple scenario definitions later.
2. Keep V1 limited to one scenario and one compact report format.

## Recommended CLI Shape

```bash
python -m ruleshield.cli run-prompt-training \
  --scenario vibecoder_stats_dashboard \
  --model gpt-5.1-codex-mini \
  --max-prompts 14 \
  --output-dir test-runs/ruleshield-training
```

Optional flags:

- `--keep-run-dir`
- `--seed`
- `--timeout-minutes`
- `--max-iterations`
- `--report-only`

## Risks and Safeguards

### Risk: Hermes escapes the workspace

Mitigation:

- dedicated cwd
- redirected `HOME`
- redirected temp dirs
- post-run path audit
- explicit prompt constraint

### Risk: Tool is too synthetic to teach RuleShield anything useful

Mitigation:

- use scenario graph instead of flat replay
- include planning, build, refine, and explain phases
- let the project state evolve during the run

### Risk: Tool is too expensive to run often

Mitigation:

- small prompt budget
- cheap default model
- small seed project
- no package installs in V1

### Risk: We accidentally optimize for Hermes quality instead of RuleShield signal

Mitigation:

- make RuleShield metrics the primary report
- treat Hermes output quality as secondary
- measure success by RuleShield learning signal, not just finished UI

## Open Questions

- Should V1 allow terminal usage inside the project, or should it stay file-edit focused?
- Should the report include a recommended RuleShield tuning section automatically?
- Should V1 reset shadow/feedback windows before each run, or preserve rolling history?

## Recommended Answers

- Terminal usage:
  - allow it only inside the project directory, because realistic coding workflows often need it
- Recommended tuning:
  - yes, but rule-family-level only in V1
- Reset behavior:
  - support both, default to a fresh measurement window

## Summary

Build a compact RuleShield prompt training tool that uses Hermes as the traffic generator inside a sealed workspace and produces a short, realistic coding session around building a small stats dashboard.

That gives us:

- realistic RuleShield training traffic
- low runtime
- low cost
- repeatable runs
- clear shadow/feedback/confidence outputs

This is the smallest design that still solves the real problem.
