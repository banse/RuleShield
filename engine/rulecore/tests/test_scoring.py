"""Tests for rulecore scoring."""
from rulecore.scoring import compute_confidence_level


class TestComputeConfidenceLevel:
    def test_confirmed(self):
        assert compute_confidence_level(5.0, True, True) == "CONFIRMED"

    def test_confirmed_requires_both(self):
        assert compute_confidence_level(5.0, True, False) == "LIKELY"
        assert compute_confidence_level(5.0, False, True) == "LIKELY"

    def test_likely(self):
        assert compute_confidence_level(2.0, False, False) == "LIKELY"
        assert compute_confidence_level(3.5, True, False) == "LIKELY"

    def test_possible(self):
        assert compute_confidence_level(0.5, False, False) == "POSSIBLE"

    def test_none(self):
        assert compute_confidence_level(0, False, False) == "NONE"
        assert compute_confidence_level(-1.0, False, False) == "NONE"
