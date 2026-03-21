"""Feedback storage protocol and JSON file implementation for rulecore."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from rulecore.types import FeedbackEntry, RuleEvent

logger = logging.getLogger("rulecore.store")


@runtime_checkable
class FeedbackStore(Protocol):
    """Protocol for feedback persistence backends."""
    def save_feedback(self, entry: FeedbackEntry) -> None: ...
    def save_event(self, event: RuleEvent) -> None: ...
    def load_feedback(self, rule_id: str | None = None) -> list[FeedbackEntry]: ...
    def load_events(self, rule_id: str | None = None) -> list[RuleEvent]: ...


class JsonFileFeedbackStore:
    """Zero-dependency JSON file feedback store."""

    def __init__(self, path: str = "feedback.json") -> None:
        self.path = os.path.expanduser(path)
        self._data: dict[str, Any] = {"feedback": [], "events": []}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {"feedback": [], "events": []}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            logger.warning("Failed to save feedback store to %s", self.path)

    def save_feedback(self, entry: FeedbackEntry) -> None:
        record = {
            "rule_id": entry.rule_id,
            "prompt": entry.prompt,
            "feedback_type": entry.feedback_type,
            "correction": entry.correction,
            "classification_correct": entry.classification_correct,
            "response_helpful": entry.response_helpful,
            "confidence_appropriate": entry.confidence_appropriate,
            "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
        }
        self._data.setdefault("feedback", []).append(record)
        self._save()

    def save_event(self, event: RuleEvent) -> None:
        record = {
            "rule_id": event.rule_id,
            "event_type": event.event_type,
            "direction": event.direction,
            "old_confidence": event.old_confidence,
            "new_confidence": event.new_confidence,
            "delta": event.delta,
            "details": event.details,
            "timestamp": event.timestamp or datetime.now(timezone.utc).isoformat(),
        }
        self._data.setdefault("events", []).append(record)
        self._save()

    def load_feedback(self, rule_id: str | None = None) -> list[FeedbackEntry]:
        entries = []
        for rec in self._data.get("feedback", []):
            if rule_id and rec.get("rule_id") != rule_id:
                continue
            entries.append(FeedbackEntry(
                rule_id=rec["rule_id"],
                prompt=rec.get("prompt", ""),
                feedback_type=rec.get("feedback_type", ""),
                correction=rec.get("correction"),
                classification_correct=rec.get("classification_correct"),
                response_helpful=rec.get("response_helpful"),
                confidence_appropriate=rec.get("confidence_appropriate"),
                timestamp=rec.get("timestamp", ""),
            ))
        return entries

    def load_events(self, rule_id: str | None = None) -> list[RuleEvent]:
        events = []
        for rec in self._data.get("events", []):
            if rule_id and rec.get("rule_id") != rule_id:
                continue
            events.append(RuleEvent(
                rule_id=rec["rule_id"],
                event_type=rec.get("event_type", ""),
                direction=rec.get("direction"),
                old_confidence=rec.get("old_confidence"),
                new_confidence=rec.get("new_confidence"),
                delta=rec.get("delta"),
                details=rec.get("details", {}),
                timestamp=rec.get("timestamp", ""),
            ))
        return events
