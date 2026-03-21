"""Core data types for rulecore."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoringConfig:
    """Configurable scoring weights for pattern matching."""
    keyword_weight: float = 1.0
    pattern_weight: float = 2.0
    exact_weight: float = 5.0
    condition_weight: float = 0.5
    min_score: float = 1.5


@dataclass
class MatchResult:
    """Result of a successful rule match."""
    rule_id: str
    rule_name: str
    response: dict[str, Any]
    confidence: float
    match_score: float
    confidence_level: str
    matched_keywords: list[str]
    matched_patterns: list[str]
    deployment: str = "production"


@dataclass
class FeedbackEntry:
    """A single feedback record."""
    rule_id: str
    prompt: str
    feedback_type: str
    correction: str | None = None
    classification_correct: bool | None = None
    response_helpful: bool | None = None
    confidence_appropriate: bool | None = None
    timestamp: str = ""


@dataclass
class RuleEvent:
    """A rule lifecycle event."""
    rule_id: str
    event_type: str
    direction: str | None = None
    old_confidence: float | None = None
    new_confidence: float | None = None
    delta: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
