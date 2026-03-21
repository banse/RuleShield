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
