# Hermes-First Training Scenarios (RuleShield)

This document summarizes how the new Hermes-first training scenarios were chosen.
The goal is to reflect common real user behavior first, then maximize RuleShield
learning and cost-saving opportunities.

## What We Optimized For

- Hermes users running repeated assistant workflows (status, plan, summarize, refine).
- Non-coding usage patterns (communication, prioritization, operations notes).
- Repeated prompt families that are good candidates for rule interception.
- Low runtime/token cost for all scenarios.
- Short/medium/complex means rule-training breadth, not harder prompts.

## Research Snapshot (high-level)

We grounded scenario design in broad LLM usage patterns reported across:

- OpenAI + NBER task-level analysis of real ChatGPT usage:
  [Which Economic Tasks are Performed with AI?](https://openai.com/index/which-economic-tasks-are-performed-with-ai/)
  and [NBER Working Paper 33800](https://www.nber.org/papers/w33800)
- Anthropic Economic Index (work/task mix across assistant use):
  [The Anthropic Economic Index](https://www.anthropic.com/news/the-anthropic-economic-index)
- McKinsey State of AI (enterprise functional adoption patterns):
  [The State of AI](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai)

Common cross-source signals used for scenario design:

- Writing/summarization/rewrite loops are extremely frequent.
- Planning/prioritization and status-style prompts are common daily behavior.
- Multi-audience communication (internal vs external wording) is a repeated pattern.
- Structured outputs (checklists, templates, runbooks) appear often in practical usage.

## New Scenarios

### 1) Short: Daily Assistant

- Config: `ruleshield/training_configs/hermes_user_short.yaml`
- Focus: low-cost baseline with a small set of core intents.
- Why useful: trains only a few frequent rule families quickly.

### 2) Medium: Knowledge Worker

- Config: `ruleshield/training_configs/hermes_user_medium.yaml`
- Focus: same low-cost prompt style, but wider intent coverage.
- Why useful: trains more rule families (capabilities, run-confirm, explain, repeat, confirmation).

### 3) Complex: Ops + Communication

- Config: `ruleshield/training_configs/hermes_user_complex.yaml`
- Focus: still low-cost prompts, but broadest intent set plus paraphrased repeats.
- Why useful: maximizes rule-training signal across many common Hermes intents.

## Arcee-Specific Variants

For OpenRouter Arcee test runs we keep separate scenario configs:

- `ruleshield/training_configs/hermes_user_arcee_short.yaml`
- `ruleshield/training_configs/hermes_user_arcee_medium.yaml`
- `ruleshield/training_configs/hermes_user_arcee_complex.yaml`

This allows model-specific tuning without changing non-Arcee scenarios.

## How to Run

Use the new suite script:

```bash
bash demo/test_training_hermes_user_suite.sh
```

This runs:

1. baseline health-check
2. short Hermes scenario
3. medium Hermes scenario
4. complex Hermes scenario

and stores artifacts under:

`test-runs/training-hermes-users/<timestamp>/`

## Monitor Semantics (KISS)

In `/test-monitor`, `RuleShield Live` is run-scoped:

- values belong to the selected run only
- no global fallback values are merged into that panel
- use `Alle anzeigen` to disable model-profile script filtering
