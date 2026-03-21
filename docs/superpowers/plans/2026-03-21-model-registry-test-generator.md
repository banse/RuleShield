# Model Registry + Test Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a model registry YAML and a Python generator that auto-creates pytest integration tests and bash e2e scripts for each test-capable model.

**Architecture:** `models/registry.yaml` is the single source of truth. `scripts/generate_model_tests.py` reads it + `tests/fixtures/prompts.json`, calls `_get_model_threshold()` for real runtime thresholds, and outputs pytest files to `tests/integration/auto/` and bash stories to `tests/stories/auto/`. Generated files are committed to git. A model suite runner handles e2e execution with gateway lifecycle.

**Tech Stack:** Python 3.9+ stdlib + PyYAML (existing dep), pytest, bash

**Spec:** `docs/superpowers/specs/2026-03-21-model-registry-test-generator-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `models/registry.yaml` | Create | Single source of truth for all models |
| `scripts/generate_model_tests.py` | Create | Generator: reads registry + fixtures, writes tests |
| `scripts/run_model_tests.sh` | Create | E2E batch runner with gateway lifecycle |
| `tests/integration/auto/__init__.py` | Generated | Package marker |
| `tests/integration/auto/conftest.py` | Generated | Shared fixtures for auto tests |
| `tests/integration/auto/test_model_*.py` | Generated | Pytest tests per model |
| `tests/stories/auto/story_model_*.sh` | Generated | Bash e2e scripts per model |
| `tests/integration/test_generator.py` | Create | Tests FOR the generator itself |

---

### Task 1: Model registry + generator tests

**Files:**
- Create: `models/registry.yaml`
- Create: `tests/integration/test_generator.py`

- [ ] **Step 1: Create the registry**

`models/registry.yaml`:
```yaml
version: 1

models:
  - id: "nvidia/nemotron-3-super-120b-a12b:free"
    name: "Nvidia Nemotron 120B"
    provider: openrouter
    tier: free
    confidence_threshold: 0.55
    pricing: {input: 0.0, output: 0.0}
    test_capable: true
    tags: [free, chat, reasoning]

  - id: "minimax/minimax-m2.5:free"
    name: "MiniMax M2.5"
    provider: openrouter
    tier: free
    confidence_threshold: 0.55
    pricing: {input: 0.0, output: 0.0}
    test_capable: true
    tags: [free, chat]

  - id: "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    name: "Nvidia Nemotron Embed 1B"
    provider: openrouter
    tier: free
    confidence_threshold: 0.45
    pricing: {input: 0.0, output: 0.0}
    test_capable: false
    tags: [free, embedding]

  - id: "gpt-4o-mini"
    name: "GPT-4o Mini"
    provider: openai
    tier: cheap
    confidence_threshold: 0.60
    pricing: {input: 0.15, output: 0.60}
    test_capable: true
    tags: [chat]

  - id: "claude-haiku-4-5"
    name: "Claude Haiku 4.5"
    provider: anthropic
    tier: cheap
    confidence_threshold: 0.60
    pricing: {input: 0.80, output: 4.00}
    test_capable: true
    tags: [chat]

  - id: "gpt-4o"
    name: "GPT-4o"
    provider: openai
    tier: mid
    confidence_threshold: 0.75
    pricing: {input: 2.50, output: 10.00}
    test_capable: true
    tags: [chat]

test_generation:
  prompts_per_category: 2
  fixture_file: tests/fixtures/prompts.json
  output_pytest: tests/integration/auto/
  output_stories: tests/stories/auto/
  proxy_port: 8347
```

- [ ] **Step 2: Write tests for the generator**

`tests/integration/test_generator.py`:
```python
"""Tests for the model test generator itself."""

import json
import os
import sys
import tempfile
import shutil

import pytest

# Add scripts dir to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))


class TestRegistryParsing:
    """Test that the generator can parse the registry correctly."""

    def test_load_registry(self):
        from generate_model_tests import load_registry
        registry = load_registry()
        assert "models" in registry
        assert "test_generation" in registry
        assert len(registry["models"]) >= 3

    def test_filter_test_capable(self):
        from generate_model_tests import load_registry, get_test_capable_models
        registry = load_registry()
        models = get_test_capable_models(registry)
        # nvidia embed model has test_capable=false, should be excluded
        ids = [m["id"] for m in models]
        assert "nvidia/llama-nemotron-embed-vl-1b-v2:free" not in ids
        assert "nvidia/nemotron-3-super-120b-a12b:free" in ids

    def test_filter_by_tags(self):
        from generate_model_tests import load_registry, get_test_capable_models
        registry = load_registry()
        models = get_test_capable_models(registry, tags=["free"])
        for m in models:
            assert "free" in m["tags"]

    def test_filter_by_model_ids(self):
        from generate_model_tests import load_registry, get_test_capable_models
        registry = load_registry()
        models = get_test_capable_models(registry, model_ids=["gpt-4o-mini"])
        assert len(models) == 1
        assert models[0]["id"] == "gpt-4o-mini"

    def test_validate_registry_entries(self):
        from generate_model_tests import validate_model_entry
        valid = {"id": "test", "provider": "openai", "tier": "cheap", "test_capable": True}
        assert validate_model_entry(valid) is True

        missing_id = {"provider": "openai", "tier": "cheap", "test_capable": True}
        assert validate_model_entry(missing_id) is False

        bad_tier = {"id": "test", "provider": "openai", "tier": "expensive", "test_capable": True}
        assert validate_model_entry(bad_tier) is False


class TestSafeId:
    """Test model ID to filesystem-safe name conversion."""

    def test_simple(self):
        from generate_model_tests import safe_id
        assert safe_id("gpt-4o-mini") == "gpt_4o_mini"

    def test_with_slash_and_colon(self):
        from generate_model_tests import safe_id
        result = safe_id("nvidia/nemotron-3-super-120b-a12b:free")
        assert "/" not in result
        assert ":" not in result
        assert result == "nvidia_nemotron_3_super_120b_a12b_free"


class TestPromptSelection:
    """Test that prompt fixture selection works."""

    def test_picks_correct_count(self):
        from generate_model_tests import load_fixtures, pick_prompts
        fixtures = load_fixtures()
        prompts = pick_prompts(fixtures, "rule_trigger", count=2)
        assert len(prompts) == 2

    def test_picks_from_category(self):
        from generate_model_tests import load_fixtures, pick_prompts
        fixtures = load_fixtures()
        prompts = pick_prompts(fixtures, "passthrough", count=2)
        assert all("text" in p for p in prompts)


class TestFileGeneration:
    """Test that the generator produces valid files."""

    def test_generates_pytest_file(self):
        from generate_model_tests import generate_pytest_file
        model = {
            "id": "test/model:free", "name": "Test Model",
            "provider": "openrouter", "tier": "free",
            "confidence_threshold": 0.55, "tags": ["free", "chat"],
        }
        content = generate_pytest_file(model, prompts_per_category=1)
        assert "test/model:free" in content
        assert "DO NOT EDIT" in content
        assert "class TestModelRouting" in content
        assert "class TestModelRuleMatch" in content
        assert "def test_rule_trigger_" in content
        assert "def test_passthrough_" in content

    def test_generates_story_file(self):
        from generate_model_tests import generate_story_file
        model = {
            "id": "test/model:free", "name": "Test Model",
            "provider": "openrouter", "tier": "free",
            "confidence_threshold": 0.55, "tags": ["free", "chat"],
        }
        content = generate_story_file(model, prompts_per_category=1)
        assert "test/model:free" in content
        assert "DO NOT EDIT" in content
        assert "curl" in content
        assert "set -euo pipefail" in content

    def test_generates_conftest(self):
        from generate_model_tests import generate_conftest
        free_models = ["nvidia/nemotron-3-super-120b-a12b:free", "minimax/minimax-m2.5:free"]
        content = generate_conftest(free_models)
        assert "allowed_models" in content
        assert "nvidia/nemotron-3-super-120b-a12b:free" in content

    def test_dry_run_writes_nothing(self):
        from generate_model_tests import run_generator
        tmpdir = tempfile.mkdtemp()
        try:
            count = run_generator(
                output_pytest=os.path.join(tmpdir, "pytest"),
                output_stories=os.path.join(tmpdir, "stories"),
                dry_run=True,
            )
            assert count > 0
            assert not os.path.exists(os.path.join(tmpdir, "pytest"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_full_generation(self):
        from generate_model_tests import run_generator
        tmpdir = tempfile.mkdtemp()
        try:
            pytest_dir = os.path.join(tmpdir, "pytest")
            stories_dir = os.path.join(tmpdir, "stories")
            count = run_generator(
                output_pytest=pytest_dir,
                output_stories=stories_dir,
            )
            assert count >= 2  # at least nemotron + minimax
            # Check pytest files exist
            assert os.path.exists(os.path.join(pytest_dir, "__init__.py"))
            assert os.path.exists(os.path.join(pytest_dir, "conftest.py"))
            py_files = [f for f in os.listdir(pytest_dir) if f.startswith("test_model_")]
            assert len(py_files) >= 2
            # Check story files exist
            sh_files = [f for f in os.listdir(stories_dir) if f.startswith("story_model_")]
            assert len(sh_files) >= 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
```

- [ ] **Step 3: Run tests — expect failure (generator doesn't exist yet)**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest tests/integration/test_generator.py -v 2>&1 | tail -5`
Expected: FAIL — `ModuleNotFoundError: No module named 'generate_model_tests'`

- [ ] **Step 4: Commit**

```bash
git add models/registry.yaml tests/integration/test_generator.py
git commit -m "test: add model registry and generator tests (failing)"
```

---

### Task 2: Implement the generator

**Files:**
- Create: `scripts/generate_model_tests.py`

- [ ] **Step 1: Create the generator**

`scripts/generate_model_tests.py`:
```python
#!/usr/bin/env python3
"""Generate model-specific test files from models/registry.yaml.

Reads the model registry and test fixtures, generates:
  - pytest integration tests at tests/integration/auto/test_model_*.py
  - bash e2e story scripts at tests/stories/auto/story_model_*.sh

Usage:
    python scripts/generate_model_tests.py                     # all test_capable models
    python scripts/generate_model_tests.py --models m1,m2      # specific models
    python scripts/generate_model_tests.py --tags free          # filter by tag
    python scripts/generate_model_tests.py --dry-run            # preview only
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from string import Template
from typing import Any

# Resolve project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY_PATH = PROJECT_ROOT / "models" / "registry.yaml"
FIXTURES_PATH = PROJECT_ROOT / "tests" / "fixtures" / "prompts.json"

# Add engine to path for rulecore, and project root for ruleshield
sys.path.insert(0, str(PROJECT_ROOT / "engine"))
sys.path.insert(0, str(PROJECT_ROOT))

VALID_TIERS = {"free", "cheap", "mid", "premium"}
REQUIRED_FIELDS = {"id", "provider", "tier", "test_capable"}


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------

def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load the model registry YAML file."""
    path = path or REGISTRY_PATH
    try:
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: simple YAML subset parser
        return _parse_simple_yaml(path)


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Minimal YAML parser for the registry subset."""
    with open(path, "r") as f:
        text = f.read()
    # Use json as intermediate: convert YAML-like to JSON
    # This handles our specific registry format only
    import re
    lines = text.split("\n")
    result: dict[str, Any] = {}
    current_list: list | None = None
    current_list_key: str = ""
    current_item: dict[str, Any] | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level key: value
        if not line.startswith(" ") and ":" in stripped:
            if current_item and current_list is not None:
                current_list.append(current_item)
                current_item = None
            key, _, val = stripped.partition(":")
            val = val.strip()
            if val:
                result[key.strip()] = _yaml_value(val)
            else:
                current_list_key = key.strip()
                current_list = []
                result[current_list_key] = current_list
            continue

        # List item start
        if stripped.startswith("- "):
            if current_item and current_list is not None:
                current_list.append(current_item)
            if ":" in stripped[2:]:
                current_item = {}
                key, _, val = stripped[2:].partition(":")
                current_item[key.strip().strip('"')] = _yaml_value(val.strip())
            else:
                if current_list is not None:
                    current_list.append(_yaml_value(stripped[2:]))
                current_item = None
            continue

        # Dict continuation inside list item
        if current_item is not None and ":" in stripped:
            key, _, val = stripped.partition(":")
            current_item[key.strip().strip('"')] = _yaml_value(val.strip())

    if current_item and current_list is not None:
        current_list.append(current_item)

    return result


def _yaml_value(s: str) -> Any:
    """Parse a YAML scalar/inline value."""
    s = s.strip().strip('"').strip("'")
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s.startswith("{") and s.endswith("}"):
        # Inline dict: {input: 0.0, output: 0.0}
        pairs = s[1:-1].split(",")
        d = {}
        for pair in pairs:
            if ":" in pair:
                k, v = pair.split(":", 1)
                d[k.strip()] = _yaml_value(v.strip())
        return d
    if s.startswith("[") and s.endswith("]"):
        # Inline list: [free, chat]
        items = s[1:-1].split(",")
        return [_yaml_value(i) for i in items]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


# ---------------------------------------------------------------------------
# Filtering and validation
# ---------------------------------------------------------------------------

def validate_model_entry(model: dict[str, Any]) -> bool:
    """Validate a model registry entry."""
    for field in REQUIRED_FIELDS:
        if field not in model:
            return False
    if model.get("tier") not in VALID_TIERS:
        return False
    return True


def get_test_capable_models(
    registry: dict[str, Any],
    tags: list[str] | None = None,
    model_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter registry to test-capable models, optionally by tags or IDs."""
    models = []
    for m in registry.get("models", []):
        if not validate_model_entry(m):
            print(f"WARNING: skipping invalid model entry: {m.get('id', '<no id>')}", file=sys.stderr)
            continue
        if not m.get("test_capable", False):
            continue
        if model_ids and m["id"] not in model_ids:
            continue
        if tags:
            model_tags = m.get("tags", [])
            if not any(t in model_tags for t in tags):
                continue
        models.append(m)
    return models


def safe_id(model_id: str) -> str:
    """Convert model ID to filesystem-safe name."""
    return model_id.replace("/", "_").replace(":", "_").replace(".", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def load_fixtures(path: Path | None = None) -> dict[str, Any]:
    """Load prompt fixtures."""
    path = path or FIXTURES_PATH
    with open(path, "r") as f:
        return json.load(f)


def pick_prompts(fixtures: dict[str, Any], category: str, count: int = 2) -> list[dict[str, str]]:
    """Pick prompts from a fixture category."""
    cat = fixtures.get(category, {})
    prompts = cat.get("prompts", [])
    return prompts[:count]


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

def get_runtime_threshold(model_id: str) -> float:
    """Get the real runtime confidence threshold for a model."""
    try:
        from ruleshield.rules import _get_model_threshold
        return _get_model_threshold(model_id)
    except Exception:
        return 0.70  # default


def generate_conftest(free_model_ids: list[str]) -> str:
    """Generate shared conftest.py for auto tests."""
    allowed = ",\n            ".join(f'"{m}"' for m in free_model_ids)
    default = free_model_ids[0] if free_model_ids else ""
    return f'''"""Shared fixtures for auto-generated model tests."""
# Generated by scripts/generate_model_tests.py from models/registry.yaml
# DO NOT EDIT — regenerate with: python scripts/generate_model_tests.py

import asyncio
import json
import os
import pytest
from ruleshield.rules import RuleEngine
from ruleshield.router import SmartRouter


@pytest.fixture
def engine():
    """RuleEngine loaded with bundled default rules."""
    e = RuleEngine()
    asyncio.run(e.init())
    return e


@pytest.fixture
def free_router():
    """SmartRouter with free model enforcement enabled."""
    return SmartRouter(config={{
        "free_model_enforcement": {{
            "enabled": True,
            "allowed_models": [
            {allowed}
            ],
            "default_model": "{default}",
        }}
    }})


@pytest.fixture
def prompts():
    """Load test prompt fixtures."""
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "fixtures", "prompts.json"
    )
    with open(fixture_path) as f:
        return json.load(f)
'''


def generate_pytest_file(model: dict[str, Any], prompts_per_category: int = 2) -> str:
    """Generate a pytest integration test file for a model."""
    mid = model["id"]
    sid = safe_id(mid)
    threshold = get_runtime_threshold(mid)
    tier = model.get("tier", "cheap")
    provider = model.get("provider", "unknown")
    name = model.get("name", mid)

    fixtures = load_fixtures()
    rule_prompts = pick_prompts(fixtures, "rule_trigger", prompts_per_category)
    pass_prompts = pick_prompts(fixtures, "passthrough", prompts_per_category)
    temporal_prompts = pick_prompts(fixtures, "temporal", 1)

    # Build test methods for rule triggers
    rule_tests = ""
    for i, p in enumerate(rule_prompts):
        text = p["text"]
        expected = p.get("expected_rule", "")
        rule_tests += f'''
    def test_rule_trigger_{safe_id(text)}(self, engine):
        """Rule should fire for: {text}"""
        result = engine.match("{text}", model=MODEL_ID)
        assert result is not None, "Expected rule match for \\"{text}\\""
        assert result["rule_id"] != ""
'''

    # Build test methods for passthrough
    pass_tests = ""
    for i, p in enumerate(pass_prompts):
        text = p["text"].replace('"', '\\"')
        pass_tests += f'''
    def test_passthrough_{i}(self, engine):
        """No rule should match: {text[:50]}"""
        result = engine.match("{text}", model=MODEL_ID)
        assert result is None, "Expected no rule match for passthrough prompt"
'''

    # Temporal test
    temporal_text = temporal_prompts[0]["text"] if temporal_prompts else "What time is it now?"
    temporal_text_escaped = temporal_text.replace('"', '\\"')

    # Free-tier specific tests
    free_tests = ""
    if tier == "free":
        free_tests = f'''
    def test_free_enforcement_allows_model(self, free_router):
        """Router allowlist should accept this free model."""
        result = free_router.route(
            "hello", None, MODEL_ID,
            provider_url="https://openrouter.ai/api/v1",
        )
        # Should either not route (already free) or route to same/another free model
        if result["routed"]:
            assert "FREE ENFORCEMENT" not in result["reason"] or result["model"] == MODEL_ID

    def test_free_enforcement_blocks_expensive(self, free_router):
        """Router should block expensive models and replace with free."""
        result = free_router.route(
            "hello", None, "gpt-5.3-codex",
            provider_url="https://openrouter.ai/api/v1",
        )
        assert result["routed"] is True
'''

    return f'''"""Auto-generated integration test for {mid}"""
# Generated by scripts/generate_model_tests.py from models/registry.yaml
# DO NOT EDIT — regenerate with: python scripts/generate_model_tests.py

import pytest

MODEL_ID = "{mid}"
MODEL_NAME = "{name}"
PROVIDER = "{provider}"
TIER = "{tier}"
CONFIDENCE_THRESHOLD = {threshold}


class TestModelRouting:
    """Verify routing and threshold behavior for {name}."""

    def test_confidence_threshold_applied(self, engine):
        """Engine should respect confidence threshold for this model."""
        from ruleshield.rules import _get_model_threshold
        threshold = _get_model_threshold(MODEL_ID)
        assert threshold == pytest.approx(CONFIDENCE_THRESHOLD, abs=0.01)
{free_tests}

class TestModelRuleMatch:
    """Verify rule matching works correctly with this model."""
{rule_tests}{pass_tests}
    def test_temporal_passthrough(self, engine):
        """Temporal queries should NOT match rules (always go to LLM)."""
        result = engine.match("{temporal_text_escaped}", model=MODEL_ID)
        assert result is None, "Temporal query should not match any rule"
'''


def generate_story_file(model: dict[str, Any], prompts_per_category: int = 2) -> str:
    """Generate a bash e2e story script for a model."""
    mid = model["id"]
    name = model.get("name", mid)

    fixtures = load_fixtures()
    rule_prompts = pick_prompts(fixtures, "rule_trigger", prompts_per_category)
    pass_prompts = pick_prompts(fixtures, "passthrough", prompts_per_category)

    total = len(rule_prompts) + len(pass_prompts)
    tests = ""
    idx = 0

    for p in rule_prompts:
        idx += 1
        text = p["text"]
        tests += f'''
# Test {idx}/{total}: Rule trigger — expect ruleshield-rule
echo "  [{idx}/{total}] Rule trigger: {text}"
RESP="$(curl -sf "$PROXY_URL/v1/chat/completions" \\
  -H "Content-Type: application/json" -H "Authorization: Bearer sk-test" \\
  -d '{{"model":"'"$MODEL"'","messages":[{{"role":"user","content":"{text}"}}]}}')"
echo "$RESP" | "$PYTHON_BIN" -c "import sys,json; d=json.load(sys.stdin); assert d['model']=='ruleshield-rule', f'Expected rule hit, got {{d[\\\"model\\\"]}}'; print('    PASS')"
'''

    for p in pass_prompts:
        idx += 1
        text = p["text"].replace("'", "'\\''")
        tests += f'''
# Test {idx}/{total}: Passthrough — expect choices in response
echo "  [{idx}/{total}] Passthrough: {text[:40]}..."
RESP="$(curl -sf "$PROXY_URL/v1/chat/completions" \\
  -H "Content-Type: application/json" -H "Authorization: Bearer sk-test" \\
  -d '{{"model":"'"$MODEL"'","messages":[{{"role":"user","content":"{text}"}}]}}')"
echo "$RESP" | "$PYTHON_BIN" -c "import sys,json; d=json.load(sys.stdin); assert 'choices' in d; print('    PASS')"
'''

    return f'''#!/usr/bin/env bash
# Auto-generated e2e test for {mid}
# Generated by scripts/generate_model_tests.py from models/registry.yaml
# DO NOT EDIT — regenerate with: python scripts/generate_model_tests.py

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"
PYTHON_BIN="${{PYTHON_BIN:-$(ruleshield_python_bin)}}"

MODEL="{mid}"
PROXY_URL="${{RULESHIELD_PROXY_URL:-http://127.0.0.1:8347}}"

echo "=== E2E: {name} ($MODEL) ==="
{tests}
echo "=== ALL PASSED: {name} ==="
'''


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def run_generator(
    registry_path: Path | None = None,
    output_pytest: str | None = None,
    output_stories: str | None = None,
    model_ids: list[str] | None = None,
    tags: list[str] | None = None,
    dry_run: bool = False,
    prompts_per_category: int = 2,
) -> int:
    """Run the full generation pipeline. Returns number of models processed."""
    registry = load_registry(registry_path)
    gen_config = registry.get("test_generation", {})
    prompts_per_category = gen_config.get("prompts_per_category", prompts_per_category)

    output_pytest = output_pytest or str(PROJECT_ROOT / gen_config.get("output_pytest", "tests/integration/auto/"))
    output_stories = output_stories or str(PROJECT_ROOT / gen_config.get("output_stories", "tests/stories/auto/"))

    models = get_test_capable_models(registry, tags=tags, model_ids=model_ids)
    if not models:
        print("No test-capable models found matching filters.", file=sys.stderr)
        return 0

    # Collect free model IDs for conftest
    free_ids = [m["id"] for m in models if m.get("tier") == "free"]

    if dry_run:
        print(f"Would generate tests for {len(models)} models:")
        for m in models:
            print(f"  - {m['id']} ({m.get('name', '')}) [{m.get('tier', '')}]")
        print(f"Output pytest: {output_pytest}")
        print(f"Output stories: {output_stories}")
        return len(models)

    # Create output dirs
    os.makedirs(output_pytest, exist_ok=True)
    os.makedirs(output_stories, exist_ok=True)

    # Write __init__.py
    init_path = os.path.join(output_pytest, "__init__.py")
    with open(init_path, "w") as f:
        f.write("")

    # Write conftest.py
    conftest_path = os.path.join(output_pytest, "conftest.py")
    with open(conftest_path, "w") as f:
        f.write(generate_conftest(free_ids))

    # Generate per-model files
    for model in models:
        sid = safe_id(model["id"])

        # Pytest file
        pytest_content = generate_pytest_file(model, prompts_per_category)
        pytest_path = os.path.join(output_pytest, f"test_model_{sid}.py")
        with open(pytest_path, "w") as f:
            f.write(pytest_content)

        # Story file
        story_content = generate_story_file(model, prompts_per_category)
        story_path = os.path.join(output_stories, f"story_model_{sid}.sh")
        with open(story_path, "w") as f:
            f.write(story_content)
        os.chmod(story_path, os.stat(story_path).st_mode | stat.S_IEXEC)

        print(f"Generated: {model['id']} -> {pytest_path}, {story_path}")

    print(f"\nGenerated tests for {len(models)} models.")
    return len(models)


def main():
    parser = argparse.ArgumentParser(description="Generate model test scripts from registry")
    parser.add_argument("--models", type=str, help="Comma-separated model IDs")
    parser.add_argument("--tags", type=str, help="Comma-separated tags to filter")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--registry", type=str, help="Path to registry YAML")
    args = parser.parse_args()

    model_ids = args.models.split(",") if args.models else None
    tags_list = args.tags.split(",") if args.tags else None
    registry_path = Path(args.registry) if args.registry else None

    count = run_generator(
        registry_path=registry_path,
        model_ids=model_ids,
        tags=tags_list,
        dry_run=args.dry_run,
    )
    if count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run generator tests**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest tests/integration/test_generator.py -v`
Expected: ALL pass

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_model_tests.py
git commit -m "feat: add model test generator script"
```

---

### Task 3: Run the generator and commit generated files

**Files:**
- Generated: `tests/integration/auto/*`
- Generated: `tests/stories/auto/*`

- [ ] **Step 1: Run the generator**

```bash
PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 scripts/generate_model_tests.py
```

Expected output:
```
Generated: nvidia/nemotron-3-super-120b-a12b:free -> tests/integration/auto/test_model_nvidia_nemotron_...py, tests/stories/auto/story_model_nvidia_nemotron_...sh
Generated: minimax/minimax-m2.5:free -> tests/integration/auto/test_model_minimax_minimax_m2_5_free.py, ...
Generated: gpt-4o-mini -> tests/integration/auto/test_model_gpt_4o_mini.py, ...
...
Generated tests for 5 models.
```

- [ ] **Step 2: Run the generated pytest tests**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest tests/integration/auto/ -v`
Expected: ALL pass

- [ ] **Step 3: Run all existing tests to verify no regressions**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest tests/ -v 2>&1 | tail -10`
Expected: Only pre-existing asyncio failures

- [ ] **Step 4: Commit generated files**

```bash
git add tests/integration/auto/ tests/stories/auto/
git commit -m "feat: auto-generated model tests for 5 models from registry"
```

---

### Task 4: Model suite runner + Training Monitor hint

**Files:**
- Create: `scripts/run_model_tests.sh`
- Modify: `ruleshield/prompt_training.py` (add ~5 lines)

- [ ] **Step 1: Create the model suite runner**

`scripts/run_model_tests.sh`:
```bash
#!/usr/bin/env bash
# Run all auto-generated model e2e tests.
# Assumes RuleShield proxy is already running (or starts it).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STORIES_DIR="$ROOT_DIR/tests/stories/auto"

if [ ! -d "$STORIES_DIR" ] || [ -z "$(ls -A "$STORIES_DIR"/story_model_*.sh 2>/dev/null)" ]; then
    echo "No auto-generated model stories found in $STORIES_DIR"
    echo "Run: python scripts/generate_model_tests.py"
    exit 1
fi

PASS=0
FAIL=0
TOTAL=0

for script in "$STORIES_DIR"/story_model_*.sh; do
    TOTAL=$((TOTAL + 1))
    echo ""
    echo "=== [$TOTAL] Running: $(basename "$script") ==="
    if bash "$script"; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        echo "FAILED: $script"
    fi
done

echo ""
echo "========================================="
echo "Model Suite Results: $PASS passed, $FAIL failed (of $TOTAL)"
echo "========================================="
[ "$FAIL" -eq 0 ]
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/run_model_tests.sh
```

- [ ] **Step 3: Add Training Monitor hint**

In `ruleshield/prompt_training.py`, find the method that collects the model name from the run. Add after the model is resolved (search for `self.model` or `model` assignment in the run method):

```python
# Check if model is in registry
try:
    import yaml
    registry_path = Path(__file__).resolve().parent.parent / "models" / "registry.yaml"
    if registry_path.exists():
        with open(registry_path) as f:
            registry = yaml.safe_load(f)
        known_ids = {m["id"] for m in registry.get("models", [])}
        if model and model not in known_ids:
            logger.info(
                "Model %s not in models/registry.yaml. "
                "Add it and run: python scripts/generate_model_tests.py --models %s",
                model, model,
            )
except Exception:
    pass  # non-critical, don't break training
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest tests/ -v 2>&1 | tail -10`
Expected: ALL pass (except pre-existing)

- [ ] **Step 5: Commit**

```bash
git add scripts/run_model_tests.sh ruleshield/prompt_training.py
git commit -m "feat: add model suite runner and training monitor registry hint"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full rulecore test suite**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest engine/rulecore/tests/ -v 2>&1 | tail -5`
Expected: 81 passed

- [ ] **Step 2: Run full RuleShield + auto test suite**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -m pytest tests/ -v 2>&1 | tail -10`
Expected: All pass except pre-existing asyncio failures

- [ ] **Step 3: Test the generator dry-run**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 scripts/generate_model_tests.py --dry-run`
Expected: Lists all test-capable models without writing files

- [ ] **Step 4: Test tag filtering**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 scripts/generate_model_tests.py --tags free --dry-run`
Expected: Lists only free models (nemotron, minimax)

- [ ] **Step 5: Verify no ruleshield imports in generator break standalone use**

Run: `PYTHONPATH=/Library/Vibes/fun/ideas/engine python3 -c "from scripts.generate_model_tests import load_registry; r = load_registry(); print(len(r['models']), 'models loaded')"`
Expected: `6 models loaded`

- [ ] **Step 6: Push**

```bash
git push
```
