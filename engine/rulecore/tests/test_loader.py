"""Tests for rulecore loader."""
import json
import os
import tempfile
import shutil

import pytest
from rulecore.loader import load_rules, save_state, apply_persisted_state


@pytest.fixture
def rules_dir():
    tmpdir = tempfile.mkdtemp(prefix="rulecore-test-")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def _write_rules(rules_dir, filename, rules):
    with open(os.path.join(rules_dir, filename), "w") as f:
        json.dump(rules, f)


class TestLoadRules:
    def test_loads_flat_rules(self, rules_dir):
        _write_rules(rules_dir, "test.json", [
            {"id": "r1", "patterns": [{"type": "exact", "value": "hi"}], "response": {"content": "hello"}, "priority": 5},
            {"id": "r2", "patterns": [{"type": "exact", "value": "bye"}], "response": {"content": "goodbye"}, "priority": 10},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 2
        assert rules[0]["id"] == "r2"

    def test_loads_condition_tree_rules(self, rules_dir):
        _write_rules(rules_dir, "tree.json", [
            {"id": "t1", "condition_tree": {"all": [{"type": "contains", "value": "hi", "field": "text"}]}, "response": {"content": "hello"}},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 1
        assert rules[0]["id"] == "t1"

    def test_skips_invalid_tree(self, rules_dir):
        _write_rules(rules_dir, "bad.json", [
            {"id": "bad", "condition_tree": {"all": []}, "response": {"content": "x"}},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 0

    def test_skips_rules_without_patterns_or_tree(self, rules_dir):
        _write_rules(rules_dir, "nopat.json", [
            {"id": "nopat", "response": {"content": "x"}},
        ])
        rules = load_rules(rules_dir)
        assert len(rules) == 0

    def test_loads_candidates(self, rules_dir):
        cand_dir = os.path.join(rules_dir, "candidates")
        os.makedirs(cand_dir)
        _write_rules(cand_dir, "cand.json", [
            {"id": "c1", "patterns": [{"type": "exact", "value": "test"}], "response": {"content": "ok"}},
        ])
        rules = load_rules(rules_dir)
        assert rules[0]["deployment"] == "candidate"

    def test_empty_dir_with_no_bundled(self, rules_dir):
        rules = load_rules(rules_dir)
        assert rules == []


class TestStatePersistence:
    def test_save_and_load(self, rules_dir):
        rules = [{"id": "r1", "hit_count": 5, "confidence": 0.8, "enabled": True, "deployment": "production"}]
        save_state(rules, rules_dir)
        state_path = os.path.join(rules_dir, "_state.json")
        assert os.path.exists(state_path)

        fresh_rules = [{"id": "r1", "hit_count": 0, "confidence": 1.0, "enabled": True}]
        apply_persisted_state(fresh_rules, rules_dir)
        assert fresh_rules[0]["hit_count"] == 5
        assert fresh_rules[0]["confidence"] == 0.8
