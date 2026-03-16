# Public Release Checklist

## Goal

Make the repository safe, understandable, and credible before switching to public.

## 1. Security / Privacy

- verify no API keys or tokens are tracked
- verify no auth files are tracked
- verify no private local machine details are exposed unnecessarily
- verify no accidental debug dumps or request dumps are committed
- verify `.gitignore` covers generated local artifacts

## 2. Public-Facing Honesty

- README claims match real behavior
- setup steps are actually reproducible
- dashboard/docs routes listed are real and working
- no leftover outdated claims from earlier experiments
- no misleading “automatic” setup claims if manual steps still exist

## 3. Code Review Focus

Prioritize findings over style.

Review these areas first:

- `ruleshield/proxy.py`
- `ruleshield/config.py`
- `ruleshield/cli.py`
- `dashboard/src/routes/test-monitor/+page.svelte`
- public docs and submission assets

Look for:

- wrong fallbacks
- confusing state behavior
- stale feature flags
- demo-only shortcuts
- hidden coupling to the local machine

## 4. Light Refactor Only

Allowed:

- remove dead code
- rename misleading functions or strings
- tighten duplicated branches
- improve comments and operator-facing messages

Avoid:

- big rewrites
- architecture churn
- speculative cleanup with regression risk

## 5. Docs Pass

- README
- Hermes integration docs
- hackathon docs
- dashboard docs pages

Check:

- quickstart
- rollback path
- auth expectations
- shadow mode explanation
- savings claims
- future-direction wording

## 6. Demo Readiness

- one stable demo path still works after cleanup
- test monitor still behaves as expected
- RuleShield Live still shows run-scoped data only
- recorded flow still matches docs and voiceover

## 7. Final Public Check

Before making the repo public:

- run the stable demo path once more
- skim git diff for accidental local noise
- confirm no private notes or machine-specific paths are exposed where they should not be
- confirm tweet/submission/docs all tell the same story
