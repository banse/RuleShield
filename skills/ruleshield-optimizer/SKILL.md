---
name: ruleshield-optimizer
description: |
  Monitors and optimizes LLM API costs in real-time. Tracks token usage,
  identifies expensive patterns, suggests and applies cost-saving rules,
  and reports savings. Use when discussing costs, optimizing prompts,
  analyzing spending patterns, or when the user mentions "costs", "expensive",
  "optimize", "savings", or "ruleshield".
license: MIT
compatibility: Requires RuleShield proxy running on localhost:8337
metadata:
  author: RuleShield
  version: "1.0"
  category: optimization
---

# RuleShield Cost Optimizer

## When to Use
- User asks about API costs or wants to optimize spending
- Before expensive batch operations (estimate first)
- After completing tasks (show savings report)
- When patterns suggest recurring unnecessary LLM calls

## Available Scripts

### analyze_costs.py
Run to get current session cost analysis:
```bash
python ~/.hermes/skills/ruleshield-optimizer/scripts/analyze_costs.py
```
Returns: total requests, cache/rule/router/LLM breakdown, savings percentage, top rules.

### suggest_rules.py
Run to get rule suggestions based on recent patterns:
```bash
python ~/.hermes/skills/ruleshield-optimizer/scripts/suggest_rules.py
```
Returns: candidate rules extracted from request history, with confidence scores.

### estimate_cost.py
Run before expensive operations to estimate cost:
```bash
python ~/.hermes/skills/ruleshield-optimizer/scripts/estimate_cost.py "prompt text here"
```
Returns: estimated tokens, cost, and whether cache/rules would handle it.

## Self-Optimization
After each session, update MEMORY.md with:
- Rules that worked well (high hit count, high confidence)
- Rules that failed (low confidence, deactivated)
- New patterns discovered
- Total savings achieved

## Integration Notes
- RuleShield proxy must be running: `ruleshield start`
- Stats available via: `curl http://localhost:8337/health`
- Rules directory: ~/.ruleshield/rules/
