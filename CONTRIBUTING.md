# Contributing to RuleShield Hermes

Thank you for your interest in contributing to RuleShield Hermes. This guide walks you through everything you need to get started, from setting up your development environment to submitting a pull request.

All contributions are welcome -- bug fixes, new rule packs, provider adapters, dashboard improvements, and documentation updates. If you are unsure whether your idea fits, open a GitHub Discussion first.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Running the Proxy Locally](#running-the-proxy-locally)
- [Testing Policy](#testing-policy)
  - [Testing Requirements](#testing-requirements)
  - [Running Tests Locally](#running-tests-locally)
  - [Installing Git Hooks](#installing-git-hooks)
  - [New Feature Policy](#new-feature-policy)
  - [Story Matrix](#story-matrix)
- [Adding a Rule Pack](#adding-a-rule-pack)
- [Adding a Provider Adapter](#adding-a-provider-adapter)
- [Contributing to the Dashboard](#contributing-to-the-dashboard)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Commit Message Format](#commit-message-format)
- [Getting Help](#getting-help)

## Development Environment Setup

### Prerequisites

- Python 3.12 or later
- Node.js 18+ and npm 9+ (for the dashboard)
- Git

### Clone and Install

1. Fork the repository on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-username>/ruleshield-hermes.git
cd ruleshield-hermes
```

2. Create and activate a Python virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

3. Install the package in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

4. Install dashboard dependencies:

```bash
cd dashboard && npm install
cd ..
```

You now have the CLI command `ruleshield` available in your terminal.

## Running the Proxy Locally

Initialize a configuration file (creates `~/.ruleshield/config.yaml` if it does not exist):

```bash
ruleshield init
```

Start the proxy server:

```bash
ruleshield start
```

The proxy runs on `http://localhost:8000` by default. Point your LLM client at this URL instead of the upstream provider to route requests through RuleShield.

## Testing Policy

RuleShield uses a three-tier test suite that gates commits, pushes, and releases. Every contributor is expected to run the appropriate suite before submitting code.

### Testing Requirements

| Suite | Command | Gate | What It Covers |
|-------|---------|------|----------------|
| Commit | `bash tests/run-commit-suite.sh` | pre-commit | Smoke tests, proxy startup, core user stories |
| Core | `bash tests/run-core-suite.sh` | pre-push | All user-story tests (Stories A-H) |
| Full | `bash tests/run-full-suite.sh` | release/demo | Extended scenarios and edge cases |

- `run-commit-suite.sh` **must** pass before every commit.
- `run-core-suite.sh` must pass before every push.
- `run-full-suite.sh` is required for release candidates and demo prep.

You can also run the unit test suite directly with pytest:

```bash
pytest        # default run
pytest -v     # verbose output with individual test results
```

### Running Tests Locally

```bash
bash tests/run-commit-suite.sh    # Fast gate (smoke + proxy + core stories)
bash tests/run-core-suite.sh      # Full user stories
bash tests/run-full-suite.sh      # Extended scenarios
```

### Installing Git Hooks

Run this once after cloning to wire up automatic test gates:

```bash
bash tests/install-git-hooks.sh   # Sets up pre-commit + pre-push
```

This configures:
- **pre-commit** runs `tests/run-commit-suite.sh`
- **pre-push** runs `tests/run-core-suite.sh`

If you need to bypass hooks in an emergency:

```bash
SKIP_HOOKS=1 git commit -m "..."  # Emergency bypass
```

### New Feature Policy

- If a feature changes an existing user story, update that story's test.
- If a feature creates a new user-visible workflow, add a new story test.
- Rule: **"No coverage, no commit."**

### Story Matrix

The canonical test inventory lives in [`tests/story-matrix.md`](tests/story-matrix.md). Stories A through H cover the following workflows:

| Story | Workflow |
|-------|----------|
| A | Install |
| B | Gateway |
| C | Passthrough |
| D | Rules |
| E | Health-check |
| F | Monitor |
| G | Feedback |
| H | Rollback |

When you add or modify a story test, update the matrix to keep it in sync.

## Adding a Rule Pack

Rule packs are JSON files stored in the `rules/` directory. Each file contains an array of rule objects. You can look at `rules/default_hermes.json` for a working reference.

### Rule Pack File Format

Create a new file at `rules/<your-domain>.json` with this structure:

```json
[
  {
    "id": "unique_rule_id",
    "name": "Human-Readable Name",
    "description": "What this rule matches and why it exists.",
    "patterns": [
      {"type": "exact", "value": "hello", "field": "last_user_message"},
      {"type": "contains", "value": "greeting", "field": "last_user_message"},
      {"type": "regex", "value": "^hi\\b", "field": "last_user_message"}
    ],
    "conditions": [
      {"type": "max_length", "value": 30, "field": "last_user_message"}
    ],
    "response": {
      "content": "The canned response returned when this rule fires.",
      "model": "ruleshield-rule"
    },
    "confidence": 0.90,
    "priority": 8,
    "enabled": true,
    "hit_count": 0
  }
]
```

### Pattern Types

| Type | Description | Example |
|------|-------------|---------|
| `exact` | Case-insensitive exact match | `"hello"` |
| `contains` | Substring match | `"how are you"` |
| `regex` | Regular expression match | `"^hi\\b"` |

### Guidelines for Rule Packs

- Set `confidence` between 0.0 and 1.0. Higher values mean you are more certain the canned response is appropriate. Use 0.85+ for exact-match rules and 0.70+ for regex-based rules.
- Set `priority` between 1 and 10. Higher-priority rules are evaluated first when multiple rules match.
- Always set `hit_count` to `0` in your submitted file; this value is incremented at runtime.
- Test your rules locally before submitting. Run the proxy and send matching prompts to verify they fire correctly.

## Adding a Provider Adapter

RuleShield routes requests to cost-appropriate models based on complexity scoring. Provider adapters live in `ruleshield/router.py` inside the `SmartRouter` class.

### Adding a New Provider to the Model Map

To add support for a new LLM provider, update the `model_map` dictionary in `SmartRouter.__init__`:

```python
self.model_map: dict[str, dict[str, str | None]] = {
    # ... existing providers ...
    "your_provider": {
        "cheap": "your-provider/small-model",
        "mid": "your-provider/medium-model",
        "premium": None,  # None means keep the original model
    },
}
```

Then update the `_detect_provider` static method to recognize your provider's API URL:

```python
@staticmethod
def _detect_provider(provider_url: str) -> str:
    url = provider_url.lower()
    # ... existing checks ...
    if "yourprovider" in url:
        return "your_provider"
    return "default"
```

### Model Tier Guidelines

| Tier | Purpose | Typical Cost |
|------|---------|--------------|
| `cheap` | Simple queries, greetings, short Q&A | Lowest cost model available |
| `mid` | Moderate complexity, summarization, light analysis | Mid-range model |
| `premium` | Complex code generation, deep analysis, multi-step reasoning | Set to `None` to keep the original requested model |

## Contributing to the Dashboard

The dashboard is a SvelteKit application styled with Tailwind CSS, located in the `dashboard/` directory.

### Running the Dashboard in Development

```bash
cd dashboard
npm run dev
```

The development server starts at `http://localhost:5173` with hot module replacement enabled. The dashboard reads data from the RuleShield proxy API, so make sure the proxy is running on port 8000.

### Dashboard Tech Stack

- **Framework**: SvelteKit (Svelte 5)
- **Styling**: Tailwind CSS 4
- **Build tool**: Vite
- **Type checking**: `npm run check`

### Dashboard Contribution Tips

- Run `npm run check` before committing to catch type errors.
- Keep components small and focused. Place new components in `dashboard/src/`.
- Follow existing Tailwind patterns rather than writing custom CSS.

## Code Style

### Python

This project uses **ruff** for linting and **black** for formatting:

```bash
# Lint
ruff check ruleshield/

# Format
black ruleshield/
```

### TypeScript / Svelte

Use **prettier** for formatting dashboard code:

```bash
cd dashboard
npx prettier --write src/
```

## Pull Request Process

1. **Fork** the repository and create a new branch from `main`:

```bash
git checkout -b feat/your-feature-name
```

2. **Make your changes.** Write tests for new functionality. Update documentation if your change affects user-facing behavior.

3. **Commit** using conventional commit messages (see below).

4. **Push** your branch and open a pull request against `main`:

```bash
git push origin feat/your-feature-name
```

5. **Fill out the PR template.** Describe what changed, why, and how reviewers can test it.

6. **Address review feedback.** A maintainer will review your PR. Once approved, a maintainer will merge it.

### What We Look For in Reviews

- Tests pass and new code is covered by tests.
- Code follows the project style (ruff, black, prettier).
- Documentation is updated for any user-facing changes.
- No secrets, credentials, or API keys are committed.
- Commit history is clean and messages follow conventional commit format.

## Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<optional body>
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process, CI, or tooling changes |

### Examples

```
feat(rules): add healthcare domain rule pack
fix(router): handle empty provider URL without crashing
docs(readme): update quick start for v0.2
refactor(proxy): extract streaming logic into helper
test(router): add edge case tests for complexity scoring
```

## Getting Help

- **Questions**: Open a thread in [GitHub Discussions](https://github.com/banse/RuleShield/discussions).
- **Bug reports**: Use the Bug Report issue template.
- **Feature ideas**: Use the Feature Request issue template.
- **Security issues**: See [SECURITY.md](SECURITY.md) for responsible disclosure instructions. Do not open a public issue for security vulnerabilities.

Thank you for helping make RuleShield Hermes better.
