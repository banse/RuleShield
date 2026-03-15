# RuleShield for Hermes Agent

> What if your AI agent could learn to optimize -- and eventually evolve -- itself?

[![PyPI version](https://img.shields.io/pypi/v/ruleshield)](https://pypi.org/project/ruleshield/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/banse/ruleshield-hermes/actions/workflows/ci.yml/badge.svg)](https://github.com/banse/ruleshield-hermes/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

RuleShield is an intelligent LLM cost optimizer that sits between your Hermes Agent and any LLM provider. It learns your agent's patterns through 4 layers of defense, routes requests to the cheapest capable model, and improves its own rules through a feedback loop. Tested against the Nous Research API: **47-82% cost savings proven**.

## Quick Start

```bash
pip install ruleshield-hermes
ruleshield init
ruleshield start
```

Point your Hermes Agent at `http://127.0.0.1:8337`. No code changes. Costs drop immediately.

### Drop-in SDK Wrapper

```python
# Before (standard OpenAI):
from openai import OpenAI
client = OpenAI()

# After (one line change):
from ruleshield.sdk import OpenAI
client = OpenAI()

# Everything else stays exactly the same
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
```

### TypeScript / Node.js

```typescript
// Before:
import OpenAI from 'openai';

// After:
import { OpenAI } from '@ruleshield/sdk';

// Everything else stays the same
const client = new OpenAI();
```

Install: `npm install @ruleshield/sdk openai`

## Dashboard

RuleShield includes a real-time web dashboard, landing page, and documentation site.

```
Terminal 1: ruleshield start
Terminal 2: cd dashboard && npm run dev
```

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | localhost:5174 | Real-time stats, requests, rules |
| Rule Explorer | localhost:5174/rules | Toggle rules on/off, sort, filter |
| Landing Page | localhost:5174/landing | Product marketing page |
| Documentation | localhost:5174/docs | Architecture, API, Hermes guide |
| Slides | localhost:5174/slides | 10-slide hackathon presentation |

## Supported Models (80+)

| Provider | Models | Tier |
|----------|--------|------|
| OpenAI | GPT-4o, GPT-4.1, GPT-4.5, o3, o4-mini | Mid-Premium |
| OpenAI Codex | GPT-5.3-codex, GPT-5.2-codex, GPT-5.1-codex-mini/max | Mid |
| Anthropic | Claude Opus 4.6, Sonnet 4.6, Haiku 4.5 | All tiers |
| Google | Gemini 2.5 Pro, Gemini 2.0 Flash | Mid-Cheap |
| DeepSeek | DeepSeek-V3, DeepSeek-R1 | Cheap-Mid |
| Nous/Hermes | Hermes 4-14B/70B/405B | All tiers |
| Open Source | Llama 3.x, Qwen 2.5/3, Mistral, Phi-4, Gemma 2 | Cheap-Mid |
| Ollama (local) | Llama 3.x, Mistral, Phi, Gemma, CodeLlama | Free (local) |

Model-aware confidence thresholds automatically adjust rule aggressiveness per model tier.

## How It Works: 5-Layer Architecture

Every request passes through five layers. The first layer that can handle it wins.

```
Request -> Cache -> Rules -> Template Optimizer -> Hermes Bridge -> Smart Router -> Upstream LLM
           $0       $0       $0 (trimming)        ~$0.001 (opt.)   auto-routing     full price
                      |                                                  |
                 Feedback Loop (accept/reject -> auto-promote)    Provider Retry
                      |
                 RL/GEPA stubs (future: self-evolution)
```

### Layer 1: Semantic Cache ($0)

Two-tier caching that catches identical and near-identical requests.

- **Exact match**: SHA-256 hash lookup. Same prompt = instant answer.
- **Semantic match**: Sentence-transformer embeddings with cosine similarity (threshold 0.92). "What's the weather?" and "Tell me the weather" both hit cache.

### Layer 2: SAP-Inspired Rule Engine ($0)

Pattern matching with weighted scoring, inspired by enterprise rule systems.

- 75 rules across 4 packs: 8 default, 12 advanced, 30 customer support, 25 coding assistant
- Pattern types: `exact`, `contains`, `startswith`, `regex`
- SAP-inspired weighted keyword and regex scoring
- Confidence levels: CONFIRMED / LIKELY / POSSIBLE
- Auto-extraction generates new rules from observed traffic
- Rules fire in under 2ms

```json
{
  "id": "greeting",
  "patterns": [
    {"type": "contains", "value": "hello", "field": "last_user_message"},
    {"type": "regex", "value": "^(hi|hey|greetings)", "field": "last_user_message"}
  ],
  "response": {"content": "Hello! How can I help you?"},
  "confidence": 0.95,
  "priority": 10
}
```

### Layer 3: Hermes Bridge (~$0.001, optional)

A local Hermes Agent instance running on a cheap model that handles medium-complexity requests. Requests too complex for rules but too simple for premium models get routed here first.

### Layer 4: Smart Model Router (auto-pricing)

Complexity classifier analyzes each request and routes to the cheapest capable model.

| Complexity | Routing | Cost |
|------------|---------|------|
| Simple (score 1-3) | Cheap model (e.g., GPT-4o-mini) | ~$0.001 |
| Medium (score 4-7) | Mid-tier model | ~$0.005 |
| Complex (score 8-10) | Premium model (e.g., Opus) | ~$0.015 |

The classifier uses prompt length, message count, keyword analysis, and question type to score complexity on a 1-10 scale.

## Feedback Loop: Self-Improving Rules

RuleShield learns from your feedback. Accept or reject any intercepted response, and the system adjusts confidence scores using bandit-style updates.

```bash
# Review recent interceptions
ruleshield feedback

# Accept a good interception (boosts rule confidence)
ruleshield feedback --accept <request-id>

# Reject a bad one (lowers confidence, rule eventually disables itself)
ruleshield feedback --reject <request-id>
```

Rules that consistently get rejected lose confidence and stop firing. Rules that get accepted grow stronger. The system improves itself over time.

## Hermes Integration

RuleShield integrates with the Hermes ecosystem at three levels.

### Hermes Skills

Ask your agent about its own efficiency:

- **"Show me my cost savings"** -- Full breakdown: requests, cache hits, rule hits, router decisions, dollars saved.
- **"What rules have you learned?"** -- Lists active rules with hit counts and confidence scores.

### MCP Server

Four tools available via JSON-RPC stdio for deep agent integration:

| Tool | Description |
|------|-------------|
| `get_stats` | Current session statistics and savings |
| `list_rules` | All active rules with metadata |
| `add_rule` | Register a new rule programmatically |
| `get_savings` | Cost breakdown and savings percentage |

### Config Integration

RuleShield patches your Hermes config automatically. Run `ruleshield init` and your `model.base_url` points to the proxy. No manual editing.

## Live Dashboard

Real-time terminal dashboard built with Rich:

```
+------------------------------------------------------------------+
|  RuleShield for Hermes Agent                        LIVE  02:34  |
|                                                                  |
|  Requests    Cache     Rules     Bridge    Router    Savings      |
|    147        63         31        12        41       82%         |
|              43%        21%        8%       28%                   |
|                                                                  |
|  Cost Savings                                                    |
|  Without RuleShield:  $4.20                                      |
|  With RuleShield:     $0.76                                      |
|  Saved: $3.44  ████████████████████████░░░░░░  82%               |
|                                                                  |
|  Recent Requests                                                 |
|   #147  "what is the status of..."   CACHE    $0.00   $0.034     |
|   #146  "hello"                      RULE     $0.00   $0.012     |
|   #145  "summarize this code..."     ROUTER   $0.001  $0.015     |
|   #144  "analyze this dataset..."    LLM      $0.045  -          |
+------------------------------------------------------------------+
```

## Prompt Trimming

RuleShield splits requests into known and unknown parts. System prompts that repeat every call get cached separately. Only the novel user content counts toward API costs.

## RL Training Interface (Stubs)

The feedback loop lays the groundwork for reinforcement learning. Interface stubs are in place for:

- **GRPO/Atropos**: Group Relative Policy Optimization for rule quality
- **DSPy/GEPA**: Guided Evolution for Prompt-based Agents

These are not yet active but define the path toward an agent that evolves its own optimization strategy.

## Results

Tested against the Nous Research Inference API with 4 real-world demo scenarios:

| Scenario | Savings | Resolution Mix |
|----------|---------|----------------|
| Morning Workflow (greetings, status) | 82% | Mostly cache + rules |
| Code Review (analysis tasks) | 47% | Router saves on simple reviews |
| Research Session (complex queries) | 52% | Bridge + Router split |
| Cron-style Recurring Tasks | 78% | Cache dominates |

| Metric | Value |
|--------|-------|
| Total cost reduction | 47-82% depending on workload |
| Cache/rule response time | <5ms |
| LLM passthrough overhead | negligible |
| Setup time | <2 minutes |
| Code changes required | zero |

## CLI Reference (15 commands)

```bash
ruleshield init              # Set up config + rules + Hermes integration
ruleshield start             # Start the proxy (with live dashboard)
ruleshield stop              # Stop the proxy
ruleshield stats             # Show current session savings
ruleshield rules             # List active rules with hit counts
ruleshield feedback          # Review and rate recent interceptions
ruleshield shadow-stats      # Shadow mode comparison statistics
ruleshield analyze-crons     # Identify recurring prompts for optimization
ruleshield test-slack        # Verify Slack webhook configuration
ruleshield promote-rule      # Promote a shadow rule to active
ruleshield auto-promote      # Auto-promote all qualifying shadow rules
ruleshield discover-templates # Discover recurring prompt templates
ruleshield templates         # List active templates and hit rates
ruleshield wrapped           # Generate a wrapped-style summary report
```

## Configuration

All settings live in `~/.ruleshield/config.yaml`:

```yaml
provider_url: https://api.openai.com    # upstream LLM provider
api_key: ""                              # or set RULESHIELD_API_KEY env var
port: 8337                               # proxy port
cache_enabled: true
rules_enabled: true
router_enabled: true                     # smart model routing
hermes_bridge_enabled: false             # optional Hermes Bridge
hermes_bridge_model: claude-haiku-4-5    # model for bridge requests
shadow_mode: false                       # log only, no interceptions
prompt_trimming_enabled: true            # template optimization
max_retries: 3                           # provider retry attempts
slack_webhook: ""                        # Slack notifications
```

Override any setting with `RULESHIELD_` prefix:

```bash
RULESHIELD_ROUTER_ENABLED=true RULESHIELD_SHADOW_MODE=false ruleshield start
```

## Project Structure

```
ruleshield-hermes/
  ruleshield/
    proxy.py           # FastAPI proxy server (OpenAI-compatible, streaming)
    cache.py           # 2-layer cache (hash + semantic)
    rules.py           # SAP-inspired pattern matching engine
    router.py          # Smart model router + complexity classifier
    hermes_bridge.py   # Local Hermes Agent bridge
    feedback.py        # Bandit-style feedback loop
    extractor.py       # Auto rule extraction from traffic
    metrics.py         # Real-time dashboard + metrics
    config.py          # Configuration management
    cli.py             # CLI entry point
    template_optimizer.py  # Prompt template discovery and optimization
    sdk.py             # Python SDK (drop-in OpenAI replacement)
  rules/
    default_hermes.json       # 8 default rules
    advanced_hermes.json      # 12 advanced rules
    customer_support.json     # 30 customer support rules
    coding_assistant.json     # 25 coding assistant rules
  sdk-node/            # Node/TypeScript SDK
  skills/
    cost_report/       # Hermes Skill: cost savings report
    show_rules/        # Hermes Skill: list active rules
  demo/
    scenarios/         # 4 tested demo scenarios
  Dockerfile           # Container support
  docker-compose.yml   # Multi-service orchestration
  .github/workflows/   # CI + publish + cost-report actions
```

## Roadmap

- [x] 5-layer architecture (cache, rules, template optimizer, bridge, router)
- [x] Smart model routing with complexity classification (80+ models)
- [x] Feedback loop with bandit-style confidence updates
- [x] Hermes Skills and config integration
- [x] Prompt trimming
- [x] MCP Server (4 tools)
- [x] SAP-inspired weighted scoring
- [x] Web-based dashboard with real-time stats
- [x] Template Optimizer with auto-discovery
- [x] Auto Rule Activation (shadow -> production)
- [x] Provider Retry with exponential backoff
- [x] Codex Responses API support
- [x] Python SDK + Node/TypeScript SDK
- [x] Docker support (Dockerfile + docker-compose.yml)
- [x] GitHub Actions CI + publish + cost-report
- [x] 4 rule packs (75 rules total)
- [x] Wrapped summary reports
- [ ] Rule marketplace (share rules across teams)
- [ ] Full RL training loop (GRPO/Atropos)
- [ ] Cost budgets and alerts

## Community

- [Contributing Guide](CONTRIBUTING.md) -- How to set up dev environment and contribute
- [Code of Conduct](CODE_OF_CONDUCT.md) -- Our community standards
- [Security Policy](SECURITY.md) -- How to report vulnerabilities
- [Good First Issues](https://github.com/banse/ruleshield-hermes/labels/good%20first%20issue) -- Great starting points for contributors

### Ways to contribute

- **Rule Packs**: Create new domain-specific rule packs (DevOps, data science, legal)
- **Provider Adapters**: Add support for additional LLM providers (Groq, Together, Fireworks)
- **Dashboard Plugins**: New widgets, charts, themes
- **Integration Guides**: AutoGPT, LlamaIndex, and more
- **Translations**: CLI and dashboard in other languages

## Built With

- [FastAPI](https://fastapi.tiangolo.com/) -- Async Python proxy
- [SvelteKit](https://kit.svelte.dev/) -- Dashboard and docs
- [Tailwind CSS](https://tailwindcss.com/) -- Styling
- [sentence-transformers](https://www.sbert.net/) -- Semantic cache embeddings
- [Rich](https://rich.readthedocs.io/) -- Terminal dashboard
- [Click](https://click.palletsprojects.com/) -- CLI framework

Built for the [Hermes Agent Hackathon](https://x.com/NousResearch) by NousResearch.

## License

MIT -- see [LICENSE](LICENSE)

## Built for the Hermes Agent Hackathon

Built for the [NousResearch Hermes Agent Hackathon](https://github.com/NousResearch).

The idea: what if the agent itself could learn to reduce its own costs, improve its own rules, and eventually evolve its own optimization strategy? Not by being less capable -- by being smarter about when it needs the LLM at all.

RuleShield does not make your agent dumber. It makes it self-aware.
