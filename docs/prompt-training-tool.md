# RuleShield Prompt Training Tool

The prompt training tool generates realistic Hermes traffic for **RuleShield**.

It is not a Hermes benchmark. Hermes is the worker. RuleShield is the system
being exercised, observed, and improved.

## Test Monitor (Current Behavior)

The `/test-monitor` page is now intentionally run-scoped (KISS).

- `RuleShield Live` shows only data of the currently selected run.
- No global `/api/shadow` or `/api/rules` fallback is shown in that panel.
- If a selected run has no RuleShield run data yet, values remain empty/zero.
- Polling is every ~2 seconds, so values can lag slightly during active runs.

### Model/Profile Script Filter

- The script list is filtered by exact script path suffix for the selected model profile.
- No profile fallback scripts are auto-included.
- Use `Alle anzeigen` in the profile selector to show the full script list.

### Single-Summary Run Safety

For runs that only produce one `ruleshield-summary.json` file, run deltas do not
use global snapshot totals anymore. This prevents global leakage in run metrics
(for example `would_trigger_shadow` jumping to historical totals).

## Purpose

Use the tool when you want a short, repeatable training run that:

- drives realistic coding-assistant prompts through Hermes
- keeps runtime and token cost low
- runs inside a dedicated workspace
- produces a RuleShield-focused report

## First Built-In Scenario

`vibecoder_stats_dashboard`

This scenario simulates a short vibecoder session that builds a tiny static
dashboard from local fixture data.

Why it is useful for RuleShield:

- it generates planning prompts
- it generates file inspection prompts
- it generates explain/change/fix prompts
- it produces realistic follow-up traffic for shadow mode

## Hermes-First Scenario Set

For broader non-coding behavior, we also provide Hermes-first YAML scenarios:

- `ruleshield/training_configs/hermes_user_short.yaml`
- `ruleshield/training_configs/hermes_user_medium.yaml`
- `ruleshield/training_configs/hermes_user_complex.yaml`

Run all three (plus baseline health check) with:

```bash
bash demo/test_training_hermes_user_suite.sh
```

## CLI

```bash
ruleshield run-prompt-training \
  --scenario vibecoder_stats_dashboard \
  --model gpt-5.1-codex-mini \
  --max-prompts 12 \
  --output-dir test-runs/ruleshield-training

# Reusable initial health check baseline
ruleshield run-prompt-training \
  --scenario-config ruleshield/training_configs/health_check_baseline.yaml \
  --model gpt-4.1-mini \
  --max-iterations 2 \
  --output-dir test-runs/ruleshield-training
```

The health-check baseline config is versioned in:

- `ruleshield/training_configs/health_check_baseline.yaml`

Use this as the first run in future test workflows to confirm proxy traffic and
baseline RuleShield telemetry before running longer scenarios.

## Preconditions

1. RuleShield proxy should be running.
2. Shadow mode should be enabled if you want comparison data.
3. Hermes Python API must be importable in the current Python environment.

If Hermes is installed under a different import path, set:

```bash
export RULESHIELD_HERMES_AGENT_IMPORT=run_agent:AIAgent
```

or:

```bash
export RULESHIELD_HERMES_AGENT_IMPORT=hermes:AIAgent
```

## Run Output

Each run creates a fresh directory:

```text
test-runs/ruleshield-training/<run-id>/
```

Contents:

- `project/` isolated dashboard seed project
- `runtime-home/` redirected runtime home directory
- `reports/transcript.json`
- `reports/ruleshield-summary.json`
- `reports/ruleshield-summary.md`

## Isolation Model

The V1 isolation model is intentionally simple:

- current working directory is the run project
- `HOME` is redirected to `runtime-home/`
- `TMPDIR` is redirected to `runtime-home/tmp`
- Hermes is instructed to use only the current project files

This is good enough for realistic low-cost training runs, but it is not yet a
hard sandbox.

## What The Report Emphasizes

The summary is centered on RuleShield signals:

- recent request breakdown
- shadow mode totals and similarity
- feedback and confidence movement
- workspace changes inside the run directory

## Current V1 Boundary

The tool stops with a clear error if Hermes Python API is not importable in the
active environment. It still writes the run workspace and report artifacts so
you can inspect the attempted setup.
