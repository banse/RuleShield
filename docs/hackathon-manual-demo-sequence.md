# Hackathon Manual Demo Sequence

**Goal**: Record a normal Hermes interaction instead of a pure test script, while still making RuleShield effects easy to see.

## Why This Exists

For the final video, a fully scripted test run is useful as backup, but a normal Hermes interaction feels more real.

This sequence is meant to:

- show Hermes in a natural flow
- produce a few obvious RuleShield wins
- still include at least one real LLM task
- keep the demo short and readable

## Recommended Model

Use:

- `GPT-5.1 Mini (OpenAI OAuth)`

Why:

- more credible cost story than a free model
- still relatively affordable for a short demo
- already integrated in the current local setup

## Suggested Recording Layout

Use:

- Hermes interaction on the left or in the main terminal area
- RuleShield dashboard or test monitor visible beside it if possible

If split-screen is too messy:

1. show Hermes prompt/response
2. cut to RuleShield panel
3. continue Hermes

## Recommended Prompt Sequence

Use only a short sequence.

### Segment A: obvious repetitive prompts

These should demonstrate direct RuleShield-style value.

1. `hi`
2. `thanks`
3. `bye`

Optional:

4. `ok`

These are useful because the viewer immediately understands why these should not need a full expensive LLM call every time.

## Segment B: one real task

Use one real LLM-shaped task in the middle.

Recommended options:

- `read README.md and summarize it briefly`
- `inspect this project and tell me what it does`
- `what should I look at first in this repo?`

Pick only one.

The purpose is to show contrast:

- some prompts should stay real model work
- some prompts should be optimized away

## Segment C: safe rollout explanation

After the short interaction, briefly cut to the RuleShield panel and explain:

- some prompts can be intercepted directly
- candidate rules can stay in shadow mode first
- only the rules that look trustworthy should be promoted

## Best Sequence For The Video

1. `hi`
2. `read README.md and summarize it briefly`
3. `ok thanks`
4. `bye`

This is probably enough.

## What To Say While Doing It

Suggested short narration:

> Some prompts are real work and should still go to the model.
> But a lot of normal agent interaction is repetitive.
> Greetings, acknowledgments, short confirmations, and repeated workflow patterns add up over time.

Then on the RuleShield panel:

> RuleShield is useful because it can catch those repetitive prompts directly, while using shadow mode to validate new rules safely before they go live.

## What To Avoid In The Manual Demo

- too many prompts
- prompts that trigger unreliable rule families
- long tool-heavy workflows
- long pauses while waiting for the model
- anything that requires debugging on camera

## Fallback

If the manual Hermes interaction becomes noisy or slow:

- keep only `hi`
- one real repo summary prompt
- `thanks`
- then cut to the RuleShield panel and continue narration there
