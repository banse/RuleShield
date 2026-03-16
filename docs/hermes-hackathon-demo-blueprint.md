# RuleShield Hermes Hackathon Demo Blueprint

**Target length**: 60-90 seconds
**Primary goal**: Show that RuleShield makes Hermes cheaper in a safe, observable way.
**Secondary goal**: Show that this can grow into workflow optimization for Hermes Python API and cron-style tasks.

## Core Message

RuleShield is the optimization layer for Hermes:

- it intercepts repetitive prompts before they hit the upstream LLM
- it tests candidate rules safely in shadow mode
- it improves rule confidence through feedback
- it creates a path toward cheaper recurring Hermes workflows

## Demo Principles

- keep the live path simple
- show one clear Hermes flow
- prefer visible savings and safe rollout over feature breadth
- do not switch between too many pages
- do not explain internals longer than needed

## Recommended Live Setup

Use one stable provider/model pair for the whole recording.

Recommended live path:

- RuleShield gateway running
- dashboard running
- `/test-monitor` open
- one short Hermes health-check run
- one short Hermes-user run

Recommended profile for the live demo:

- Arcee or the currently most stable low-cost provider/model that passes the health check reliably

## Pages To Use

Use only these three views in the recording:

1. terminal for setup/start
2. `http://localhost:5174/test-monitor`
3. optionally one docs or landing/slides page for opening or closing frame

Avoid route-hopping during the core demo.

## Recording Order

## 1. Opening: 10-15s

### Visual

- your face/voiceover or slides/landing page

### Script

> The last time I got this excited about a new technology, it also became very expensive for me.
> That taught me how quickly infrastructure cost and friction can add up.
> With AI, I do not want to make the same mistake again.
> So I built RuleShield.

### Transition line

> RuleShield sits in front of Hermes, catches repetitive prompts, tests new rules safely in shadow mode, and improves through feedback over time.

## 2. Minimal setup: 10s

### Visual

- terminal

### Commands

```bash
ruleshield init --hermes
ruleshield start
```

### What to say

> RuleShield can patch an existing Hermes config or create a minimal starter config for a blank local setup.

If you want a slightly more grounded line:

> That means a normal Hermes user can get to a first protected run without digging through config files.

## 3. Health check: 10-15s

### Visual

- switch to `/test-monitor`
- run `test_training_health_check...`

### What to show

- selected model profile
- active run status
- prompt/answer log updating

### What to say

> First I run a short health check, just to prove the proxy, Hermes path, and monitor are all wired correctly.

Do not spend time on detailed logs here.

## 4. Main value moment: Hermes user run + RuleShield Live: 20-25s

### Visual

- start the Hermes-user run
- keep `RuleShield Live` and `Prompt/Antwort Monitor` visible

### What to highlight

- `Would Trigger (Shadow)`
- `Triggered Rules`
- `Run Savings`
- recent rule events if they appear

### What to say

> Now I run a more realistic Hermes user scenario.
> The important part is that RuleShield does not just blindly intercept.
> Candidate rules can run in shadow mode first, so we can compare what the rule would have done against the real LLM response before promoting anything.

Then:

> So this gives Hermes a safe path to optimization: first observe, then compare, then promote only what looks trustworthy.

## 5. Savings payoff: 10-15s

### Visual

- same `RuleShield Live` panel after the run finishes

### What to say

> This is the payoff: we can see how many prompts RuleShield could handle, how many rules actually triggered, and what that means for cost.

Optional stronger version:

> For an autonomous agent like Hermes, even small repetitive prompt families add up fast, so reducing that waste matters a lot over time.

## 6. Feedback loop: 8-10s

### Visual

- rule events / confidence movement if available
- otherwise keep it verbal and short

### What to say

> The feedback loop is what makes this more than a cache.
> Bad rules weaken, good rules get stronger, and over time Hermes gets a safer optimization layer instead of a static shortcut list.

## 7. Future direction: 8-10s

### Visual

- keep the same page or briefly show a cron-related docs/slide frame

### What to say

> And because Hermes can also be driven programmatically, for example through the Python API, the next step is not just intercepting prompts.
> It is shrinking recurring workflows themselves.

Then:

> That opens the door to a Cron Optimizer or even a Cron Replacer, where repeated agent jobs are split into deterministic pre-processing, a much smaller core prompt, and deterministic post-processing.

## 8. Close: 5s

### Script

> RuleShield helps Hermes reduce repetitive LLM spend today, and gives it a path toward safer self-optimization tomorrow.

## What Must Be Visible On Screen

At minimum, the recording should visibly include:

- `ruleshield init --hermes`
- `ruleshield start`
- the test monitor
- an active or just-finished run
- `RuleShield Live`
- at least one visible savings or rule-trigger metric

## What Not To Show

- provider switching mid-demo
- unstable gateway restarts
- too many dashboard routes
- raw internal debugging
- long terminal output dumps
- speculative RL details beyond one sentence

## Alternative Cut: Mid-Video Test Monitor Segment

Use this only if there is enough time and the gateway/test monitor are behaving cleanly.

This version keeps the main story intact, but inserts the monitor as a stronger
"live instrumentation" moment in the middle.

### Best use case

- the normal Hermes interaction looks good
- the test monitor is stable
- run-scoped RuleShield Live values look readable
- you want a stronger proof point for shadow mode and observability

### Where to insert it

Insert after the normal Hermes interaction and before the future-direction close.

### Structure

1. opening motivation
2. minimal setup
3. short normal Hermes interaction
4. **cut to Test Monitor**
5. short explanation of:
   - shadow mode
   - would-trigger vs triggered
   - safe promotion path
6. close with Python API / Cron Optimizer vision

### What to say

> The normal Hermes interaction is what the user sees.
> This monitor is what RuleShield sees behind the scenes.

Then:

> Here we can watch candidate rules in shadow mode, see what would have triggered, what actually triggered, and use that to decide what is safe to promote.

### Important rule

Do not let the monitor replace the product story.

It should support the demo, not become the whole demo.

The viewer should still come away with:

- Hermes is the main product
- RuleShield is the optimization layer
- shadow mode makes optimization safer

## Best Fallback If Live Data Misbehaves

If the live panel is not behaving reliably during recording:

1. keep the health check short
2. use a known-good completed run in the monitor
3. narrate the shadow/savings story over stable data
4. use screenshots as backup

The audience cares more about clarity than about whether every number was generated 3 seconds earlier.

## Suggested Run Order

Use this exact order unless a more stable path emerges:

1. `ruleshield init --hermes`
2. `ruleshield start`
3. open `/test-monitor`
4. run `test_training_health_check...`
5. run `test_training_hermes_user_suite...`
6. narrate `RuleShield Live`
7. close with Python API / Cron Optimizer vision

## Backup Assets To Prepare Before Recording

- one screenshot of `/test-monitor` with an active run
- one screenshot of `/test-monitor` with finished savings numbers
- one screenshot of docs or slides for the opening/closing frame
- final tweet text
- final short Discord submission text
