# Test Framework Base (Reusable)

This folder contains the reusable, app-independent test framework pieces.

## Goals

- Keep test status storage independent from the main application.
- Use relative test script paths so this can be copied to other repos.
- Separate reusable test infrastructure from app-specific story scripts.

## Files

- `suite_runner.sh`
  - Shell helpers to run test cases, write logs, and record per-case status.
- `status_store.py`
  - JSON status store for runs, per-test last status, and summary generation.

## Reuse in another application

1. Copy `tests/framework/`.
2. Copy `tests/status/` (page + catalog).
3. Add app-specific test scripts under `tests/stories/` or another local folder.
4. Register those scripts in `tests/status/catalog.json`.
5. Build suite entrypoints that call `suite_case` from `suite_runner.sh`.
