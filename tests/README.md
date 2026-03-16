# RuleShield Test Suite

This folder contains the story-first test gates.

## Why this structure

We test user workflows first, then implementation details.

The gate order is:

1. `commit` gate (fast, deterministic)
2. `core` gate (adds health-check, monitor-contract, and feedback-loop stories)
3. `full` gate (extended suites)

## Commands

```bash
# one-time: import keys into test-local store
bash tests/import_test_keys.sh

# then run suites
bash tests/run-commit-suite.sh
bash tests/run-core-suite.sh
bash tests/run-full-suite.sh
```

For browser-based full-story checks, install Lightpanda once:

```bash
mkdir -p tools
curl -L -o tools/lightpanda https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-macos
chmod +x tools/lightpanda
```

## Git hooks

Install once per clone:

```bash
bash tests/install-git-hooks.sh
```

This sets:
- pre-commit -> `tests/run-commit-suite.sh`
- pre-push -> `tests/run-core-suite.sh`

## Story contract

The source of truth is:
- `tests/story-matrix.md`

Before shipping a new feature, map it to a story in that matrix and ensure the mapped story test covers it.

## Standalone status page

The independent test status UI lives in:
- `tests/status/`

It is not connected to the app monitor. It only reads suite artifacts from:
- `tests/status/data/summary.json`
