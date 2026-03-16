# Standalone Test Status Page

This page is independent from the app monitor and only reads test-suite status files.

## Open locally

From repo root:

```bash
python3 -m http.server 8080
```

Then open:

`http://127.0.0.1:8080/tests/status/`

Shortcut:

```bash
bash tests/status/open.sh
```

## Data flow

- `tests/run-*.sh` suites call the reusable framework in `tests/framework/`.
- Framework writes:
  - `tests/status/data/runs/*.json`
  - `tests/status/data/tests/*.json`
  - `tests/status/data/summary.json`
- This page reads `tests/status/data/summary.json` and renders:
  - test name
  - relative script path
  - group
  - last run timestamp
  - status
  - last failed error message
