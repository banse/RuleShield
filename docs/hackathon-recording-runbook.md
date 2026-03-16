# Hackathon Recording Runbook

## Goal

One single runbook for recording the final RuleShield hackathon demo.

Use this as the only document during recording.

## Final Demo Shape

- Main story: normal Hermes interaction with `GPT-5.1 Mini`
- Optional cut: short Test Monitor segment in the middle
- Tone: simple, calm, credible
- Target length: `75-90 seconds`
- Hard max: `120 seconds`

## Final Title Cards

### Opening Card

```text
RuleShield
Cut repetitive LLM spend. Validate safely in shadow mode.
```

### Optional Mid-Monitor Overlay

```text
What the user sees vs. what RuleShield sees
```

### Closing Card

```text
Optimize safely. Spend less. Learn over time.
RuleShield
```

### End Frame

```text
RuleShield
github.com/banse/RuleShield
```

## Final Prompt Sequence

Use exactly these prompts in the main Hermes interaction:

1. `hi`
2. `read README.md and summarize it briefly`
3. `ok thanks`
4. `bye`

Avoid:

- `status`
- `show me what changed`
- `undo that`
- long tool-heavy prompts
- live debugging during recording

## Shot List

### Shot 1: Opening

- Screen: opening card
- Duration: `5-8s`
- Purpose: establish product and promise

### Shot 2: Setup

- Screen: terminal
- Show:

```bash
ruleshield init --hermes
ruleshield start
```

- Duration: `8-12s`
- Purpose: prove setup path is real, but do not linger

### Shot 3: Hermes Prompt 1

- Screen: Hermes
- Prompt: `hi`
- Duration: `6-8s`
- Purpose: obvious repetitive interaction

### Shot 4: Hermes Prompt 2

- Screen: Hermes
- Prompt: `read README.md and summarize it briefly`
- Duration: `10-15s`
- Purpose: show one clearly real LLM task

### Shot 5: Hermes Prompt 3

- Screen: Hermes
- Prompt: `ok thanks`
- Duration: `4-6s`
- Purpose: second repetitive interaction

### Shot 6: Hermes Prompt 4

- Screen: Hermes
- Prompt: `bye`
- Duration: `4-6s`
- Purpose: clean finish for the user flow

### Shot 7: Optional Monitor Cut

- Screen: Test Monitor / RuleShield Live
- Duration: `10-15s`
- Show:
  - active or finished run
  - RuleShield Live
  - Prompt/Antwort Monitor
- Purpose: show what RuleShield sees behind the scenes

### Shot 8: Future Direction

- Screen: monitor or simple static frame
- Duration: `8-12s`
- Purpose: Python API workflows, recurring tasks, Cron Optimizer / Replacer

### Shot 9: Closing

- Screen: closing card
- Duration: `4-6s`
- Purpose: leave the final thesis clearly on screen

## Main Voiceover

```text
The last time I got this excited about a new technology, it also became very expensive for me.

That taught me how quickly infrastructure cost and friction can add up when you use a powerful system a lot.

With AI, I do not want to make the same mistake again.

So I built RuleShield.

RuleShield is an optimization layer that sits in front of Hermes. It catches repetitive prompts before they hit the upstream LLM, tests candidate rules safely in shadow mode, and improves over time through feedback.

Here I am running Hermes through RuleShield and starting with a short health check to prove the proxy, agent path, and monitor are wired correctly.

Now I switch to a normal Hermes interaction.

The key idea is that RuleShield does not just blindly intercept. Some prompts should still go to the model, but repetitive prompts and recurring interaction patterns do not always need a full upstream call.

And when I want to inspect what is happening behind the scenes, I can cut to the monitor. That is where shadow mode becomes useful: candidate rules run in the background so we can compare what the rule would have returned against the real LLM response before promoting anything.

That gives Hermes a safe path to optimization: observe, compare, then promote only what looks trustworthy.

The feedback loop makes this more than a cache. Bad rules weaken, good rules get stronger, and over time Hermes gets a safer optimization layer.

And because Hermes can also be driven programmatically, the next step is not just intercepting prompts. It is shrinking recurring workflows themselves, including future cron-style optimizers that split work into deterministic pre-processing, a smaller core prompt, and deterministic post-processing.

RuleShield helps Hermes reduce repetitive LLM spend today, and gives it a path toward safer self-optimization tomorrow.
```

## Optional Mid-Monitor Insert

Use these lines only if the Test Monitor cut is included.

```text
The normal Hermes interaction is what the user sees.

This monitor is what RuleShield sees behind the scenes.

Here we can watch candidate rules in shadow mode, see what would have triggered, what actually triggered, and use that to decide what is safe to promote.
```

## TTS Block Split

If you generate voice automatically, split the audio into these blocks:

1. Opening motivation
2. RuleShield core explanation
3. Shadow mode and feedback loop
4. Future direction and closing

Keep the delivery:

- warm
- calm
- low-energy but confident
- slightly rough
- not polished
- not announcer-like

## Live Recording Rules

- Prefer a clean believable take over a perfect one
- Do not debug live on screen
- If the monitor looks noisy, cut to a stable finished run
- Do not depend on a huge live dollar-savings number
- Focus on:
  - repetitive upstream calls
  - shadow mode
  - safe rollout
  - feedback loop
  - future workflow optimization

## Recording Stack

- Screen recording: `Cmd+Shift+5` or Screen Studio
- Editing: CapCut or Descript
- Voice: own voice preferred, TTS acceptable if calm and natural

## Final Pre-Record Checklist

- `GPT-5.1 Mini` active for the main demo
- gateway running
- Hermes path works
- monitor reachable
- opening and closing cards ready
- no irrelevant windows visible
- prompts copied and ready to paste

## Fallback Plan

If the live monitor segment does not behave well:

1. record the Hermes interaction cleanly
2. record a stable finished run separately
3. use the monitor only as a short explanatory insert
4. keep the story centered on safe shadow-mode validation
