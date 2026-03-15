# Cron Optimizer User Guide

This guide is for operators who want to use the RuleShield Cron Optimizer day to day.

## What the Cron Optimizer does

The Cron Optimizer helps you reduce repeated prompt cost for recurring workflows.

It works in stages:

1. detect recurring workflow prompts
2. create a draft cron profile
3. validate draft behavior in shadow
4. activate only when quality is good enough
5. run the active profile with dynamic payloads

## Prerequisites

- RuleShield proxy running on `http://127.0.0.1:8337`
- Hermes routed through RuleShield
- request history in `request_log` (so recurring workflows can be detected)

## Main operator surfaces

- Dashboard board: `/cron-lab`
- Profile detail page: `/cron-lab/<profile_id>`
- API:
  - `GET /api/cron-profiles`
  - `GET /api/cron-profiles/{id}`
  - `POST /api/cron-profiles/{id}/shadow-run`
  - `POST /api/cron-profiles/{id}/activate`
  - `POST /api/cron-profiles/{id}/execute`

## Recommended workflow

### 1) Create or inspect a draft profile

Use the existing analysis and draft flow to get a candidate profile from repeated prompts.

In `cron-lab`:

- open the draft
- adjust compact prompt and model if needed
- keep the payload-oriented shape (fixed instructions in profile, variable data in payload)

### 2) Run shadow validation from payload

Use `Run Shadow` in the draft panel.

What to check:

- `Similarity` should trend up
- `Confidence` should trend up
- `Validation Diff` should show acceptable semantic drift

### 3) Activate with guardrails

If guardrails pass, activate normally.

If blocked:

- inspect `Validation History`
- tune compact prompt
- rerun shadow
- force activate only when you accept the tradeoff

### 4) Execute active profile

For runtime calls, send only dynamic payload:

```bash
curl -s -X POST http://127.0.0.1:8337/api/cron-profiles/<profile_id>/execute \
  -H 'content-type: application/json' \
  -d '{"payload_text":"<dynamic content>"}'
```

Then monitor:

- `Execution History`
- `Last Executed`
- output quality in the detail page

## How to read key metrics

- `Shadow Runs`: amount of evidence collected for draft quality
- `Optimization Confidence`: aggregate readiness score for activation
- `Similarity`: closeness between original and optimized outputs
- `Length Ratio`: output size drift indicator (too small may mean missing info)
- `Last Validated`: freshness of your validation signal
- `Last Executed`: whether active profile is actually in use

## Lifecycle actions

Use these to keep the workspace clean:

- `Duplicate`: branch a profile for experiments
- `Archive`: retire without deleting evidence
- `Restore`: bring archived profile back to draft
- `Delete`: remove profile permanently (usually only after archive)

## Automation handoff (active profiles)

For active profiles, use the automation suggestion from profile detail.

It provides:

- suggested schedule (`rrule`)
- a compact task prompt for Codex automation
- a ready `::automation-update{mode="suggested create" ...}` directive

## Troubleshooting

### Draft confidence does not improve

- payloads are too different from original workflow
- compact prompt too short or too generic
- expected output format mismatch

Actions:

- tighten compact prompt
- run more representative payload samples
- inspect `Validation Diff` per run, not only averages

### Active profile output quality dropped

- duplicate profile
- tune draft copy
- shadow validate again
- archive old active profile when new one is stable

### No recurring workflows detected

- not enough repeated prompts yet
- min occurrence threshold too high
- prompt variants too inconsistent

## Best practices

- keep deterministic steps outside LLM prompts
- keep payloads normalized before execute calls
- avoid force activation without at least a few strong shadow runs
- use JSON/CSV export for audit trails during tuning windows

## Related docs

- `docs/cron-runtime-guide.md`
- `docs/cron-optimization-spec.md`
- `docs/cron-optimization-implementation-plan.md`
