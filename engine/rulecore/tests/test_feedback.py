"""Tests for rulecore FeedbackManager."""
import os
import tempfile
import shutil

import pytest
from rulecore.engine import RuleEngine
from rulecore.store import JsonFileFeedbackStore
from rulecore.feedback import FeedbackManager


@pytest.fixture
def tmpdir():
    d = tempfile.mkdtemp(prefix="rulecore-fb-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def engine():
    e = RuleEngine()
    e.rules = [
        {"id": "r1", "name": "Rule 1", "confidence": 0.8, "enabled": True, "deployment": "production",
         "patterns": [{"type": "exact", "value": "hi"}], "response": {"content": "hello"}},
        {"id": "r2", "name": "Rule 2", "confidence": 0.55, "enabled": True, "deployment": "candidate",
         "patterns": [{"type": "exact", "value": "bye"}], "response": {"content": "goodbye"}},
    ]
    return e


@pytest.fixture
def feedback(engine, tmpdir):
    store = JsonFileFeedbackStore(os.path.join(tmpdir, "fb.json"))
    return FeedbackManager(engine=engine, store=store)


class TestAcceptReject:
    def test_accept_increases_confidence(self, engine, feedback):
        old = engine.rules[0]["confidence"]
        feedback.accept("r1", "hello")
        new = engine.rules[0]["confidence"]
        assert new > old

    def test_reject_decreases_confidence(self, engine, feedback):
        old = engine.rules[0]["confidence"]
        feedback.reject("r1", "hello")
        new = engine.rules[0]["confidence"]
        assert new < old

    def test_ema_formula_accept(self, engine, feedback):
        feedback.accept("r1", "test")
        assert abs(engine.rules[0]["confidence"] - 0.802) < 0.001

    def test_ema_formula_reject(self, engine, feedback):
        feedback.reject("r1", "test")
        assert abs(engine.rules[0]["confidence"] - 0.76) < 0.001

    def test_reject_with_correction(self, engine, feedback):
        feedback.reject("r1", "hello", correction="should say goodbye")
        entries = feedback.store.load_feedback(rule_id="r1")
        assert entries[0].correction == "should say goodbye"


class TestAutoDeactivation:
    def test_deactivates_below_threshold(self, engine, feedback):
        engine.rules[0]["confidence"] = 0.06
        feedback.reject("r1", "test")
        assert engine.rules[0]["enabled"] is False

    def test_keeps_above_threshold(self, engine, feedback):
        feedback.reject("r1", "test")
        assert engine.rules[0]["enabled"] is True


class TestAnalytics:
    def test_underperforming_rules(self, engine, feedback):
        for i in range(3):
            feedback.accept("r1", f"prompt{i}")
        for i in range(7):
            feedback.reject("r1", f"prompt{i}")
        result = feedback.get_underperforming_rules(min_feedback=5)
        assert len(result) == 1
        assert result[0]["rule_id"] == "r1"
        assert result[0]["acceptance_rate"] == 0.3

    def test_performance_by_category(self, engine, feedback):
        feedback.accept("r1", "test1")
        feedback.accept("r1", "test2")
        feedback.reject("r1", "test3")
        result = feedback.get_performance_by_category()
        assert "r1" in result
        assert result["r1"]["total"] == 3
        assert result["r1"]["accepted"] == 2

    def test_check_promotions(self, engine, feedback):
        engine.rules[1]["confidence"] = 0.99
        promoted = feedback.check_promotions()
        assert "r2" in promoted
        assert engine.rules[1]["deployment"] == "production"
