# RuleShield Rule Operations Guide

This guide explains how to operate the current `RuleShield Hermes` rules engine during realistic day-in-the-life testing.

It is written for the practical questions that come up during live usage:

- how to run a realistic shadow-mode test
- what to watch during a multi-hour prompt session
- how to interpret shadow metrics correctly
- when to tune a rule
- when to pause a rule
- when a candidate is ready for promotion

This is the operational companion to the technical reference in [rules-engine.md](/Users/banse/codex/hermes/ruleshield-hermes/docs/rules-engine.md).

## Testing Philosophy

The most useful test setup is not a synthetic benchmark. It is a normal Hermes work session with realistic prompts.

That means:

- natural greetings
- quick acknowledgments
- short follow-up confirmations
- occasional clarification requests
- file and command workflow prompts
- normal interruptions like `wait`, `skip`, `undo`

The engine should be evaluated against real assistant behavior, not against idealized template responses.

## Recommended Test Modes

There are three useful modes.

### 1. Infrastructure smoke test

Use this only to verify plumbing:

- proxy is active
- dashboard is alive
- shadow logs appear
- candidate hits are counted

Good prompts:

- `hello`
- `ok`
- `shadow model probe beta 88`

### 2. Focused prompt family test

Use this to calibrate one rule family:

- greetings
- acknowledgments
- confirmations
- file workflow

This is useful when one rule is already underperforming and you want a clean batch of evidence.

### 3. Day-in-the-life test

This is the most realistic mode.

Use Hermes normally for a few hours and let RuleShield observe:

- varied short prompts
- natural switching between English and German if that is how you actually work
- real task flow instead of one repeated prompt

This is the best way to see whether the rule pack is production-worthy.

## Recommended Setup for a Day-in-the-Life Test

### Proxy

Run RuleShield with shadow mode enabled on the local proxy:

```bash
env RULESHIELD_SHADOW_MODE=true /Users/banse/codex/hermes/ruleshield-hermes/.venv/bin/python -m ruleshield.proxy
```

### Hermes

Run Hermes through the proxy:

```bash
HERMES_CODEX_BASE_URL=http://127.0.0.1:8337 hermes
```

### Dashboard

For the minimal live board:

[http://127.0.0.1:5174/shadow-lab](http://127.0.0.1:5174/shadow-lab)

Main dashboard:

[http://127.0.0.1:5174/](http://127.0.0.1:5174/)

Test monitor:

[http://127.0.0.1:5174/test-monitor](http://127.0.0.1:5174/test-monitor)

## Before Starting a Fresh Test Window

If you want a clean measurement window, clear old shadow comparisons first.

Current reliable direct reset:

```bash
sqlite3 /Users/banse/.ruleshield/cache.db "DELETE FROM shadow_log;"
```

After reset, verify:

```bash
curl -s 'http://127.0.0.1:8337/api/shadow?recent=25'
```

Expected:

- `total_comparisons = 0`
- no `entries`
- no `tune_examples`

## What to Watch During the Session

### 1. Total comparisons

This tells you whether the engine is seeing enough relevant traffic.

If comparisons stay near zero:

- your prompts are not hitting rules
- or shadow mode is not wired into the active request path

For `/test-monitor`, remember:

- `RuleShield Live` is run-scoped and does not show global fallback values.
- A health-check run can legitimately show `0` triggered rules and `0` would-trigger values.
- This usually means all prompts were passthrough and no matching rule family fired.

### 2. Per-rule comparison counts

This tells you which rules are actually involved in your day-to-day usage.

Operationally, these rules matter most:

- rules with many shadow comparisons
- rules with many live hits
- rules with repeated low similarity

If you need global totals, use API endpoints directly:

- `/api/shadow`
- `/api/rules`
- `/api/rule-events`

### 3. Average similarity

This is useful, but only in context.

Do not treat it as a pure “correctness” score.

Low similarity may mean:

- wrong answer
- wrong language
- too much verbosity difference
- same intent but different wording

### 4. Confidence movement

This is often more important than raw similarity.

If a rule keeps drifting toward `0.5`, the feedback loop is telling you:

- the current response shape is not production-safe

### 5. Tune examples

These are the highest-signal operational artifact.

They show:

- prompt
- rule response
- real Hermes/LLM response

This is the primary material for rule tuning.

## How to Interpret Shadow Results

### Good signal

If the rule response and Hermes response are close in:

- intent
- tone
- language
- length

then you should expect similarity to climb.

### Misleading low score

A low score does not always mean the rule is fundamentally wrong.

Typical misleading cases:

- English rule vs German Hermes response
- same meaning, different phrasing
- one answer includes emoji and one does not
- one answer is much shorter but still equally useful

Example:

- Rule: `Hello! I'm here and ready to help. What can I do for you today?`
- Hermes: `Hello! What can I help you with today?`

This is actually a good semantic match, but the current lexical overlap metric will still score it only moderately.

### Truly bad signal

Treat a rule as genuinely weak when:

- multiple examples show different intent, not just different phrasing
- the rule response is consistently longer, stiffer, or off-tone
- confidence keeps dropping despite many similar prompts

## Realistic Expectations by Rule Family

Not all rule families should be evaluated the same way.

### Greetings

These should usually be:

- short
- natural
- close to the assistant’s normal style

If they are verbose or overly formal, shadow similarity will suffer quickly.

### Acknowledgments

These are tricky.

Prompts like:

- `ok`
- `thanks`
- `got it`

are very short, so even small tone differences matter a lot.

These rules are useful, but they are also easy to overfit badly.

### Clarification rules

These are often strong candidate rules.

If the assistant usually responds to unknown labels with:

- “Could you clarify what you mean?”

then a shadow candidate in that style can be production-worthy.

### Workflow rules

Examples:

- `show diff`
- `undo`
- `retry`
- `save`

These should be evaluated not only for text similarity but also for whether they fit the real tool workflow of the agent.

## When to Tune a Rule

Tune a rule when all of the following are true:

1. it is being hit regularly
2. the intent is roughly correct
3. the response shape is consistently off

Typical tuning moves:

- shorten the response
- match the dominant language
- reduce stiffness or boilerplate
- make the phrasing more aligned with Hermes’ normal voice

Do not tune just because of one bad sample.

Look for a pattern across multiple examples.

## When to Pause a Rule

Pause a production rule when:

1. confidence is drifting toward `0.5`
2. tune examples show repeated intent mismatch
3. the rule is harming live realism more than it is saving cost

Operationally, pausing is better than forcing a weak rule to stay active.

A paused rule can later return as:

- a better production rule
- or a candidate rule for shadow-only retraining

## When to Keep a Rule Live Despite Imperfect Similarity

Sometimes a rule is useful even if similarity is not high.

This is only acceptable when:

- intent is consistently correct
- the response is short and harmless
- the wording differences do not affect user outcome

Be careful here.

The current feedback loop is conservative for a reason.

If a rule is truly safe, it should survive repeated real traffic over time.

## When a Candidate Rule Is Ready for Promotion

Current promotion logic expects:

- at least `10` shadow comparisons
- average similarity `>= 0.80`
- feedback acceptance rate `>= 0.85`
  - or no explicit feedback yet

Operationally, you should also ask:

1. Is the rule solving a real recurring pattern?
2. Is the response style aligned with current Hermes behavior?
3. Would I be comfortable with this being returned live without another model call?

If the answer to any of these is no, leave it as candidate.

## Suggested Day-in-the-Life Prompt Mix

To get realistic signal, let your session include a broad mix like:

### Lightweight conversational prompts

- `hello`
- `hi`
- `thanks`
- `ok`
- `wait`
- `next`

### Workflow prompts

- `show diff`
- `undo that`
- `retry`
- `save`
- `read the file`

### Clarification prompts

- unknown project names
- weird labels
- short ambiguous tags

### Real task prompts

- normal coding or research instructions
- file operations
- debugging flow

The engine is most useful when tested under mixed traffic, not one isolated prompt family.

## Recommended Session Review Rhythm

For a multi-hour session, do not stare at the dashboard constantly.

A good rhythm is:

### Every 20-30 minutes

Check:

- top shadow entries
- confidence drift
- new tune examples

### Every 1-2 hours

Decide:

- which rules need tuning
- which rules should be paused
- which candidate rules are collecting meaningful evidence

### At the end of the session

Review:

- top underperformers
- rules with most hits
- candidate rules with best shadow quality

## Minimal Review Checklist

After a day-in-the-life test, ask:

1. Which rules were hit often?
2. Which rules had repeated poor shadow results?
3. Were the bad results caused by intent mismatch or style mismatch?
4. Which candidate rules gathered enough evidence to keep iterating?
5. Which production rules should be softened, shortened, or paused?

## Practical Decision Rules

### Tune

Tune a rule if:

- it hits often
- intent is right
- style is off

### Pause

Pause a rule if:

- confidence keeps falling
- repeated examples show wrong-fit responses

### Promote

Promote a candidate if:

- it sees real recurring traffic
- shadow comparisons are strong
- it feels safe as a live response

### Ignore for now

Ignore a rule if:

- it barely gets traffic
- evidence is too sparse

## What This Guide Optimizes For

This operating model is designed to optimize:

- realistic live testing
- safe rule evolution
- evidence-based tuning
- low-risk promotion

The right goal is not to maximize raw rule count.

The right goal is:

- fewer
- better
- more realistic
- production-safe rules

that match how Hermes actually behaves during a normal working day.
