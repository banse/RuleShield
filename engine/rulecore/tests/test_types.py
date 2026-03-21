"""Tests for rulecore data types."""
from rulecore.types import ScoringConfig, MatchResult, FeedbackEntry, RuleEvent


class TestScoringConfig:
    def test_defaults(self):
        cfg = ScoringConfig()
        assert cfg.keyword_weight == 1.0
        assert cfg.pattern_weight == 2.0
        assert cfg.exact_weight == 5.0
        assert cfg.condition_weight == 0.5
        assert cfg.min_score == 1.5

    def test_custom_values(self):
        cfg = ScoringConfig(keyword_weight=2.0, min_score=3.0)
        assert cfg.keyword_weight == 2.0
        assert cfg.min_score == 3.0
        assert cfg.pattern_weight == 2.0


class TestMatchResult:
    def test_creation(self):
        r = MatchResult(
            rule_id="test", rule_name="Test", response={"content": "hi"},
            confidence=0.9, match_score=3.0, confidence_level="LIKELY",
            matched_keywords=["hello"], matched_patterns=[],
        )
        assert r.rule_id == "test"
        assert r.deployment == "production"


class TestFeedbackEntry:
    def test_accept(self):
        e = FeedbackEntry(rule_id="r1", prompt="hi", feedback_type="accept")
        assert e.correction is None

    def test_reject_with_correction(self):
        e = FeedbackEntry(rule_id="r1", prompt="hi", feedback_type="reject", correction="bye")
        assert e.correction == "bye"


class TestRuleEvent:
    def test_defaults(self):
        ev = RuleEvent(rule_id="r1", event_type="confidence_update")
        assert ev.details == {}
        assert ev.direction is None
