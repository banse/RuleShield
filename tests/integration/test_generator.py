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
