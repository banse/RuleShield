# Hackathon Generated Voice Runbook

## Goal

Fast fallback workflow for producing the hackathon video with generated narration.

## Suggested Tool Order

1. export audio with TTS
2. record the screen
3. edit video to the audio

This is usually easier than trying to match TTS timing after the cut.

## Minimal Stack

- TTS: ElevenLabs, OpenAI TTS, or another natural voice tool
- Screen capture: `Cmd+Shift+5` or Screen Studio
- Editing: CapCut or Descript

## TTS Input Source

Use:

- [hackathon-recording-voiceover-blocks.txt](./hackathon-recording-voiceover-blocks.txt)

Render each block separately.

## Recommended Render Order

### Block 1

Opening motivation

### Block 2

RuleShield core explanation

### Block 3

Shadow mode and feedback loop

### Block 4

Future direction and closing

### Optional

Mid-monitor insert

## Timing Guidance

- Block 1: calm, slightly slower
- Block 2: steady and clear
- Block 3: slowest block, let the explanation breathe
- Block 4: slightly tighter and more conclusive

## Editing Sequence

1. opening card
2. setup clip
3. Hermes prompt sequence
4. optional monitor cut
5. closing card
6. end frame

## TTS-Specific Rules

- if a block sounds too polished, regenerate only that block
- do not over-process the audio
- do not add dramatic music
- keep pauses between blocks around `0.3s` to `0.7s`
- if a sentence sounds artificial, shorten the sentence instead of forcing it

## Best Use Case

Use generated voice if:

- you are short on time
- you want a cleaner delivery fast
- you already have the screen flow ready

Prefer your own voice if:

- you want maximum authenticity
- the personal motivation should feel more human
- you can record a clean take quickly
