# RuleShield: The Agent That Optimizes Itself

## The Problem

Every AI agent has a dirty secret: most of its API calls are wasted money. Run a Hermes Agent for an hour. 60-80% of the calls are repetitive -- greetings, status checks, rephrased questions, confirmations. You pay full premium pricing for every single one.

## The Solution

RuleShield is a transparent proxy that sits between your Hermes Agent and any LLM. It learns your agent's patterns and intercepts the ones that do not need an LLM. Three commands, zero code changes, immediate savings.

```bash
pip install ruleshield-hermes && ruleshield init && ruleshield start
```

## 5 Layers of Intelligence

Not just a cache. Five layers of cost defense, each smarter than the last:

1. **Semantic Cache** -- Exact hash + embedding similarity. Identical or rephrased questions get instant answers. Cost: $0.
2. **SAP-Inspired Rule Engine** -- 75 rules across 4 packs (default, advanced, customer support, coding assistant). Weighted keyword and regex scoring with confidence levels (CONFIRMED/LIKELY/POSSIBLE). Auto-extracts new rules from traffic. Cost: $0.
3. **Template Optimizer** -- Discovers recurring prompt structures, caches fixed portions, sends only variable content to the LLM. Cost: $0.
4. **Hermes Bridge** -- Optional local agent on a cheap model handles medium-complexity tasks. Cost: ~$0.001.
5. **Smart Router** -- Complexity classifier routes across 80+ models to cheap/mid/premium tiers. Simple questions never touch expensive APIs. Cost: varies.

## It Learns From Feedback

Accept or reject any intercepted response. RuleShield adjusts confidence scores using bandit-style updates. Bad rules weaken and die. Good rules grow stronger. The system improves itself with every interaction.

## Deep Hermes Integration

Not just a proxy -- a native Hermes citizen:

- **Hermes Skills**: Ask your agent "show me my savings" or "what rules have you learned?" and it reports back.
- **MCP Server**: 4 tools (get_stats, list_rules, add_rule, get_savings) via JSON-RPC stdio. The agent can query and modify its own optimization layer.
- **Config Integration**: `ruleshield init` patches your Hermes config automatically. No manual setup.

## The Path to Self-Evolution

The feedback loop is step one. RL training stubs are already in place:

- **GRPO/Atropos**: Group Relative Policy Optimization for rule quality
- **DSPy/GEPA**: Guided Evolution for prompt-based agents

Today RuleShield saves costs. Tomorrow it evolves its own optimization strategy. The agent that optimizes itself.

## Proven Results

Tested against the Nous Research Inference API with 4 real-world scenarios:

| Scenario | Savings |
|----------|---------|
| Morning Workflow (greetings, status checks) | **82%** |
| Cron-style Recurring Tasks | **78%** |
| Research Session (mixed complexity) | **52%** |
| Code Review (analysis-heavy) | **47%** |

Setup time: under 2 minutes. Code changes: zero. Response time for cache/rule hits: under 5ms.

## Why Hermes?

Hermes runs autonomously -- planning, executing, iterating. More autonomy means more API calls. More calls means more repetition. More repetition means more savings.

The Hermes Skills system and MCP integration make RuleShield a first-class citizen in the agent ecosystem. The agent does not just save money -- it knows it is saving money, and it can introspect its own optimization layer.

## What Makes This Different

Most cost optimizers are caches. RuleShield is a learning system with 30 commits, 35+ Python modules, and 15 CLI commands:

- 75 rules across 4 domain-specific rule packs
- 80+ models supported (OpenAI, Codex, Anthropic, Google, DeepSeek, Nous/Hermes, Ollama)
- Template Optimizer discovers and caches recurring prompt structures
- Auto Rule Activation promotes shadow-tested rules to production automatically
- Provider Retry with exponential backoff for upstream reliability
- Codex Responses API support for code generation workloads
- Python SDK + Node/TypeScript SDK for drop-in integration
- Docker support (Dockerfile + docker-compose.yml)
- GitHub Actions CI + publish + cost-report workflows
- It integrates natively with the Hermes ecosystem (Skills + MCP)

One command. 47-82% proven savings. 30 commits. An agent that optimizes itself.

---

Built for the [NousResearch Hermes Agent Hackathon](https://github.com/NousResearch) by the RuleShield team.

Source: [GitHub](https://github.com/ruleshield/ruleshield-hermes)
