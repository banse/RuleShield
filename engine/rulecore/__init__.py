"""Rulecore — generic pattern-matching rule engine with feedback loops."""
__version__ = "0.1.0"

from rulecore.types import ScoringConfig, MatchResult, FeedbackEntry, RuleEvent
from rulecore.engine import RuleEngine
from rulecore.feedback import FeedbackManager
from rulecore.store import JsonFileFeedbackStore, FeedbackStore

__all__ = [
    "RuleEngine",
    "MatchResult",
    "ScoringConfig",
    "FeedbackEntry",
    "RuleEvent",
    "FeedbackManager",
    "JsonFileFeedbackStore",
    "FeedbackStore",
]
