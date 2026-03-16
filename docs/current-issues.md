# Current Issues

This file captures the current known issues and findings from the hackathon push,
especially around installability, test reliability, and the training monitor.

## 1. Gateway lifecycle is still unstable under training load

Status: open

What we observed:
- `demo/gateway_ctl.sh restart` can report a healthy startup and a live PID.
- `demo/test_training_health_check.sh` can begin successfully, including:
  - gateway health check
  - shadow mode toggle
  - prompt training startup
- during the training run, the gateway can still disappear.

Symptoms:
- training `PROBE` values become `error:ConnectError`
- follow-up `curl` calls to `/health` fail
- the training script can still complete because Hermes fallback continues, but live proxy telemetry is no longer reliable

Impact:
- monitor polling becomes unreliable
- live RuleShield metrics during a run are incomplete or misleading
- reviewer confidence suffers because the recommended demo path is not yet fully stable under load

## 2. RuleShield Live monitor still underreports shadow comparisons

Status: open

What we observed:
- a finished health-check summary can contain valid shadow data, for example:
  - `shadow_snapshot.enabled: true`
  - `shadow_snapshot.total_comparisons: 56`
  - multiple `by_rule` entries like `status_check`, `file_listing_request`, `greeting_simple`, `goodbye`
- yet the `RuleShield Live` panel can still show:
  - `Would Trigger (Shadow): 0`
  - `Triggered Rules: 0`

Likely cause:
- the run-specific monitor logic for single-summary runs still does not map the available `shadow_snapshot` data cleanly into the displayed counters

Impact:
- shadow mode appears inactive or ineffective even when comparisons were actually recorded
- weakens the main product story in the UI

## 3. Health-check scenario is poor at visibly demonstrating successful rules

Status: open

What we observed:
- `ruleshield/training_configs/health_check_baseline.yaml` is made of prompts like:
  - `status`
  - `list files in this project`
  - `read README.md and summarize it briefly`
  - `show me what changed`
  - `explain what happened`
  - `run ls in this project and confirm when done`
- these are useful for baseline validation, but not ideal for visibly showing rule hits or shadow hits in the monitor

Impact:
- even when the script is functioning, the UI payoff is weak
- for demos and reviewer checks, a smaller rule-triggering scenario would be better

Recommendation:
- add a tiny dedicated demo/training script with obvious prompts such as greetings, acknowledgments, and goodbyes

## 4. Arcee/OpenRouter path is still not reliable enough as a primary demo path

Status: open

What we observed:
- `test_training_health_check.openrouter_arcee_trinity_free.sh` often failed early
- `test_training_hermes_user_suite.openrouter_arcee_trinity_free.sh` progressed further, but later failed in the complex phase with timeout behavior
- Arcee runs can still produce useful RuleShield stats, but are not stable enough for the primary install/demo path

Impact:
- OpenAI/Hermes remains the best current demo path
- OpenRouter/Arcee should be treated as secondary/experimental for now

## 5. Training monitor model/profile selection had regressions

Status: partly fixed

What was fixed:
- OpenAI profiles now show generic shell scripts again
- OpenRouter profiles still show only their profile-specific script variants
- `Alle anzeigen` no longer gets silently invalidated
- changing model no longer auto-selects an old run and carry stale RuleShield numbers into the new selection
- empty recent rule events panel is now hidden entirely

Remaining caution:
- monitor correctness still depends on stable run telemetry from the gateway

## 6. Test/demo scripts were previously split across hardcoded port assumptions

Status: fixed

What was fixed:
- the normal installation path now uses port `8347`
- test/demo scripts, gateway control, and training CLI now resolve the proxy port from the same config source:
  - `ruleshield.config.load_settings().port`
- `~/.ruleshield/config.yaml` is now the central source of truth for the configured port

Why this matters:
- the port can now be changed once in config and the scripts will follow it
- this avoids the earlier conflict between “normal install” and “local training/test stack”

## 7. `_helpers.sh` previously polluted script model defaults

Status: fixed

What happened:
- `_helpers.sh` defined a global `MODEL` fallback (`claude-sonnet-4-6`)
- scripts sourcing it could unexpectedly inherit the wrong model

What was fixed:
- `_helpers.sh` now only uses a local model variable inside `send()`
- training scripts keep their own explicit model defaults

## 8. Public repo secret exposure check

Status: checked, no leak found

What we verified:
- no real API keys were found in tracked files
- no real OAuth tokens were found in tracked files
- no `.env` or `auth.json` files were committed
- matches in the repo are placeholders, environment variable names, workflow inputs, or local-path documentation references

Residual caution:
- local runtime still depends on user-owned files such as `~/.codex/auth.json`, `~/.hermes/.env`, and `~/.hermes/config.yaml`
- this is expected, but should remain clearly documented

## 9. Hermes integration cleanup / restore behavior

Status: acceptable, but should be documented more clearly

What exists:
- `ruleshield init --hermes` patches `~/.hermes/config.yaml`
- previous `base_url` is backed up in `~/.ruleshield/hermes_original_url.txt`
- `ruleshield restore-hermes` restores the old Hermes `base_url`

Remaining concern:
- users can still become confused if they alternate between test and install flows without realizing Hermes config is global

Recommendation:
- keep emphasizing:
  - one central config file
  - one clean install port
  - `ruleshield restore-hermes` for rollback

## 10. SmartRouter observability needs stronger failure surfacing

Status: open (todo)

What we observed:
- in test/monitor flows, SmartRouter can rewrite a free OpenRouter model to a default OpenAI model
- this can produce downstream auth failures that look unrelated unless route decisions are visible
- noisy gateway INFO lines can hide the real failure line in status summaries

Why this matters:
- routing mistakes are high-impact and should be obvious immediately
- monitor/operator UX should show route decision + upstream target in a compact, explicit way

Todo:
- add first-class SmartRouter diagnostics (decision reason, source model, target model, upstream provider/url)
- expose these diagnostics clearly in monitor/test run outputs and UI status summaries
- keep current detailed logs as fallback for deep debugging

## 11. Auth source (OAuth vs API key) should be user-configurable

Status: open (todo)

What we observed:
- monitor-driven training and health-check runs currently infer auth from local user files/environment
- in practice, this can pull from `~/.codex/auth.json` (OAuth) or `.env`-based API keys depending on what is present
- source selection is implicit, not explicitly selectable in UI/config for the test flow

Why this matters:
- users and reviewers should be able to choose the auth path intentionally
- explicit auth mode selection reduces confusion and makes test runs reproducible

Todo:
- add a single config-driven auth mode selector for test/monitor flows (OAuth / API key / auto)
- surface the active auth source clearly in monitor UI and run logs
- keep secure handling (no secrets in repo; no secret values in logs)

## 12. Expose `router_enabled` in Config page UI

Status: open (todo)

What we observed:
- `router_enabled` is available via runtime config API, but not clearly controllable from the Config page workflow used during demos/tests

Why this matters:
- model-routing can change provider/model unexpectedly in test/demo flows
- operators need a fast UI toggle to freeze routing behavior when validating specific model paths

Todo:
- add a visible `router_enabled` toggle in the Config page
- show current value and apply changes via `/api/runtime-config`
- include short helper text explaining impact on routing and reproducibility

## 13. Align all test scripts with `test_training_health_check.openrouter_arcee_trinity_free.sh`

Status: open (todo)

What we observed:
- `test_training_health_check.openrouter_arcee_trinity_free.sh` now has stronger preflight diagnostics,
  runtime-config checks, and explicit router handling for OpenRouter free-model validation
- other test scripts still use older logging/guard patterns and are less transparent on failure

Why this matters:
- inconsistent diagnostics slows down debugging under deadline pressure
- harmonized script behavior makes monitor logs and status page interpretation predictable

Todo:
- port the same preflight/diagnostic logging style to the other training/test scripts
- standardize runtime-config checks and explicit failure messages across scripts
- ensure every script emits clear step boundaries and root-cause-first error output

## 14. Validate and publish the intended pip install path

Status: open (todo)

What we observed:
- direct install commands shown in UI/docs can drift from what is actually available on package indexes
- a recent isolated check showed no matching distribution for `ruleshield` and `ruleshield-hermes` from pip
- local source install (`pip install -e .`) works reliably for now

Why this matters:
- install commands in marketing/docs must be executable as-is
- broken pip instructions reduce reviewer trust and slow first-time setup

Todo:
- verify which package name should be published (`ruleshield` vs `ruleshield-hermes`)
- check PyPI availability and version visibility before documenting a PyPI command
- keep UI/docs on `pip install -e .` until PyPI install is confirmed end-to-end

## Suggested next priorities

1. Fix gateway stability during training runs.
2. Fix `RuleShield Live` shadow metrics for single-summary runs.
3. Add one tiny rule-triggering demo/training script for obvious UI feedback.
4. Tighten normal-user install docs around the clean `8347` path.
