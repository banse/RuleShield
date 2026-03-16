# Cron Optimizer Quickstart (5 Minutes)

This is the fastest path to run the Cron Optimizer end to end.

## 1) Start RuleShield

```bash
ruleshield start
```

Expected:

- proxy is reachable on `http://127.0.0.1:8347`
- dashboard is reachable on your local dashboard port

## 2) Open Cron Lab

Open:

- `http://127.0.0.1:5174/cron-lab`

If your dashboard uses the default Svelte port, use:

- `http://127.0.0.1:5173/cron-lab`

## 3) Pick or create a draft profile

In `Cron Lab`:

- choose a draft profile from the Lifecycle Board
- open profile detail
- verify compact prompt is reasonable for your recurring workflow

## 4) Run one shadow validation

In the draft panel:

- paste a realistic payload into the payload box
- click `Run Shadow`

Then check:

- `Similarity` and `Confidence` in Validation
- `Validation Diff` to see original vs optimized output

## 5) Activate when ready

When validation looks good:

- click `Activate`

If guardrails block activation:

- tune compact prompt
- run shadow again
- only use force activate if you accept risk

## 6) Execute active profile

For active profiles, run with payload:

```bash
curl -s -X POST http://127.0.0.1:8347/api/cron-profiles/<profile_id>/execute \
  -H 'content-type: application/json' \
  -d '{"payload_text":"<dynamic payload>"}'
```

Or use `Run` directly in `Cron Lab`.

## 7) Monitor and iterate

Watch:

- `Last Validated`
- `Last Executed`
- `Execution History`
- `Validation History`

Use lifecycle actions as needed:

- `Duplicate` for experiments
- `Archive` to retire
- `Restore` to bring back archived profiles

## Common first issues

- No profiles found:
  - not enough recurring traffic yet
- Low similarity:
  - compact prompt too generic or payload too noisy
- Output too short:
  - expand compact prompt output requirements
