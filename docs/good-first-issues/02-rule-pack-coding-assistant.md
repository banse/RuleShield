# Add Rule Pack: Coding Assistant patterns

**Labels:** `good first issue`, `help wanted`, `rules`, `enhancement`

## Description

Create a new rule pack file `rules/coding_assistant.json` containing 15-20 rules that intercept common patterns seen in coding assistant interactions. Developers using AI coding assistants frequently send short, predictable messages like "run the tests", "build the project", or "yes, commit that" -- these can be intercepted with deterministic responses instead of burning expensive LLM tokens.

## Why this is useful

Coding assistants (Cursor, Copilot Chat, Hermes Agent, Aider, etc.) are among the fastest-growing LLM use cases. Developers often use terse, repetitive commands during coding sessions. A purpose-built rule pack for this use case can dramatically cut costs for teams running AI-assisted development workflows, especially when the same developer uses the same phrases dozens of times per day.

## Where to look in the codebase

- **Rule format reference:** `rules/default_hermes.json` -- shows the exact JSON schema for rules
- **Advanced rules example:** `rules/hermes_advanced.json` -- shows more complex pattern combinations
- **Rule engine:** `ruleshield/rules.py` -- the `RuleEngine` class handles matching logic
- **Pattern types:** `exact`, `contains`, `startswith`, `regex` (defined in `_single_pattern_matches()`)
- **Condition types:** `max_length`, `min_length`, `max_messages` (defined in `_conditions_met()`)

## What to build

Create `rules/coding_assistant.json` with rules covering these categories:

1. **Build commands** -- "build it", "run the build", "compile", "make"
2. **Test runners** -- "run the tests", "run tests", "test it", "pytest", "npm test"
3. **Git operations** -- "commit this", "push it", "git status", "create a PR"
4. **File operations** -- "save it", "create the file", "delete that file"
5. **Linting/formatting** -- "lint it", "format the code", "fix the formatting"
6. **Approval/confirmation** -- "looks good", "ship it", "LGTM", "approve"
7. **Navigation** -- "show me the file", "open that", "go to the function"
8. **Debugging acknowledgments** -- "that fixed it", "still broken", "same error"

## Rule format example

```json
{
  "id": "code_run_tests",
  "name": "Run Tests Command",
  "description": "Intercepts short requests to run tests during a coding session.",
  "patterns": [
    {"type": "exact", "value": "run the tests", "field": "last_user_message"},
    {"type": "exact", "value": "run tests", "field": "last_user_message"},
    {"type": "exact", "value": "test it", "field": "last_user_message"},
    {"type": "regex", "value": "^(run|execute)\\s+(the\\s+)?tests?$", "field": "last_user_message"},
    {"type": "exact", "value": "pytest", "field": "last_user_message"},
    {"type": "exact", "value": "npm test", "field": "last_user_message"}
  ],
  "conditions": [
    {"type": "max_length", "value": 25, "field": "last_user_message"}
  ],
  "response": {
    "content": "Running the test suite now. I'll report back with the results.",
    "model": "ruleshield-rule"
  },
  "confidence": 0.88,
  "priority": 7,
  "enabled": true,
  "hit_count": 0
}
```

## Acceptance criteria

- [ ] File `rules/coding_assistant.json` exists and contains valid JSON (an array of rule objects)
- [ ] Contains 15-20 rules covering at least 5 of the 8 categories listed above
- [ ] Every rule has a unique `id` prefixed with `code_` (e.g., `code_run_tests`, `code_git_commit`)
- [ ] Every rule includes all required fields: `id`, `name`, `description`, `patterns`, `conditions`, `response`, `confidence`, `priority`, `enabled`, `hit_count`
- [ ] Pattern `field` values are set to `"last_user_message"`
- [ ] Response `model` values are set to `"ruleshield-rule"`
- [ ] Confidence values are between 0.70 and 0.95
- [ ] `max_length` conditions are appropriately set (coding commands tend to be very short, so 15-40 chars is typical)
- [ ] The file loads without errors when placed in the rules directory
- [ ] Rules do not duplicate rules already in `rules/default_hermes.json`

## Estimated difficulty

**Easy** -- JSON authoring only. No Python changes needed. Familiarity with common developer workflows is the main requirement.

## Helpful links and references

- [Default rules file](../../rules/default_hermes.json) -- Reference implementation
- [Rule engine source](../../ruleshield/rules.py) -- How patterns are scored and matched
- [Router source](../../ruleshield/router.py) -- How complexity scoring works (for context on what kinds of prompts are "simple")
