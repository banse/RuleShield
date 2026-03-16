# Hackathon Shot List

## Goal

A simple shot-by-shot recording plan for the final Hermes Hackathon demo.

## Shot 1: Opening

- **Screen**: opening slide or landing/slides page
- **Duration**: 5-8s
- **Voiceover**: opening motivation
- **Purpose**: personal context and immediate transition into RuleShield

## Shot 2: Setup

- **Screen**: terminal
- **Show**:

```bash
ruleshield init --hermes
ruleshield start
```

- **Duration**: 8-12s
- **Purpose**: prove the setup path is real without over-focusing on it

## Shot 3: Hermes Prompt 1

- **Screen**: Hermes
- **Prompt**:

```text
hi
```

- **Duration**: 6-8s
- **Purpose**: obvious repetitive interaction

## Shot 4: Hermes Prompt 2

- **Screen**: Hermes
- **Prompt**:

```text
read README.md and summarize it briefly
```

- **Duration**: 10-15s
- **Purpose**: one clearly real LLM / agent task

## Shot 5: Hermes Prompt 3

- **Screen**: Hermes
- **Prompt**:

```text
ok thanks
```

- **Duration**: 4-6s
- **Purpose**: another obvious repetitive prompt family

## Shot 6: Hermes Prompt 4

- **Screen**: Hermes
- **Prompt**:

```text
bye
```

- **Duration**: 4-6s
- **Purpose**: clean finish for the normal user flow

## Shot 7: RuleShield Monitor

- **Screen**: Test Monitor / RuleShield Live
- **Duration**: 10-15s
- **Show**:
  - active or finished run
  - RuleShield Live
  - Prompt/Antwort Monitor
- **Purpose**: show what RuleShield sees behind the scenes

## Shot 8: Future Direction

- **Screen**: monitor or simple static frame
- **Duration**: 8-12s
- **Purpose**: Python API workflows, recurring tasks, Cron Optimizer / Replacer

## Shot 9: Closing

- **Screen**: closing slide
- **Duration**: 4-6s
- **Suggested text**:
  - Safe rollout
  - Lower repetitive LLM spend
  - Path to workflow optimization

## Recommended Prompt Set

Use exactly these prompts for the main Hermes interaction:

1. `hi`
2. `read README.md and summarize it briefly`
3. `ok thanks`
4. `bye`

## Avoid

- `status`
- `show me what changed`
- `undo that`
- long or tool-heavy debugging prompts
- live debugging during recording

## Fallback

If the live monitor is noisy:

- record the Hermes interaction cleanly
- cut to a stable finished run or screenshot for the monitor segment
- keep the narration focused on shadow mode and safe rollout
