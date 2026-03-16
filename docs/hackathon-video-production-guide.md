# Hackathon Video Production Guide

**Goal**: Produce a clean Hermes Hackathon demo video with minimal risk and minimal editing overhead.

## Production Principle

Keep the production stack simple.

The strongest hackathon video for RuleShield is not the fanciest one.
It is the one that is:

- clear
- believable
- short
- easy to follow
- visibly real

## Recommended Stack

## Option A: Fastest and safest

- **Screen recording**: macOS Screenshot Tool (`Cmd+Shift+5`)
- **Voiceover**: your own recorded voice
- **Editing**: CapCut or Descript
- **Visual framing**: existing RuleShield pages, no custom motion graphics required

This should be the default.

## Option B: Slightly more polished

- **Screen recording**: Screen Studio
- **Voiceover**: your own recorded voice
- **Editing**: CapCut, Descript, or Screen Studio export
- **Visual framing**: existing RuleShield pages plus one opening and one closing frame

Use this only if the tooling is already familiar.

## Option C: Synthetic voice fallback

If you do not want to record your own voice:

- ElevenLabs
- OpenAI TTS
- Edge TTS

But this should be the fallback, not the default.

For this story, a human voice is usually stronger.

## Recommended Asset Structure

Use only three visual types:

1. **Opening frame**
   - title
   - one-line problem framing

2. **Main demo recording**
   - terminal setup
   - test monitor
   - health check
   - Hermes user run
   - RuleShield Live payoff

3. **Closing frame**
   - one-line conclusion
   - optional three bullets

That is enough.

## Suggested Scene Breakdown

## Scene 1: Opening frame

**Length**: 5-8 seconds

Suggested text:

- RuleShield
- Cut repetitive LLM spend. Validate safely in shadow mode.

Optional subtext:

- Built for the Hermes Hackathon

## Scene 2: Terminal setup

**Length**: 8-12 seconds

Show:

```bash
ruleshield init --hermes
ruleshield start
```

This is enough.
Do not dwell on terminal output.

## Scene 3: Test Monitor

**Length**: 35-45 seconds

Show:

- health check run
- Hermes-user run
- prompt/response log
- RuleShield Live panel

This is the core of the video.

## Scene 4: Future direction

**Length**: 8-12 seconds

Keep the same page or briefly cut to a static frame.

Mention:

- Hermes Python API
- recurring workflows
- future Cron Optimizer / Replacer path

## Scene 5: Closing frame

**Length**: 4-6 seconds

Suggested text:

- Reduce repetitive LLM spend
- Validate safely in shadow mode
- Build toward workflow optimization

## Voice Strategy

## Best choice

Use your own voice.

Why:

- more authentic
- better fit for the personal motivation
- more convincing for hackathon judges

## How to record

Two good approaches:

### Approach 1: Live narration

- record screen and voice at the same time

Good if:

- you are comfortable speaking while demoing

Risk:

- more likely to need re-takes

### Approach 2: Voiceover after recording

- first record the screen cleanly
- then record the voiceover over the cut

This is the recommended approach.

Why:

- more control
- easier retakes
- cleaner pacing

## Editing Guidance

Keep editing light.

Allowed:

- trim dead time
- speed up tiny waiting gaps if needed
- add 1-2 title cards
- crop slightly for focus
- improve audio levels

Avoid:

- heavy animations
- long intros
- constant zoom effects
- too many transitions
- overproduced marketing style

## Layout Guidance

If you want a title card or closing card, keep them minimal.

Suggested opening card:

- Title: `RuleShield`
- Subtitle: `Cut repetitive LLM spend. Validate safely in shadow mode.`

Suggested closing card:

- `Safe rollout`
- `Visible savings`
- `Path to workflow optimization`

## Audio Guidance

- keep background music optional
- if used, keep it very quiet
- prioritize voice clarity over polish
- normalize volume before export

## Export Guidance

- aspect ratio: `16:9`
- resolution: `1080p`
- target length: `75-90 seconds`
- hard cap: `120 seconds`

## Recommended Workflow

1. prepare the stable demo environment
2. open the exact pages in advance
3. record the main screen flow once or twice
4. pick the cleanest take
5. record voiceover from the final script
6. add opening and closing frame
7. export and review once

## Pre-Recording Checklist

- gateway stable
- dashboard stable
- chosen profile stable
- active run path verified
- backup screenshots ready
- voiceover text open and easy to read

## Final Recommendation

For this hackathon, use:

- macOS screen recording or Screen Studio
- your own voice
- CapCut or Descript for editing
- existing RuleShield UI as the main visual asset

That gives the best balance of:

- speed
- clarity
- credibility
- low production risk
