# RuleShield Optimizer Memory

## Session Log
<!-- Hermes will append session summaries here -->

### 2026-03-15 - Shadow/Test-Monitor Stabilization Snapshot
- Shadow mode flow verified end-to-end with live comparisons logged in `/api/shadow`.
- Fixed OpenRouter routing path in RuleShield proxy for OpenRouter-style models (`*:free`, `provider/model`).
- Added robust payload normalization for OpenRouter chat-completions (`instructions` + `input` -> `messages`, tool schema normalization).
- Fixed Arcee training path in prompt training:
  - model-aware provider/api-mode selection (`openrouter + chat_completions` for OpenRouter-like models),
  - fixed auth propagation so OpenRouter runs no longer send `Authorization: Bearer None`.
- Added explicit fallback logs (`[fallback] ...`) across training scripts and training runtime for faster failure diagnosis.
- Added `Auth/Login` line in training headers; confirmed for Arcee runs: `OpenRouter API key (~/.hermes/.env)`.
- Fixed monitor run-events behavior:
  - no more hard `404` for missing run IDs (`status=not_found` + empty events),
  - frontend auto-resets stale selected run IDs after gateway restart.
- Fixed monitor self-kill bug:
  - monitor-started scripts now force `AUTO_GATEWAY_RESTART=0`,
  - Arcee wrapper also disables restart when `RULESHIELD_TEST_MONITOR=1`.
- Test Monitor UX fixes:
  - `health check` and `suite` scripts prioritized at top.
  - script list now filtered by selected model/profile (profile-specific + generic scripts only).
  - selected model profile persisted; combo box no longer jumps back to OpenAI on run start.
- Current known operational caveat:
  - when gateway process is down, monitor shows repeated `ERR_CONNECTION_REFUSED`; this is expected until gateway is running again.
  - `favicon.ico 404` and `Unchecked runtime.lastError` in browser are non-blocking and unrelated to RuleShield runtime correctness.

### Current Stable Test Baseline
- Gateway URL: `http://127.0.0.1:8337`
- Dashboard URL: `http://localhost:5174/test-monitor`
- Health check: passing with Arcee profile in monitor mode (no gateway self-restart).
- Recommended start command (manual): `./demo/gateway_ctl.sh start`

## Effective Rules
<!-- Rules that consistently save costs -->

## Patterns Discovered
<!-- Recurring prompt patterns worth watching -->

## Total Lifetime Savings
$0.00
