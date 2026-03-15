# Cron Optimization for RuleShield Hermes

**Mode**: Deep / Hammock
**Date**: 2026-03-15
**Status**: Draft

## Problem Statement

We do not actually want to "replace cron jobs with rules."

The real problem is:

- recurring agent tasks often resend the same expensive orchestration prompt
- the prompt contains a large static workflow frame plus a much smaller dynamic payload
- tool setup, scheduling language, formatting instructions, and repeated context consume tokens on every run
- some scheduled tasks use the LLM for deterministic pre/post steps that do not need a model at all

This creates unnecessary cost, latency, and tool usage for recurring Hermes jobs.

Example:

```text
please check my mails every day at 8 am and then sort them by category and summarize every category and return with a formatted output
```

This single prompt mixes several concerns:

1. schedule definition
2. source fetch
3. categorization strategy
4. summarization
5. formatting
6. delivery

Only part of that belongs inside the LLM request.

## Success Criteria

The feature is successful if RuleShield can:

1. detect recurring scheduled-agent prompts that contain large static frames
2. classify which parts are deterministic and can be moved out of the LLM call
3. rewrite the execution plan so the LLM sees only the irreducible reasoning payload
4. reduce per-run tokens and tool usage for repeated tasks
5. do this without changing the user-visible output quality

## What We Are Actually Building

The correct mental model is:

**RuleShield as a cron workflow optimizer**

not:

**RuleShield as a general cron replacement engine**

The optimized flow should separate:

- orchestration
- deterministic data preparation
- minimal LLM reasoning
- deterministic output handling

## Facts

The current codebase already contains partial groundwork:

- recurring prompt analysis in [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)
  - `ruleshield analyze-crons`
- direct prompt promotion to a direct rule endpoint in [cli.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/cli.py)
  - `ruleshield promote-rule`
- direct response retrieval in [proxy.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/proxy.py)
  - `GET /api/rules/{rule_id}/response`
- MCP analysis support in [mcp_server.py](/Users/banse/codex/hermes/ruleshield-hermes/ruleshield/mcp_server.py)
  - `_analyze_crons(...)`
- a demo narrative for cron replacement in [test_cron_replacement.sh](/Users/banse/codex/hermes/ruleshield-hermes/demo/test_cron_replacement.sh)

The current engine is still mainly optimized for:

- repeated prompts
- direct response replacement
- shadow validation of candidate rules

It is not yet optimized for:

- structured scheduled workflows
- splitting one job into deterministic pre/post and minimal LLM core
- reusable task-specific execution plans

## Context

Hermes already supports library-style embedding through its Python API, which makes recurring-task optimization much more realistic than trying to force everything through plain text prompts.

Important implication:

- recurring task runners can call Hermes as code
- the runner can fetch data, normalize payload, and call Hermes only for the summarization/reasoning step
- RuleShield can sit above this flow as the optimizer that suggests or enforces the compact version

This means the feature should be designed as a bridge between:

- request-log analysis
- recurring job discovery
- prompt-template extraction
- deterministic execution wrappers
- compact Hermes calls

## Constraints

- KISS is important: the first version should not try to build a universal workflow engine
- backward compatibility matters: existing proxy behavior should continue to work
- cost reduction must be measurable from request logs
- the system must not silently break task semantics while optimizing prompts
- deterministic and non-deterministic stages must be clearly separated

## Unknowns

Resolved enough for planning:

- Hermes can be embedded as a Python library
- RuleShield already has cron-analysis and direct-response concepts

Still open for implementation:

- exact stable interface for "optimized scheduled task" definitions
- how far categorization should be deterministic vs LLM-driven
- whether to store optimized cron specs as rules, templates, or a new artifact type

## Core Insight

A recurring job usually contains three kinds of work:

### 1. Deterministic control work

Examples:

- schedule handling
- fetching emails
- reading files
- selecting the output format
- sending the result somewhere

This should be code, not prompt text.

### 2. Deterministic preprocessing

Examples:

- basic normalization
- stripping signatures
- grouping by sender
- attaching labels
- splitting large payloads

This may be code or a template stage.

### 3. Irreducible reasoning work

Examples:

- summarizing a set of emails
- generating category summaries
- writing a human-readable digest

This is what should remain inside Hermes.

That means the optimization problem is mostly:

**move stages 1 and 2 out of the prompt**

and then:

**minimize the prompt for stage 3**

## Optimization Flow

The cron optimizer should have its own explicit optimization flow.

This flow mirrors the general RuleShield philosophy:

- observe first
- optimize second
- validate in shadow
- activate only when proven

### End-to-end flow

```text
recurring traffic
  -> recurring workflow detection
  -> workflow decomposition
  -> cron optimization profile draft
  -> cost / latency / tool-use estimate
  -> shadow validation against original execution
  -> optimization confidence score
  -> explicit activation
```

### Step 1: Detect recurring jobs

Input:

- request log
- repeated prompt hashes
- repeated prompt families
- prompts containing schedule-like or workflow-like language

Output:

- recurring job candidates

The goal here is not to decide correctness yet. It is simply to surface which jobs are worth examining.

### Step 2: Decompose the workflow

For each recurring candidate, split the task into:

- deterministic control steps
- deterministic preprocessing
- minimal LLM reasoning task
- deterministic postprocessing

Output:

- explicit workflow decomposition

This is the critical stage because most of the cost savings come from removing non-reasoning work from the prompt.

### Step 3: Build a draft optimization profile

Convert the decomposition into a `Cron Optimization Profile`.

Output:

- reusable profile artifact
- source prompt reference
- compact prompt template
- deterministic execution metadata

At this stage the profile is still a draft. It should not replace the original job yet.

### Step 4: Estimate savings

Compare the original workflow prompt to the compact execution profile.

Estimate:

- token reduction
- expected cost reduction
- reduced tool calls
- latency improvement

Output:

- optimization estimate

This is the product-facing justification for the optimization.

### Step 5: Shadow-validate the optimized flow

Run both versions in parallel:

- original full execution
- optimized compact execution

Compare:

- output similarity
- output structure
- missing information
- formatting stability

Output:

- validation evidence

This is analogous to rule shadow mode, but at workflow level rather than single response level.

### Step 6: Score optimization confidence

From the validation evidence, compute an optimization confidence score.

This should reflect:

- output fidelity
- structural correctness
- consistency
- operator acceptance

Output:

- optimization confidence

This is separate from ordinary rule confidence.

### Step 7: Activate

Once the optimized flow is proven, allow the cron job to switch to the optimized path.

Output:

- active optimized cron profile

Activation should remain explicit in early versions so operators can review what is changing.

### Operating principle

Rules optimize repeated static responses.

Cron optimization profiles optimize recurring workflows.

That distinction is important because it keeps the engine honest about what can safely be reduced to a rule and what still needs a compact LLM call.

## Solutions Considered

## Option A: Pure Rule Replacement

### Approach

Use `analyze-crons` to find repeated prompts and convert them directly into rules or direct response endpoints.

### Pros

- simple
- fits current RuleShield shape
- cheap to implement

### Cons

- only works when the output is nearly static
- fails for jobs where the payload changes each run
- not suitable for tasks like "summarize today's emails"

### Sacrifice

This optimizes only the smallest subset of recurring tasks.

## Option B: Template-Only Optimization

### Approach

Detect recurring prompts, split out a static template, and only send the variable content to Hermes.

### Pros

- matches the actual token-saving problem
- works for many recurring jobs
- fits the existing template-optimizer direction

### Cons

- still leaves orchestration logic implicit
- deterministic steps remain inside the conceptual prompt flow
- does not reduce tool usage as much as possible

### Sacrifice

This improves token cost but does not fully solve workflow inefficiency.

## Option C: Workflow Decomposition Profile

### Approach

Introduce a new artifact that describes a recurring job as:

- trigger
- fetcher
- preprocessing steps
- minimal LLM task
- output formatter
- delivery target

RuleShield then analyzes recurring prompts and suggests this decomposition. Hermes is called only for the minimal reasoning stage.

### Pros

- addresses both token cost and unnecessary tool usage
- fits real scheduled agents
- makes optimization explicit and measurable
- can reuse Hermes Python library effectively

### Cons

- larger feature surface
- requires a new data model
- needs careful guardrails to avoid overpromising automation

### Sacrifice

Higher implementation complexity than simple rule promotion.

## Recommendation

Choose **Option C**, but implement it in phased form with a KISS first slice.

Reason:

- Option A is too narrow
- Option B is useful but incomplete
- Option C is the first design that actually matches the real user problem

However, the first implementation should be intentionally constrained:

- optimize recurring tasks that have a clear static frame
- generate a compact execution profile
- keep the actual execution mostly explicit and inspectable
- do not attempt fully autonomous task synthesis

## Proposed Feature Model

Introduce a new concept:

**Cron Optimization Profile**

This is not a normal rule.

It is a structured artifact representing a recurring workflow that can be optimized.

Example conceptual shape:

```json
{
  "id": "mail_digest_daily",
  "name": "Daily Mail Digest",
  "source_prompt": "please check my mails every day at 8 am ...",
  "schedule": {
    "type": "daily",
    "time": "08:00"
  },
  "fetch": {
    "type": "mailbox",
    "account": "primary"
  },
  "preprocess": [
    "strip_signatures",
    "group_by_category"
  ],
  "llm_task": {
    "prompt_template": "Summarize these categorized emails in the following format: ...",
    "input_binding": "categorized_mail_batch"
  },
  "postprocess": {
    "format": "markdown_digest",
    "deliver_to": "stdout"
  },
  "estimated_savings": {
    "token_reduction_pct": 62.0,
    "tool_reduction_pct": 50.0
  }
}
```

## Architecture

## Layer 1: Detection

Use request-log analysis to detect recurring prompts that are cron-like.

Signal candidates:

- repeated prompt hash or repeated prompt family
- presence of scheduling language
- recurring time-related framing
- repeated action structure with variable payload

Potential implementation home:

- extend `analyze-crons`
- add pattern scoring for "workflow-like recurring prompts"

## Layer 2: Decomposition

Take a recurring prompt and split it into:

- static orchestration frame
- deterministic pre/post steps
- minimal reasoning task
- variable runtime payload

This can initially be heuristic plus optional human review.

The output is a `Cron Optimization Profile`, not an auto-executed job.

## Layer 3: Execution Adapter

For accepted profiles, provide a Python execution adapter that:

1. fetches the real payload
2. runs deterministic preprocessing
3. invokes Hermes with the compact LLM prompt
4. runs deterministic post-formatting

This is where Hermes Python library integration matters.

## Layer 4: Optional Direct Response / Rule Use

If a stage becomes fully deterministic, it can still be:

- turned into a direct rule
- promoted to `/api/rules/{rule_id}/response`

So rules remain useful, but they are only one tool in the larger workflow optimizer.

## Relationship to Existing Features

### `analyze-crons`

Should evolve from:

- repeated prompt counter

into:

- recurring workflow detector

### `promote-rule`

Should remain for static repeated prompts, but not be the main path for workflow optimization.

### template optimizer

Becomes a natural engine for extracting the compact LLM core prompt.

### shadow mode

Can be reused to compare:

- original full prompt execution
- optimized compact execution

This is a very important validation path.

## Validation Strategy

The safest way to validate this feature is not to switch execution immediately.

Instead:

### Phase 1 validation

Run in analysis-only mode:

- suggest cron optimization profiles
- estimate token savings
- do not alter execution

### Phase 2 validation

Run original and optimized forms in parallel:

- original full prompt
- compact optimized prompt

Compare:

- output similarity
- structure completeness
- failure rate
- cost and latency

This is conceptually similar to shadow mode for rules.

### Phase 3 activation

Allow the optimized profile to become the default executor once the compact flow proves stable.

## Feedback Loop Design for Cron Optimization

The existing feedback loop operates on rule confidence.

For cron optimization, the object being evaluated is slightly different:

- not just "did this rule text match?"
- but "did this optimized workflow preserve task quality?"

So we need a second feedback object:

**optimization confidence**

It should track:

- output similarity to original execution
- output structure correctness
- operator acceptance
- cost savings achieved

Suggested signals:

- `accepted`
  - optimized output acceptable
- `rejected`
  - optimized output lost important structure or meaning
- `partial`
  - useful, but missing detail or formatting fidelity

This should not replace rule confidence. It should live beside it.

## API / CLI Proposal

## CLI

New commands:

```bash
ruleshield analyze-crons --structured
ruleshield suggest-cron-profile <prompt-hash-or-text>
ruleshield list-cron-profiles
ruleshield run-cron-shadow <profile-id>
ruleshield activate-cron-profile <profile-id>
```

Minimal first slice:

- `analyze-crons --structured`
- `suggest-cron-profile <prompt>`

## API

Potential endpoints:

```text
GET  /api/cron-profiles
POST /api/cron-profiles/suggest
POST /api/cron-profiles/{id}/shadow-run
POST /api/cron-profiles/{id}/activate
```

## Python Integration

Potential helper module:

```python
from ruleshield.cron_optimizer import OptimizedRecurringTask
```

Conceptual usage:

```python
task = OptimizedRecurringTask.load("mail_digest_daily")
result = task.run()
```

Internally this would:

- fetch source data
- preprocess
- call Hermes with compact prompt
- format output

## Tradeoffs

## Simplicity vs capability

- A simple direct-rule approach is easier
- but it misses the actual value for dynamic recurring jobs

## Explicitness vs automation

- full automation sounds powerful
- but explicit profiles are safer and easier to debug

## Fast implementation vs durable design

- quick wins can come from improving `analyze-crons`
- but the durable version needs a new workflow artifact, not just more rules

## Recommendation on this axis

Prefer:

- explicit profile artifacts
- human-reviewable decomposition
- shadow validation before activation

over:

- fully automatic replacement

## Risks

### 1. Over-optimization

The system may remove prompt context that actually matters.

Mitigation:

- shadow-compare original vs optimized outputs
- require review before activation

### 2. False determinism

A preprocessing step may look deterministic but actually requires reasoning.

Mitigation:

- keep preprocessing vocabulary small in v1
- only support well-bounded transforms at first

### 3. Workflow explosion

Trying to support every cron-like job too early will make the system vague.

Mitigation:

- target a narrow set of recurring job families first

### 4. Hidden integration complexity

Real mailbox or data-source integration may be much harder than prompt analysis itself.

Mitigation:

- spec the optimizer independently from connectors
- first support local or already-fetched payloads

## First Version Scope

The first real version should support:

1. detection of recurring workflow-like prompts
2. extraction of static frame vs dynamic payload
3. generation of an optimization profile draft
4. estimated token savings
5. optional shadow comparison of original vs optimized prompt form

It should not yet try to:

- own all schedulers
- fetch every external source
- replace arbitrary toolchains automatically

## Phased Implementation Plan

## Phase 1: Structured Analysis

Extend `analyze-crons` to identify:

- repeated prompts
- repeated prompt families
- static-frame-heavy tasks
- prompts likely to benefit from workflow decomposition

Deliverables:

- structured CLI output
- MCP support
- savings estimate

## Phase 2: Cron Profile Drafts

Add a new profile artifact type.

Deliverables:

- profile schema
- `suggest-cron-profile`
- file storage for draft profiles

## Phase 3: Hermes Compact Executor

Introduce a Python execution path that runs a profile through:

- fetch
- preprocess
- compact Hermes call
- postprocess

Deliverables:

- helper runtime module
- example mail-digest profile

## Phase 4: Shadow Validation

Compare original full prompt execution vs optimized compact execution.

Deliverables:

- comparison logs
- optimization confidence score
- operator review flow

## Phase 5: Activation

Allow explicit activation of proven profiles.

Deliverables:

- activation command/API
- cost reporting
- rollback path

## Open Questions

1. Should cron profiles live under `~/.ruleshield/rules/` or in a separate `profiles/` directory?
2. Should categorization in v1 be deterministic, LLM-based, or configurable?
3. Should optimized cron execution live inside the proxy process or as a separate helper runtime?
4. How much of the output contract should be schema-driven versus plain prompt text?

## Recommendation Summary

Build this as a **Cron Optimization Profile system** layered on top of existing RuleShield primitives.

Do not frame the first implementation as:

- "the rule engine replaces cron"

Frame it as:

- "RuleShield detects recurring workflow prompts, extracts the static frame, and validates a cheaper compact execution path"

That is the smallest architecture that actually solves the user's cost problem without pretending that all scheduled tasks can be collapsed into static rules.
