"""Scoring logic for rulecore — confidence levels and score computation."""
from __future__ import annotations


def compute_confidence_level(
    score: float,
    has_keywords: bool,
    has_patterns: bool,
) -> str:
    """Compute a discrete confidence level from a numeric match score."""
    if score >= 4.0 and has_keywords and has_patterns:
        return "CONFIRMED"
    if score >= 2.0:
        return "LIKELY"
    if score > 0:
        return "POSSIBLE"
    return "NONE"
