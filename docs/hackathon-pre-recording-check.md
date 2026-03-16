# Hackathon Pre-Recording Check

## Window Layout

Keep the desktop simple.

Use only these windows:

1. Terminal
2. Hermes
3. Browser on the Test Monitor

Optional:

4. a second browser tab with landing/slides only for reference

## What Each Window Is For

### Terminal

Use terminal only for the short setup proof:

```bash
ruleshield init --hermes
ruleshield start
```

Do not linger on terminal output.

### Hermes

Hermes is the main hero window.

Use a fresh session and send exactly:

1. `hi`
2. `read README.md and summarize it briefly`
3. `ok thanks`
4. `bye`

### Test Monitor

Open:

[http://localhost:5174/test-monitor](http://localhost:5174/test-monitor)

Keep visible:

- `RuleShield Live`
- `Prompt/Antwort Monitor`

Use profile:

- `GPT-5.1 Mini (OpenAI OAuth)`

## Recording Order

1. terminal setup
2. switch to Hermes
3. send the 4 prompts
4. cut to Test Monitor
5. add title cards in editing, not live

## What Should Not Be Visible

- DevTools
- Finder windows with private files
- irrelevant browser tabs
- noisy logs before the demo starts
- old broken runs if they weaken the story

## Hermes Preparation

- start from a clean visible state
- make the window large enough to read comfortably
- avoid extra panels unless they help the story
- do not show messy prior chat context

## Test Monitor Preparation

- keep the correct profile selected
- if live data looks unstable, use a stable finished run
- do not scroll around too much during recording
- use it as a short explanatory cut, not the main scene

## Audio Strategy

Preferred:

- record screen first
- add voiceover after

If using TTS:

- render in 4 blocks
- keep the voice warm, calm, and understated

## Editing Strategy

Do not force one perfect take.

Record these as separate clips:

1. setup
2. Hermes interaction
3. monitor cut
4. closing

Then assemble them in the editor.
