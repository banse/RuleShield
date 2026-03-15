# Add Rule Pack: Customer Support patterns

**Labels:** `good first issue`, `help wanted`, `rules`, `enhancement`

## Description

Create a new rule pack file `rules/customer_support.json` containing 15-20 rules that intercept common customer support conversation patterns. These are messages that appear constantly in support chatbot interactions and have predictable, canned responses -- making them ideal candidates for cost-saving rule interception instead of full LLM calls.

## Why this is useful

Customer support chatbots are one of the highest-volume use cases for LLM APIs. A large percentage of incoming messages are repetitive greetings, hold acknowledgments, FAQ queries, and satisfaction checks. By intercepting these with rules, RuleShield can save significant API costs for teams running support bots. This rule pack makes RuleShield immediately valuable for anyone building a customer support agent.

## Where to look in the codebase

- **Rule format reference:** `rules/default_hermes.json` -- this file shows the exact JSON schema every rule must follow
- **Rule engine (how rules are matched):** `ruleshield/rules.py` -- the `RuleEngine` class, specifically `_score_rule()` and `_conditions_met()`
- **Pattern types supported:** `exact`, `contains`, `startswith`, `regex` (see `_single_pattern_matches()` in `ruleshield/rules.py`)
- **Condition types supported:** `max_length`, `min_length`, `max_messages` (see `_conditions_met()` in `ruleshield/rules.py`)

## What to build

Create `rules/customer_support.json` with rules covering these categories:

1. **Greeting variations** -- "Hi, I need help", "Hello support", "Is anyone there?"
2. **Hold/wait acknowledgments** -- "I'll wait", "Take your time", "No rush"
3. **FAQ triggers** -- "What are your hours?", "How do I reset my password?", "Where is my order?"
4. **Escalation triggers** -- "I want to speak to a manager", "This is unacceptable", "I want a refund"
5. **Satisfaction checks** -- "That solved my problem", "This didn't help", "Thanks, that worked"
6. **Ticket status queries** -- "What's the status of my ticket?", "Any update on my case?"
7. **Closing/goodbye** -- "That's all I needed", "Thanks for your help", "You can close this ticket"

## Rule format example

Each rule in the JSON array must follow this structure:

```json
{
  "id": "cs_greeting_help",
  "name": "Support Greeting - Help Request",
  "description": "Intercepts common customer support greeting patterns where the user asks for help.",
  "patterns": [
    {"type": "contains", "value": "i need help", "field": "last_user_message"},
    {"type": "contains", "value": "can you help", "field": "last_user_message"},
    {"type": "regex", "value": "^(hi|hello|hey),?\\s*(i need|can you|please) help", "field": "last_user_message"}
  ],
  "conditions": [
    {"type": "max_length", "value": 60, "field": "last_user_message"}
  ],
  "response": {
    "content": "Hello! I'm here to help. Could you please describe the issue you're experiencing so I can assist you?",
    "model": "ruleshield-rule"
  },
  "confidence": 0.90,
  "priority": 8,
  "enabled": true,
  "hit_count": 0
}
```

## Acceptance criteria

- [ ] File `rules/customer_support.json` exists and contains valid JSON (an array of rule objects)
- [ ] Contains 15-20 rules covering at least 5 of the 7 categories listed above
- [ ] Every rule has a unique `id` prefixed with `cs_` (e.g., `cs_greeting_help`, `cs_hold_wait`)
- [ ] Every rule includes `id`, `name`, `description`, `patterns`, `conditions`, `response`, `confidence`, `priority`, `enabled`, and `hit_count` fields
- [ ] Pattern `field` values are set to `"last_user_message"`
- [ ] Response `model` values are set to `"ruleshield-rule"`
- [ ] Confidence values are between 0.70 and 0.95 (appropriate for the specificity of each pattern)
- [ ] The file can be loaded by the RuleEngine without errors (test by placing it in `~/.ruleshield/rules/` and running `ruleshield rules`)
- [ ] Rules do not overlap significantly with those already in `rules/default_hermes.json`

## Estimated difficulty

**Easy** -- No Python code changes needed. This is purely a JSON authoring task. You only need to understand the rule format and write patterns for common customer support phrases.

## Helpful links and references

- [RuleShield README](../../README.md) -- Overview of the project and how rules work
- [Default rules file](../../rules/default_hermes.json) -- Reference implementation with 8 rules
- [Rule engine source](../../ruleshield/rules.py) -- Pattern matching logic and scoring weights
- Python regex syntax: https://docs.python.org/3/library/re.html
