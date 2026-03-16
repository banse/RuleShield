# User-Story Test Suite - Design Document

**Mode**: Standard  
**Date**: 2026-03-16  
**Status**: Final

## Problem Statement

RuleShield currently has a mix of unit tests, demo scripts, training scripts, and ad-hoc hackathon flows, but no single trustworthy test suite that answers the most important product question:

**Can a real end user install RuleShield, run it through Hermes, observe the intended behavior, and trust that the key workflows still work after every change?**

The problem is not just test coverage. The problem is that the repo does not yet enforce a durable, user-story-centered definition of “done”. That creates three risks:

1. hackathon-critical flows can silently regress
2. new features can ship without proving the existing user experience still works
3. contributors do not have one canonical test suite to run before committing

We need one coherent test strategy that:

- covers the real user stories that matter most
- is suitable both for local development and automated execution
- becomes the gating layer before every commit
- makes “no test, no merge/commit” the normal rule for new features

## Understanding

### Facts

- The repo already contains:
  - unit/integration-style Python tests in `tests/`
  - many shell-based demo/training flows in `demo/`
  - dashboard and monitor flows in `dashboard/`
- The current hackathon story depends heavily on:
  - install/init path
  - Hermes integration
  - prompt training / health-check runs
  - shadow mode
  - observable RuleShield behavior
- The monitor and gateway lifecycle are still not fully stable under load.
- The health-check scenario is useful as a baseline but weak as a visible rule-trigger story.
- We already identified current reliability issues in:
  - [/Users/banse/codex/hermes/ruleshield-hermes/docs/current-issues.md](/Users/banse/codex/hermes/ruleshield-hermes/docs/current-issues.md)

### Context

- Backend: FastAPI / Python
- Frontend: SvelteKit
- CLI: Click
- Current scripts are shell-heavy and practical, but they are not yet organized as a disciplined product test matrix.
- Current tests skew toward implementation verification, not end-user workflows.

### Constraints

- KISS should dominate the design.
- User stories matter more than low-level test abundance.
- The suite should be reusable for both:
  - local developer confidence
  - automated pre-commit / CI checks
- We should avoid a giant brittle browser-only system.
- The gateway instability means the suite must separate:
  - small stable smoke tests
  - deeper scenario tests
- New features should not be accepted unless the suite covers them.

### Unknowns (Resolved)

- [x] Where current user-facing test material lives  
  → mostly in `demo/`, with Python tests in `tests/`
- [x] Whether there is already a stable user-story test backbone  
  → no, only partial building blocks
- [x] Whether current scripts can be reused  
  → yes, but they need to be reorganized under a clearer test taxonomy

### Unknowns (Open)

- [ ] How much of the gateway instability should be fixed before the suite becomes hard-gated
- [ ] Whether browser-level monitor assertions should be part of the core pre-commit path or only a slower integration tier

## Research & Input

Current relevant material:

- install/init path via `ruleshield init --hermes`
- gateway control via `demo/gateway_ctl.sh`
- health/training scripts in `demo/`
- Python tests in `tests/test_imports.py` and `tests/test_prompt_training.py`
- hackathon live/demo expectations in:
  - [/Users/banse/codex/hermes/ruleshield-hermes/docs/hermes-hackathon-demo-blueprint.md](/Users/banse/codex/hermes/ruleshield-hermes/docs/hermes-hackathon-demo-blueprint.md)
  - [/Users/banse/codex/hermes/ruleshield-hermes/docs/current-issues.md](/Users/banse/codex/hermes/ruleshield-hermes/docs/current-issues.md)

Main insight:

We already have enough ingredients for a good suite, but they are arranged around scripts and experiments, not around product promises.

## Solutions Considered

### Option A: Expand the existing ad-hoc scripts and call that the suite

**Approach**: Keep building on `demo/test_*.sh`, add more scripts, and run them manually or in CI.

**Pros**:
- fastest short-term path
- reuses existing hackathon flows
- minimal structural work

**Cons**:
- still script-centric rather than story-centric
- naming and purpose remain muddy
- no strong contract about what belongs in the “must pass before commit” path
- harder to scale as product surface grows

**Sacrifices**:
- long-term clarity
- maintainable ownership model for testing

### Option B: Build a layered user-story test suite with stable tiers

**Approach**:
- define a small set of canonical user stories
- map each story to a dedicated test entrypoint
- keep a layered suite:
  - Tier 1: fast smoke tests
  - Tier 2: user-story workflow tests
  - Tier 3: slower extended scenario/integration tests
- make Tier 1 + Tier 2 mandatory before commit
- require new features to add or update at least one story-level test

**Pros**:
- aligns tests with user value
- scales better
- easier to explain to contributors
- gives a durable “definition of done”
- naturally supports local and CI use

**Cons**:
- requires upfront taxonomy work
- some current scripts need renaming/refactoring/reframing
- forces sharper decisions about what is “core” vs “extended”

**Sacrifices**:
- short-term convenience
- some freedom to ship untested experiments quickly

### Option C: Heavy browser-first E2E suite as the primary test backbone

**Approach**:
- use browser automation as the main truth source
- drive installation, dashboard, monitor, and flows via UI

**Pros**:
- very close to user experience
- good for demos and visual regressions

**Cons**:
- too brittle as the primary gate
- slower
- more sensitive to current gateway instability
- harder to keep deterministic

**Sacrifices**:
- speed
- reliability of everyday pre-commit usage

## Tradeoffs Matrix

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Simplicity | Medium | High | Low |
| User-story fidelity | Medium | High | High |
| Pre-commit suitability | Medium | High | Low |
| Long-term maintainability | Low | High | Low |
| Speed to implement | High | Medium | Low |
| CI friendliness | Medium | High | Low |

## Recommendation

Choose **Option B: a layered user-story test suite with stable tiers**.

### Reasoning

It is the best balance of:

- KISS
- real product coverage
- contributor discipline
- long-term maintainability

It also lets us reuse what already exists without pretending the current script set is already a coherent test system.

The key principle is:

**Test stories, not internals first.**

Internals still matter, but the top-level gate should answer:

- can a user install it?
- can Hermes run through it?
- do the core RuleShield behaviors happen?
- does the dashboard/monitor reflect the expected state well enough?
- do known hackathon-critical workflows still work?

## Proposed Test Suite Shape

### Tier 1: Fast Core Smoke

Purpose: catch immediate breakage in under a few minutes.

Examples:
- import/boot tests
- config load and patch/restore tests
- proxy health boot test
- SDK wrapper instantiation test
- dashboard build/type check

Run:
- every commit
- pre-push
- CI

### Tier 2: Core User Stories

Purpose: verify the main end-user product promises.

These should be the canonical suite that must pass before every commit.

Proposed user stories:

1. **Install and initialize RuleShield**
   - create config
   - patch Hermes config
   - restore Hermes config

2. **Start RuleShield and verify gateway health**
   - gateway becomes healthy
   - expected port matches config

3. **Run Hermes through RuleShield on the normal local path**
   - simple prompt passthrough works
   - transcript/report artifacts are generated

4. **Run a tiny rule-triggering workflow**
   - greetings / acknowledgment / goodbye prompts
   - at least one rule or shadow candidate becomes observable

5. **Run the baseline health-check workflow**
   - current `test_training_health_check.sh`
   - validates the standard product path

6. **Verify dashboard-facing monitor data contract**
   - monitor API returns expected fields for scripts / runs / ruleshield
   - run-scoped values reset correctly when selection changes

### Tier 3: Extended Scenarios

Purpose: broader confidence, not mandatory on every single commit unless relevant.

Examples:
- Hermes user short / medium / complex suite
- vibecoder suite
- shadow coverage diagnostic
- OpenRouter secondary-path tests
- browser-level dashboard/monitor E2E

Run:
- pre-merge
- nightly
- before release
- when touching affected feature areas

## Proposed Canonical User Stories

These should become the backbone of the suite.

### Story A: Fresh local install

“As a new local user, I can install RuleShield, initialize it, and get a valid config and Hermes patch without manual file surgery.”

### Story B: Gateway starts from config

“As a user, I can start RuleShield and the running gateway honors the configured port from the central config.”

### Story C: Hermes basic flow works

“As a Hermes user, I can send normal prompts through RuleShield and receive valid responses.”

### Story D: RuleShield visibly adds value

“As a user, I can run a simple workflow where RuleShield catches or shadow-tests obvious repetitive prompts.”

### Story E: Health-check training path works

“As a user, I can run the recommended health-check script and get reports/transcripts without hand-editing environment details.”

### Story F: UI/monitor contract is correct

“As a user, the monitor reflects the right scripts, run selection, and run-scoped RuleShield state for the chosen profile.”

### Story G: Feedback loop updates rule quality safely

“As a user, I can accept or reject an intercepted response and RuleShield records that feedback in a way that affects future confidence.”

### Story H: Hermes rollback stays clean

“As a user, I can undo the Hermes patch and return to my previous Hermes base URL without manual repair.”

## Hackathon Feature Coverage Matrix

The suite should cover the actual hackathon promise surface, not just technical components.

| Hackathon feature / promise | Primary user story | Test tier | Why it matters |
|-----------------------------|--------------------|-----------|----------------|
| `ruleshield init --hermes` works for a blank or existing setup | Story A | Core | This is the first-run user experience |
| gateway starts from configured install port | Story B | Core | Prevents the current “works only on my local test port” failure mode |
| Hermes works normally through RuleShield | Story C | Core | This is the core product behavior |
| obvious repetitive prompts get intercepted or shadow-compared | Story D | Core | This is the clearest product payoff |
| recommended health-check flow works end-to-end | Story E | Core | This is the current demo and support path |
| monitor/profile/script selection stays truthful | Story F | Core | Avoids misleading UI states |
| feedback loop is real, not just claimed | Story G | Core | This is part of the differentiation story |
| Hermes can be restored cleanly | Story H | Core | Protects install trust and uninstall confidence |
| OpenRouter / Arcee secondary path | Extended scenario | Extended | Useful coverage, but not stable enough to gate every commit |
| longer Hermes suites (short / medium / complex) | Extended scenario | Extended | Good confidence expansion after core stories are stable |
| browser-level visual monitor checks | Integration | Extended | Valuable, but too brittle for the first hard gate |

## Suite Contract

The suite should answer one question before code is committed:

**Would a normal local Hermes user still trust this change after installing, running, observing, and undoing RuleShield?**

That means the suite is not organized around modules first. It is organized around:

1. install
2. start
3. use
4. observe
5. learn
6. rollback

## Suite Organization Proposal

Create a dedicated top-level structure:

```text
tests/
  smoke/
  stories/
  integration/
  fixtures/
```

And keep `demo/` for:

- demos
- recordings
- exploratory/manual scripts

Concrete rule:

- if a script is required for product confidence, it should live under `tests/`
- if a script is primarily for showcase/manual use, it can stay under `demo/`

## Enforcement Policy

### Before every commit

Mandatory:
- `tests/run-commit-suite.sh`

This commit suite must stay small enough to be realistic, but strong enough to protect the product contract.

Recommended contents:
- Tier 1 smoke
- the smallest deterministic subset of Tier 2:
  - Story A
  - Story B
  - Story C
  - Story D
  - Story H

### Before merge / release

Mandatory:
- `tests/run-core-suite.sh`
- all core stories
- relevant extended scenarios for touched areas

### Before release / demo refresh

Mandatory:
- `tests/run-full-suite.sh`
- core stories
- extended scenarios
- browser/integration checks that are stable enough to matter for demos

### For new features

Policy:
- no new feature should be committed unless:
  - it is covered by at least one existing user-story test, or
  - a new user-story/integration test is added for it

Plain rule:

**No coverage, no commit.**

More concrete rule:

- if a feature changes an existing user story, update that story test
- if a feature creates a new user-visible workflow, add a new story test
- if a feature is too hard to test at story level, the design is probably too coupled or too internal-facing

## Automation Plan

### Local

Add one canonical command:

```bash
./tests/run-commit-suite.sh
```

This should run the commit gate:
- smoke tests
- smallest deterministic user stories

Add one canonical core command:

```bash
./tests/run-core-suite.sh
```

This should run:
- smoke tests
- core user-story tests

Add one extended command:

```bash
./tests/run-full-suite.sh
```

This should run:
- core suite
- extended scenarios

### Pre-commit / pre-push

Recommended:
- pre-commit hook runs `run-commit-suite.sh`
- pre-push hook runs `run-core-suite.sh`

Why:
- “before every commit” should stay true in spirit and tooling
- but the literal commit hook must remain fast enough that contributors do not bypass it
- the heavier but still blocking user-story suite should run before push and in CI

Therefore the enforcement ladder is:

1. commit: `run-commit-suite.sh`
2. push: `run-core-suite.sh`
3. CI / release: `run-full-suite.sh`

### CI

GitHub Actions matrix:

1. commit suite
2. core stories
3. extended scenarios
4. optional browser/integration

## Implementation Plan

### Phase 1: Freeze the contract

1. **Freeze the canonical core stories**
   - finalize Stories A-H as the official product contract
2. **Tag each existing script**
   - `core`
   - `extended`
   - `demo/manual`
3. **Define pass/fail output contract**
   - every story test writes a small machine-readable result artifact

### Phase 2: Build the minimal gate

4. **Create the dedicated test-suite layout**
   - `tests/smoke`
   - `tests/stories`
   - `tests/integration`
   - `tests/fixtures`
5. **Build the tiny rule-trigger story**
   - greetings / thanks / goodbye
   - assert at least one observable rule or shadow event
6. **Add install/start/rollback stories**
   - Story A
   - Story B
   - Story H
7. **Add canonical runners**
   - `tests/run-commit-suite.sh`
   - `tests/run-core-suite.sh`
   - `tests/run-full-suite.sh`

### Phase 3: Cover the hackathon promise

8. **Promote the OpenAI/Hermes path to primary core coverage**
   - Story C
   - Story E
9. **Add feedback-loop story coverage**
   - Story G
10. **Stabilize monitor data-contract assertions**
   - Story F at API/data level first
   - browser-level checks only after the data path is trustworthy

### Phase 4: Make it enforceable

11. **Add git hook enforcement**
   - commit hook runs `run-commit-suite.sh`
   - push hook runs `run-core-suite.sh`
12. **Update contributor rules**
   - new feature requires story coverage
   - flaky demo scripts do not count as feature coverage
13. **Keep extended providers non-blocking until stable**
   - OpenRouter / Arcee remain extended until gateway lifecycle and timeout issues are fixed

## Proposed Script Mapping

This is the clean starting taxonomy.

### Core

- current `demo/test_training_health_check.sh`
  - becomes or is wrapped by `tests/stories/story_health_check.sh`
- new tiny rule-trigger script
  - becomes `tests/stories/story_rule_trigger.sh`
- new install/start/restore script
  - becomes `tests/stories/story_install_start_restore.sh`

### Extended

- `demo/test_training_hermes_user_suite.sh`
- `demo/test_training_vibecoder_suite.sh`
- `demo/test_shadow_coverage_check.sh`
- OpenRouter profile variants

### Demo / Manual only

- `demo/test_all.sh`
- `demo/test_morning_workflow.sh`
- `demo/test_code_review.sh`
- `demo/test_research.sh`
- `demo/test_cron_replacement.sh`
- `demo/test_morning_workflow.sh`

These are still useful, but they should not define the quality gate.

## Open Questions

- When the gateway lifecycle is fixed, should the tiny rule-trigger story assert `triggered_rules > 0`, `would_trigger_shadow > 0`, or either?
- Should feedback-loop coverage be CLI-level only at first, or also verify dashboard/API reflection in the same story?
- Once monitor correctness is fixed, should Story F stay API-level only or gain a small browser check in the core suite?

## Immediate Next Move

The best next implementation step is:

1. create a **tiny deterministic story test** for obvious rule-trigger prompts
2. create `tests/run-commit-suite.sh` and `tests/run-core-suite.sh`
3. add one install/start/restore story around the clean `8347` path
4. document the “no coverage, no commit” rule in contributing docs

That gives us a realistic hard gate quickly, while leaving the longer suites and browser checks for the next pass.
