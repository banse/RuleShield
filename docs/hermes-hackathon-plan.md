# RuleShield Hermes Hackathon Plan

**Date**: 2026-03-16
**Status**: Active
**Goal**: Submit RuleShield to the Hermes Agent Hackathon with a demo that is creative, useful, and easy to believe.

## Problem We Must Solve

RuleShield already has strong technical substance, but hackathons are not won by raw feature count.

We need three things to land at once:

1. a clear demo story that shows real value in under a few minutes
2. a setup flow that works for someone starting from a normal Hermes install
3. a submission package that looks polished and low-risk

If any one of these fails, the project becomes harder to judge, harder to trust, and easier to dismiss.

## Success Criteria

We should consider the hackathon effort successful if we can show:

- RuleShield saving real Hermes traffic from hitting the upstream LLM
- shadow mode proving where RuleShield is safe and where it still needs tuning
- a fresh Hermes user getting from install to first protected run without manual config archaeology
- a short video demo that is easy to follow without deep prior context
- a tweet + brief writeup + Discord submission ready before deadline

## Hackathon Positioning

The strongest positioning is:

**RuleShield is the optimization layer for Hermes.**

Not a generic proxy.
Not just a cache.
Not just a rule engine.

It is the layer that lets Hermes:

- avoid waste on repetitive prompts
- observe rule quality in shadow mode
- improve rule confidence through feedback
- prepare the path toward agent self-optimization

This aligns well with the judging criteria:

- **Creativity**: an agent-side optimization layer that learns from live usage
- **Usefulness**: cost savings, safer rule rollout, operational visibility
- **Presentation**: a concrete before/after demo with dashboards and live traffic

## Recommended Demo Story

The demo should stay simple and believable.

### Core story

1. Start with a normal Hermes workflow.
2. Show that many prompts are short, repetitive, and expensive to send upstream.
3. Put RuleShield in front of Hermes.
4. Show:
   - direct rule hits for obvious prompt families
   - shadow comparisons for candidate rules
   - live feedback / confidence behavior
   - what this means for cost and rollout safety

### Best demo sequence

1. **Opening**
   - one sentence problem statement:
   - "Hermes is powerful, but normal agent usage includes many repetitive prompts that do not need a full LLM call."

2. **Normal Hermes integration**
   - show the minimal setup path
   - ideally `ruleshield init --hermes`
   - start gateway
   - open test monitor / dashboard

3. **Health check**
   - run the shortest working test
   - prove the proxy, monitor, and live logs are wired

4. **Realistic Hermes user run**
   - run a short Hermes-user scenario
   - show greetings, acknowledgments, status checks, clarification-style prompts
   - keep prompts cheap but realistic

5. **Shadow mode**
   - explain:
   - "candidate rules can run in the background without changing real answers"
   - show where a rule would trigger
   - show comparison quality

6. **Feedback loop**
   - show confidence movement or rule event history
   - keep explanation short:
   - "bad rules weaken, good rules get promoted"

7. **Close**
   - summarize:
   - "RuleShield helps Hermes reduce waste today and build a safer optimization loop for tomorrow."

## What Not To Overemphasize

These are useful, but should stay secondary in the final demo:

- too many provider/model combinations
- long architectural deep dives
- speculative RL future work
- too many pages in the dashboard
- too much time on synthetic benchmark claims

The primary demo should feel like:

- normal Hermes
- one extra layer
- immediate operational value

## Workstreams

## Workstream A: Submission Narrative

This is the judging-facing layer.

### Deliverables

- final hackathon positioning sentence
- 60-120 second video structure
- single recording runbook
- tweet copy
- short submission writeup for Discord
- backup static screenshots in case live demo capture fails

### Personal origin story

Use a short personal motivation at the beginning of the video.

Keep it brief and grounded:

> The last time I got this excited about a new technology, it also became very expensive for me.
> That taught me how quickly infrastructure cost and friction can add up.
> With AI, I do not want to make the same mistake again.
> So I built RuleShield.

This should support the story, not dominate it.

Guidelines:

- do not mention exact ETH amounts
- keep it to roughly 10-15 seconds
- move quickly from motivation into the live demo
- use it to frame the cost problem as personal and real

### Must show

- what problem exists
- how RuleShield plugs into Hermes
- why shadow mode matters
- why the feedback loop matters
- what makes this more than a plain cache

### Hermes-native future direction

Use one short forward-looking line in the writeup or near the end of the video:

> Because Hermes can also be driven programmatically, RuleShield can grow from a prompt optimizer into a workflow optimizer.

What that means:

- recurring **pre-processing** can move into deterministic code
- the **prompt** can shrink to the part that actually needs intelligence
- recurring **post-processing** can move back into deterministic code

This is especially relevant for:

- Hermes Python API workflows
- cron-like repeated agent tasks
- structured recurring automations

Call out one concrete example when useful:

- a future `Cron Optimizer / Replacer` flow where recurring Hermes jobs are partially turned into deterministic pre/post steps, so the remaining prompt is much smaller and cheaper

Important:

- mention this as the next step, not the main live demo
- keep the live demo focused on shadow mode, safe rollout, and savings
- use this to strengthen the creativity angle in the submission
- mention cron optimization as a concrete next product direction

## Workstream B: Blank-Start Hermes Integration

This is the most important product gap before submission.

Today, `ruleshield init --hermes` patches Hermes only when an existing Hermes config is already present.

That is not enough for a clean "normal user" story.

### Target user experience

A fresh user should be able to:

1. install RuleShield
2. point Hermes at it with minimal steps
3. start Hermes without hand-editing config files unless they want to

### Required behavior

- detect whether `~/.hermes/config.yaml` exists
- if missing, bootstrap a minimal valid Hermes config or create a guided starter config
- patch Hermes base URL to the RuleShield proxy
- avoid storing secrets in git
- keep auth resolution local-only:
  - `~/.codex/auth.json`
  - `~/.hermes/.env`
  - user environment variables

### Required docs

- fresh-start quickstart
- auth/login expectations by provider
- restore / rollback path
- "how to verify it works" section

### Required CLI honesty

The CLI output must match reality.

Specifically:

- no wrong path references like `~/.hermes/cli-config.yaml`
- clear next step if Hermes config is missing
- clear distinction between:
  - config patched
  - config created
  - config skipped

## Workstream C: Demo Reliability

The demo must survive realistic local usage.

### Goals

- gateway starts reliably
- health check always works
- test monitor behaves predictably
- run data is understandable
- no confusing global fallback values in run-scoped panels

### Critical demo-safe requirements

- `RuleShield Live` must show current run data only
- health check should never display unrelated historic totals
- test scripts list should match selected profile cleanly
- monitor logs should make auth/fallback behavior obvious
- gateway restart behavior should not silently destroy operator confidence

### Follow-up improvement

Persist minimal test-run state across gateway restarts.

This is not mandatory for the hackathon demo if the gateway is kept stable during recording, but it is a strong reliability upgrade.

## Workstream D: Hermes-Native Scenarios

The tests should feel like Hermes usage, not a benchmark harness.

### Recommended scenario stack

- **health check**
  - proves the wiring
- **Hermes user short**
  - cheap, fast, rule-friendly prompt families
- **Hermes user medium**
  - broader user behavior with normal follow-ups
- **vibecoder**
  - demonstrates coding-agent traffic and tool-heavy responses
- **shadow coverage check**
  - sanity-checks whether candidate rule families are even being exercised

### Guiding principle

Prompt complexity should stay low-cost.
Training complexity should come from broader coverage, not from longer prompts.

## Workstream E: Presentation Assets

We already have a strong base:

- dashboard
- docs site
- slides
- test monitor

For the hackathon package, we should freeze a minimal subset.

### Keep in the final presentation flow

- landing page or slides for framing
- test monitor for live execution
- one docs page for technical trust

### Avoid in the live path

- too many route changes
- too many feature tours
- pages that are not actively used in the demo story

## Execution Plan

## Phase 1: Stabilize the setup story

### Objective

Make the first-run Hermes integration believable and repeatable.

### Tasks

- fix `ruleshield init --hermes` messaging
- support missing Hermes config on blank start
- document provider auth expectations
- add a verification step:
  - "send one prompt through Hermes and confirm RuleShield saw it"

### Exit criteria

- a fresh user path exists in docs
- CLI output matches actual behavior
- no manual file archaeology is required

## Phase 2: Stabilize the demo environment

### Objective

Reduce demo-time surprises.

### Tasks

- verify gateway startup and restart path
- validate Arcee/OpenRouter health check end to end
- verify test monitor run scoping
- verify rule event visibility for active runs
- capture one known-good demo flow

### Exit criteria

- one demo path works twice in a row
- no misleading global counters appear in run-scoped UI

## Phase 3: Freeze the hackathon narrative

### Objective

Turn the project into a judging-friendly story.

### Tasks

- tighten `HACKATHON_SUBMISSION.md`
- update README claims to match actual blank-start behavior
- prepare short script for voiceover
- decide final metric framing:
  - focus on savings + safe rollout, not just raw rule count

### Exit criteria

- one crisp sentence explains RuleShield
- one short demo script exists
- one short tweet/writeup exists

## Phase 4: Record and submit

### Objective

Ship cleanly before deadline.

### Tasks

- choose the recording stack
- record video demo
- export backup screenshots
- post tweet tagging `@NousResearch`
- send tweet link to Discord submissions channel

### Exit criteria

- public tweet live
- Discord submission posted
- all links work

## Phase 5: Public release pass

### Objective

Prepare the repository for public visibility without destabilizing the demo build.

### Tasks

- run a focused code review on the most fragile areas
- remove stale hackathon-only wording or inconsistent claims
- do a light KISS refactor where it reduces confusion
- verify no secrets or private local assumptions leak into the public repo
- check that public-facing docs match actual behavior

### Review focus

- test monitor
- run-scoped RuleShield Live logic
- Hermes blank-start integration
- gateway start/stop flow
- model/profile script handling
- public docs and setup instructions

### Refactor scope

Keep this pass small.

Good:

- rename misleading helpers
- remove stale comments and dead branches
- reduce obvious duplication
- tighten docs and CLI wording

Avoid:

- major architecture changes
- new feature work
- broad rewrites just before public release

### Exit criteria

- no secrets in tracked files
- no major known demo-time bugs left open without documentation
- README and docs are honest
- repo feels understandable to a new external reader

## Recommended Order For Immediate Work

If time is tight, the highest-value order is:

1. blank-start Hermes integration
2. demo reliability on one provider/model pair
3. final hackathon writeup and script
4. video recording
5. optional polish
6. public release pass

## Risks

## Risk 1: Setup claims exceed reality

If README and CLI imply "three commands and done" but a fresh Hermes user still has to manually repair config, trust drops fast.

### Mitigation

- make setup path fully honest
- document the exact blank-start path
- reduce magic

## Risk 2: Dashboard tells the wrong story

If run-scoped panels show historic global values, the demo becomes harder to trust.

### Mitigation

- keep run-scoped UI strictly run-scoped
- prefer blank state over misleading fallback

## Risk 3: Too many features, weak presentation

Hackathon judges will not reward feature sprawl if the story is blurry.

### Mitigation

- one problem
- one clear solution
- one believable demo flow

## Recommended Final Submission Angle

Use this as the default framing:

> RuleShield is the optimization layer for Hermes Agent. It catches repetitive prompts before they hit the upstream LLM, runs candidate rules safely in shadow mode, and improves rule confidence through feedback so Hermes gets cheaper and smarter over time.

## Next Actions

The next concrete implementation steps should be:

1. fix blank-start Hermes setup behavior and docs
2. verify one stable demo run on the chosen provider/model
3. tighten `HACKATHON_SUBMISSION.md` to match the actual live demo
4. prepare tweet copy and recording checklist
