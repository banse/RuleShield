"""Integration test: load condition_tree rules from JSON, match through full pipeline."""

import asyncio
import json
import os
import tempfile
import shutil

import pytest
from ruleshield.rules import RuleEngine


@pytest.fixture
def rules_dir():
    """Create a temp directory with example nested rules."""
    tmpdir = tempfile.mkdtemp(prefix="ruleshield-test-")
    src = os.path.join(os.path.dirname(__file__), "..", "..", "rules", "examples_nested.json")
    shutil.copy2(src, os.path.join(tmpdir, "examples_nested.json"))
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def engine(rules_dir):
    """Create a RuleEngine loaded from the temp rules dir."""
    e = RuleEngine(rules_dir=rules_dir)
    asyncio.run(e.init())
    return e


class TestConditionTreeLoading:
    def test_tree_rules_loaded(self, engine):
        assert len(engine.rules) == 3
        ids = [r["id"] for r in engine.rules]
        assert "nested_git_help" in ids
        assert "nested_short_greeting" in ids
        assert "nested_code_review" in ids

    def test_git_help_matches(self, engine):
        result = engine.match("how do I git push to remote?", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "nested_git_help"

    def test_git_help_blocked_by_ci(self, engine):
        result = engine.match("setup github actions for git push", model="gpt-4o-mini")
        assert result is None

    def test_short_greeting_matches(self, engine):
        result = engine.match("hi", model="gpt-4o-mini")
        assert result is not None
        assert result["rule_id"] == "nested_short_greeting"

    def test_greeting_question_blocked(self, engine):
        result = engine.match("hi?", model="gpt-4o-mini")
        # "hi?" fails: exact("hi") != "hi?" in the any-node, so no score.
        assert result is None

    def test_get_active_rules_shows_tree_flag(self, engine):
        active = engine.get_active_rules()
        tree_rule = next(r for r in active if r["id"] == "nested_git_help")
        assert tree_rule["has_condition_tree"] is True
        assert tree_rule["pattern_count"] == 0
