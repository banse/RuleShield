"""RuleShield Hermes -- Rule Feedback Loop and RL Integration Interface.

Implements a simple multi-armed bandit approach to rule confidence tuning:
  - Accepted rule responses increase confidence (small delta).
  - Rejected rule responses decrease confidence (larger penalty).
  - Rules that drop below a threshold are auto-deactivated.
  - Rules that rise above a promotion threshold are flagged as high-quality.

Also provides stub interfaces for future Hermes RL Training (GRPO/Atropos)
and Self-Evolution (DSPy/GEPA) integration.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("ruleshield.feedback")

_SCHEMA_FEEDBACK = """
CREATE TABLE IF NOT EXISTS rule_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    prompt_text TEXT,
    rule_response TEXT,
    feedback TEXT CHECK(feedback IN ('accept', 'reject', 'correct')),
    correction TEXT,
    classification_correct BOOLEAN,
    response_helpful BOOLEAN,
    confidence_appropriate BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_SCHEMA_RULE_EVENTS = """
CREATE TABLE IF NOT EXISTS rule_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    direction TEXT,
    old_confidence REAL,
    new_confidence REAL,
    delta REAL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Migration statements to add per-component columns to an existing table
# that was created before the per-component upgrade.
_MIGRATIONS_COMPONENT_COLUMNS = [
    "ALTER TABLE rule_feedback ADD COLUMN classification_correct BOOLEAN",
    "ALTER TABLE rule_feedback ADD COLUMN response_helpful BOOLEAN",
    "ALTER TABLE rule_feedback ADD COLUMN confidence_appropriate BOOLEAN",
]


# ---------------------------------------------------------------------------
# RuleFeedback -- bandit-style confidence updater
# ---------------------------------------------------------------------------


class RuleFeedback:
    """Tracks feedback on rule responses to improve confidence scores.

    Delegates confidence math to rulecore.FeedbackManager (EMA formula).
    Persists feedback and events to SQLite via aiosqlite.

    The feedback data is persisted in the same SQLite database used by the
    cache layer so that a single ``cache.db`` file holds all runtime state.
    """

    def __init__(
        self,
        rule_engine: Any,
        db_path: str = "~/.ruleshield/cache.db",
    ) -> None:
        self.rule_engine = rule_engine
        self.db_path = str(Path(db_path).expanduser())
        self._db: aiosqlite.Connection | None = None

        # Tuning knobs
        self.acceptance_delta: float = 0.01   # small bump per accept
        self.rejection_delta: float = 0.05    # larger penalty per reject
        self.deactivation_threshold: float = 0.5
        self.promotion_threshold: float = 0.98

        # Rulecore integration for confidence math
        from rulecore.feedback import FeedbackManager as _CoreFeedback
        from rulecore.store import JsonFileFeedbackStore as _NullStore

        class _BufferStore:
            """Captures rulecore events for async sqlite flush."""
            def __init__(self):
                self.pending_events = []
            def save_feedback(self, entry):
                pass  # sqlite persistence handled by RuleFeedback directly
            def save_event(self, event):
                self.pending_events.append(event)
            def load_feedback(self, rule_id=None):
                return []

        self._rulecore_store = _BufferStore()
        self._core_feedback = _CoreFeedback(
            engine=self.rule_engine,
            store=self._rulecore_store,
            acceptance_delta=self.acceptance_delta,
            rejection_delta=self.rejection_delta,
            deactivation_threshold=self.deactivation_threshold,
            promotion_threshold=self.promotion_threshold,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self) -> None:
        """Open the database and create the feedback table if it does not exist.

        Also runs migrations to add per-component tracking columns when
        upgrading an existing database.
        """
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_SCHEMA_FEEDBACK)
        await self._db.execute(_SCHEMA_RULE_EVENTS)
        await self._db.commit()

        # Migrate existing tables: add per-component columns if missing.
        await self._run_migrations()

        logger.info("Feedback table initialised at %s", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    # ------------------------------------------------------------------
    # Recording feedback
    # ------------------------------------------------------------------

    async def record_accept(
        self,
        rule_id: str,
        prompt_text: str,
        *,
        classification_correct: bool | None = None,
        response_helpful: bool | None = None,
        confidence_appropriate: bool | None = None,
    ) -> None:
        """Record that a rule response was accepted.

        Acceptance is typically inferred: if the next user request is *not* a
        correction or complaint, the previous rule response is implicitly
        accepted.

        Per-component tracking:
          *classification_correct* -- was the right rule matched?
          *response_helpful* -- was the response useful to the user?
          *confidence_appropriate* -- was the confidence level reasonable?
        These are optional and default to None (unknown).
        """
        if self._db is None:
            await self.init()

        await self._db.execute(
            """
            INSERT INTO rule_feedback
                (rule_id, prompt_text, feedback,
                 classification_correct, response_helpful, confidence_appropriate)
            VALUES (?, ?, 'accept', ?, ?, ?)
            """,
            (rule_id, prompt_text,
             classification_correct, response_helpful, confidence_appropriate),
        )
        await self._db.commit()

        await self.update_confidence(rule_id, accepted=True)
        await self.log_rule_event(
            rule_id=rule_id,
            event_type="feedback_accept",
            details={"prompt_text": prompt_text[:200]},
        )
        logger.debug("Recorded accept for rule %s", rule_id)

    async def record_reject(
        self,
        rule_id: str,
        prompt_text: str,
        rule_response: str,
        llm_response: str,
        *,
        classification_correct: bool | None = None,
        response_helpful: bool | None = None,
        confidence_appropriate: bool | None = None,
    ) -> None:
        """Record that a rule response was rejected.

        Rejection happens when:
          1. Shadow mode detects low similarity between the rule response and
             the LLM response for the same prompt.
          2. The user explicitly corrects the answer (e.g. "no, that's wrong").

        Per-component tracking:
          *classification_correct* -- was the right rule matched?
          *response_helpful* -- was the response useful to the user?
          *confidence_appropriate* -- was the confidence level reasonable?
        These are optional and default to None (unknown).
        """
        if self._db is None:
            await self.init()

        await self._db.execute(
            """
            INSERT INTO rule_feedback
                (rule_id, prompt_text, rule_response, feedback, correction,
                 classification_correct, response_helpful, confidence_appropriate)
            VALUES (?, ?, ?, 'reject', ?, ?, ?, ?)
            """,
            (rule_id, prompt_text, rule_response, llm_response,
             classification_correct, response_helpful, confidence_appropriate),
        )
        await self._db.commit()

        await self.update_confidence(rule_id, accepted=False)
        await self.log_rule_event(
            rule_id=rule_id,
            event_type="feedback_reject",
            details={"prompt_text": prompt_text[:200]},
        )
        logger.debug("Recorded reject for rule %s", rule_id)

    # ------------------------------------------------------------------
    # Confidence updates
    # ------------------------------------------------------------------

    async def update_confidence(self, rule_id: str, accepted: bool) -> None:
        """Update rule confidence using rulecore's EMA implementation.

        Delegates math to rulecore.FeedbackManager, then flushes
        buffered events to sqlite.
        """
        rule = self._find_rule(rule_id)
        if rule is None:
            logger.warning("Cannot update confidence: rule %s not found", rule_id)
            return

        current = rule.get("confidence", 1.0)

        # Delegate to rulecore for the EMA math
        self._core_feedback._update_confidence(rule_id, accepted=accepted)

        new_confidence = rule.get("confidence", current)

        # Flush buffered events from rulecore store to sqlite
        for event in self._rulecore_store.pending_events:
            await self.log_rule_event(
                rule_id=event.rule_id,
                event_type=event.event_type,
                direction=event.direction,
                old_confidence=event.old_confidence,
                new_confidence=event.new_confidence,
                delta=event.delta,
                details=event.details,
            )
        self._rulecore_store.pending_events.clear()

        # Check thresholds after update
        await self.check_deactivations()

        logger.info(
            "Rule %s confidence: %.4f -> %.4f (%s)",
            rule_id,
            current,
            new_confidence,
            "accept" if accepted else "reject",
        )

    # ------------------------------------------------------------------
    # Threshold checks
    # ------------------------------------------------------------------

    async def check_deactivations(self) -> list[str]:
        """Check rules against thresholds and deactivate/promote as needed.

        Returns a list of rule IDs that were deactivated in this check.
        """
        deactivated: list[str] = []

        for rule in self.rule_engine.rules:
            confidence = rule.get("confidence", 1.0)
            rule_id = rule.get("id", "")

            if confidence < self.deactivation_threshold and rule.get("enabled", True):
                self.rule_engine.deactivate_rule(rule_id)
                deactivated.append(rule_id)
                await self.log_rule_event(
                    rule_id=rule_id,
                    event_type="rule_deactivated",
                    direction="down",
                    old_confidence=confidence,
                    new_confidence=confidence,
                    delta=0.0,
                    details={"threshold": self.deactivation_threshold},
                )
                logger.warning(
                    "Rule %s deactivated (confidence %.4f < threshold %.4f)",
                    rule_id,
                    confidence,
                    self.deactivation_threshold,
                )

        return deactivated

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_feedback_stats(self) -> list[dict[str, Any]]:
        """Return per-rule feedback statistics.

        Each entry contains: rule_id, accept_count, reject_count,
        total_feedback, acceptance_rate, and current_confidence.
        """
        if self._db is None:
            await self.init()

        stats: list[dict[str, Any]] = []

        try:
            async with self._db.execute(
                """
                SELECT
                    rule_id,
                    SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS accepts,
                    SUM(CASE WHEN feedback IN ('reject', 'correct') THEN 1 ELSE 0 END) AS rejects,
                    COUNT(*) AS total
                FROM rule_feedback
                GROUP BY rule_id
                ORDER BY total DESC
                """
            ) as cur:
                rows = await cur.fetchall()

            for row in rows:
                rule_id = row["rule_id"]
                accepts = row["accepts"]
                rejects = row["rejects"]
                total = row["total"]

                # Look up current confidence from the rule engine
                rule = self._find_rule(rule_id)
                current_confidence = rule.get("confidence", 1.0) if rule else None

                stats.append({
                    "rule_id": rule_id,
                    "accept_count": accepts,
                    "reject_count": rejects,
                    "total_feedback": total,
                    "acceptance_rate": round(accepts / total, 4) if total > 0 else 0.0,
                    "current_confidence": current_confidence,
                })

        except Exception:
            logger.exception("Failed to query feedback stats")

        return stats

    async def get_recent_feedback(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent feedback entries for UI/logging use."""
        if self._db is None:
            await self.init()

        rows_out: list[dict[str, Any]] = []
        try:
            async with self._db.execute(
                """
                SELECT
                    id, rule_id, feedback, prompt_text, rule_response, correction, created_at
                FROM rule_feedback
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ) as cur:
                rows = await cur.fetchall()

            for row in rows:
                rows_out.append({
                    "id": row["id"],
                    "rule_id": row["rule_id"],
                    "feedback": row["feedback"],
                    "prompt_text": row["prompt_text"] or "",
                    "rule_response": row["rule_response"] or "",
                    "correction": row["correction"] or "",
                    "created_at": row["created_at"] or "",
                })
        except Exception:
            logger.exception("Failed to query recent feedback")

        return rows_out

    async def get_recent_rule_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent confidence/lifecycle events for the rule engine."""
        if self._db is None:
            await self.init()

        rows_out: list[dict[str, Any]] = []
        try:
            async with self._db.execute(
                """
                SELECT
                    id, rule_id, event_type, direction,
                    old_confidence, new_confidence, delta, details, created_at
                FROM rule_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ) as cur:
                rows = await cur.fetchall()

            for row in rows:
                details = row["details"] or ""
                try:
                    details_obj = json.loads(details) if details else {}
                except Exception:
                    details_obj = {"raw": details}

                rows_out.append({
                    "id": row["id"],
                    "rule_id": row["rule_id"],
                    "event_type": row["event_type"],
                    "direction": row["direction"] or "",
                    "old_confidence": float(row["old_confidence"] or 0.0),
                    "new_confidence": float(row["new_confidence"] or 0.0),
                    "delta": float(row["delta"] or 0.0),
                    "details": details_obj,
                    "created_at": row["created_at"] or "",
                })
        except Exception:
            logger.exception("Failed to query recent rule events")

        return rows_out

    async def log_rule_event(
        self,
        rule_id: str,
        event_type: str,
        direction: str | None = None,
        old_confidence: float | None = None,
        new_confidence: float | None = None,
        delta: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append a rule engine event row."""
        if self._db is None:
            await self.init()

        try:
            await self._db.execute(
                """
                INSERT INTO rule_events
                    (rule_id, event_type, direction, old_confidence, new_confidence, delta, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_id,
                    event_type,
                    direction,
                    old_confidence,
                    new_confidence,
                    delta,
                    json.dumps(details or {}),
                ),
            )
            await self._db.commit()
        except Exception:
            logger.exception("Failed to write rule event for %s", rule_id)

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------

    async def get_underperforming_rules(
        self,
        min_feedback: int = 5,
    ) -> list[dict[str, Any]]:
        """Find rules with low accuracy.

        Returns rules where:
          - Total feedback >= *min_feedback* (ensures statistical relevance).
          - Acceptance rate < 70%.

        Results are sorted by acceptance rate ascending (worst first) so
        that operators can prioritise the most problematic rules for review
        or deactivation.
        """
        if self._db is None:
            await self.init()

        results: list[dict[str, Any]] = []

        try:
            async with self._db.execute(
                """
                SELECT
                    rule_id,
                    SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS accepts,
                    COUNT(*) AS total
                FROM rule_feedback
                GROUP BY rule_id
                HAVING COUNT(*) >= ?
                ORDER BY (CAST(SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS REAL)
                          / COUNT(*)) ASC
                """,
                (min_feedback,),
            ) as cur:
                rows = await cur.fetchall()

            for row in rows:
                rule_id = row["rule_id"]
                accepts = row["accepts"]
                total = row["total"]
                rate = round(accepts / total, 4) if total > 0 else 0.0

                if rate >= 0.70:
                    continue  # only return underperformers

                rule = self._find_rule(rule_id)
                results.append({
                    "rule_id": rule_id,
                    "rule_name": rule.get("name", rule_id) if rule else rule_id,
                    "accept_count": accepts,
                    "reject_count": total - accepts,
                    "total_feedback": total,
                    "acceptance_rate": rate,
                    "current_confidence": rule.get("confidence", 1.0) if rule else None,
                })

        except Exception:
            logger.exception("Failed to query underperforming rules")

        return results

    async def get_performance_by_category(self) -> dict[str, dict[str, Any]]:
        """Group feedback by rule category / ID prefix.

        Uses the portion of the rule_id before the first underscore as the
        category name (e.g. ``greeting_simple`` -> ``greeting``).  This gives
        operators a high-level view of which *domains* of rules are working
        well and which need attention.

        Returns::

            {
                "greeting": {"total": 50, "accepted": 48, "accuracy": 0.96},
                "status_check": {"total": 30, "accepted": 22, "accuracy": 0.73},
            }
        """
        if self._db is None:
            await self.init()

        categories: dict[str, dict[str, Any]] = {}

        try:
            async with self._db.execute(
                """
                SELECT
                    rule_id,
                    SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS accepts,
                    COUNT(*) AS total
                FROM rule_feedback
                GROUP BY rule_id
                """
            ) as cur:
                rows = await cur.fetchall()

            for row in rows:
                rule_id: str = row["rule_id"]
                # Derive category from rule_id prefix (before first '_').
                category = rule_id.split("_")[0] if "_" in rule_id else rule_id

                if category not in categories:
                    categories[category] = {"total": 0, "accepted": 0, "accuracy": 0.0}

                categories[category]["total"] += row["total"]
                categories[category]["accepted"] += row["accepts"]

            # Compute accuracy for each category.
            for cat_data in categories.values():
                total = cat_data["total"]
                cat_data["accuracy"] = (
                    round(cat_data["accepted"] / total, 4) if total > 0 else 0.0
                )

        except Exception:
            logger.exception("Failed to query performance by category")

        return categories

    async def get_component_accuracy(self) -> dict[str, dict[str, float]]:
        """Return per-component accuracy across all rules.

        Analyses the boolean component columns (classification_correct,
        response_helpful, confidence_appropriate) to identify which
        *aspect* of the rule engine needs the most improvement.

        Returns::

            {
                "classification_correct": {"total": 100, "correct": 92, "accuracy": 0.92},
                "response_helpful": {"total": 85, "correct": 78, "accuracy": 0.9176},
                "confidence_appropriate": {"total": 60, "correct": 55, "accuracy": 0.9167},
            }
        """
        if self._db is None:
            await self.init()

        _VALID_COMPONENT_COLS = frozenset({"classification_correct", "response_helpful", "confidence_appropriate"})
        components = ("classification_correct", "response_helpful", "confidence_appropriate")
        result: dict[str, dict[str, float]] = {}

        try:
            for col in components:
                if col not in _VALID_COMPONENT_COLS:
                    continue  # skip invalid column names
                async with self._db.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN {col} = 1 THEN 1 ELSE 0 END) AS correct
                    FROM rule_feedback
                    WHERE {col} IS NOT NULL
                    """
                ) as cur:
                    row = await cur.fetchone()

                total = row["total"] if row else 0
                correct = row["correct"] if row else 0
                result[col] = {
                    "total": total,
                    "correct": correct,
                    "accuracy": round(correct / total, 4) if total > 0 else 0.0,
                }

        except Exception:
            logger.exception("Failed to query component accuracy")

        return result

    # ------------------------------------------------------------------
    # Auto-promotion
    # ------------------------------------------------------------------

    async def check_promotions(self) -> list[str]:
        """Check if any rules should be auto-promoted based on feedback.

        A rule is promoted (enabled) when:
          1. It is currently disabled (shadow/candidate mode).
          2. It has at least ``min_shadow_comparisons`` shadow comparisons.
          3. Shadow accuracy > 80% (avg similarity from shadow_log).
          4. Acceptance rate from feedback > 85%.

        Returns list of promoted rule IDs.
        """
        if self._db is None:
            await self.init()

        min_shadow_comparisons = 10
        min_shadow_accuracy = 0.80
        min_acceptance_rate = 0.85

        promoted: list[str] = []

        # Find shadow candidates that are eligible for promotion.
        candidate_rules = [
            r for r in self.rule_engine.rules
            if r.get("deployment") == "candidate"
        ]

        if not candidate_rules:
            return promoted

        for rule in candidate_rules:
            rule_id = rule.get("id", "")
            if not rule_id:
                continue

            # Check shadow comparisons (query the shadow_log table).
            shadow_ok = False
            try:
                async with self._db.execute(
                    """
                    SELECT COUNT(*) AS total, AVG(similarity) AS avg_sim
                    FROM shadow_log
                    WHERE rule_id = ?
                    """,
                    (rule_id,),
                ) as cur:
                    row = await cur.fetchone()

                if row:
                    shadow_total = row["total"] or 0
                    shadow_avg = float(row["avg_sim"] or 0)
                    if (shadow_total >= min_shadow_comparisons
                            and shadow_avg >= min_shadow_accuracy):
                        shadow_ok = True
            except Exception:
                # shadow_log table may not exist yet -- skip shadow check.
                logger.debug("Shadow log query failed for rule %s", rule_id)
                continue

            if not shadow_ok:
                continue

            # Check feedback acceptance rate.
            feedback_ok = False
            try:
                async with self._db.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS accepts
                    FROM rule_feedback
                    WHERE rule_id = ?
                    """,
                    (rule_id,),
                ) as cur:
                    row = await cur.fetchone()

                if row:
                    fb_total = row["total"] or 0
                    fb_accepts = row["accepts"] or 0
                    if fb_total > 0:
                        acceptance_rate = fb_accepts / fb_total
                        if acceptance_rate >= min_acceptance_rate:
                            feedback_ok = True
                    else:
                        # No feedback yet -- allow promotion based on shadow alone
                        # if shadow accuracy is strong enough.
                        feedback_ok = True
            except Exception:
                logger.debug("Feedback query failed for rule %s", rule_id)
                continue

            if not feedback_ok:
                continue

            # Rule passes all checks -- promote it.
            promoted.append(rule_id)
            logger.info(
                "Rule %s eligible for auto-promotion "
                "(shadow: %d comparisons, %.2f avg_sim; feedback: accepted)",
                rule_id,
                shadow_total,
                shadow_avg,
            )

        return promoted

    async def get_promotion_candidates(self) -> list[dict[str, Any]]:
        """Return detailed information about disabled rules and their promotion status.

        Each entry contains: rule_id, rule_name, enabled, shadow_total,
        shadow_avg_sim, feedback_total, acceptance_rate, promotable.
        """
        if self._db is None:
            await self.init()

        candidates: list[dict[str, Any]] = []

        candidate_rules = [
            r for r in self.rule_engine.rules
            if r.get("deployment") == "candidate"
        ]

        for rule in candidate_rules:
            rule_id = rule.get("id", "")
            if not rule_id:
                continue

            entry: dict[str, Any] = {
                "rule_id": rule_id,
                "rule_name": rule.get("name", rule_id),
                "confidence": rule.get("confidence", 1.0),
                "shadow_total": 0,
                "shadow_avg_sim": 0.0,
                "feedback_total": 0,
                "acceptance_rate": 0.0,
                "promotable": False,
            }

            # Shadow stats
            try:
                async with self._db.execute(
                    """
                    SELECT COUNT(*) AS total, AVG(similarity) AS avg_sim
                    FROM shadow_log
                    WHERE rule_id = ?
                    """,
                    (rule_id,),
                ) as cur:
                    row = await cur.fetchone()
                if row:
                    entry["shadow_total"] = row["total"] or 0
                    entry["shadow_avg_sim"] = round(float(row["avg_sim"] or 0), 4)
            except Exception:
                pass

            # Feedback stats
            try:
                async with self._db.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS accepts
                    FROM rule_feedback
                    WHERE rule_id = ?
                    """,
                    (rule_id,),
                ) as cur:
                    row = await cur.fetchone()
                if row:
                    entry["feedback_total"] = row["total"] or 0
                    fb_accepts = row["accepts"] or 0
                    if entry["feedback_total"] > 0:
                        entry["acceptance_rate"] = round(
                            fb_accepts / entry["feedback_total"], 4
                        )
            except Exception:
                pass

            # Determine if promotable
            shadow_ok = (
                entry["shadow_total"] >= 10
                and entry["shadow_avg_sim"] >= 0.80
            )
            feedback_ok = (
                entry["feedback_total"] == 0  # no feedback = allow based on shadow
                or entry["acceptance_rate"] >= 0.85
            )
            entry["promotable"] = shadow_ok and feedback_ok

            candidates.append(entry)

        return candidates

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Find a rule in the engine by ID."""
        for rule in self.rule_engine.rules:
            if rule.get("id") == rule_id:
                return rule
        return None

    async def _run_migrations(self) -> None:
        """Apply schema migrations for existing databases.

        Adds per-component tracking columns that may not
        exist in databases created before this upgrade.  Each ALTER TABLE
        is wrapped in a try/except so that already-migrated databases
        proceed without error.
        """
        for stmt in _MIGRATIONS_COMPONENT_COLUMNS:
            try:
                await self._db.execute(stmt)
            except Exception:
                # Column already exists -- safe to ignore.
                pass
        await self._db.commit()


# ---------------------------------------------------------------------------
# HermesRLInterface -- stub for future Hermes RL Training integration
# ---------------------------------------------------------------------------


class HermesRLInterface:
    """Stub interface for future Hermes RL Training integration.

    Hermes uses GRPO (Group Relative Policy Optimization) via Atropos + Tinker.
    RuleShield can provide training environments that teach the model to produce
    more cacheable and rule-friendly responses.

    All methods in this class are stubs that return configuration dicts
    describing the *intended* integration.  They are safe to call but perform
    no actual training or optimization.
    """

    def create_rl_environment(self) -> dict[str, Any]:
        """Generate an RL environment config for Hermes training.

        The environment would:
          1. Present prompts from the request_log.
          2. Score responses on cacheability and rule-friendliness.
          3. Reward = cosine_similarity(response, cached_response) * brevity_bonus.

        Returns a config dict compatible with Hermes RL environments.
        """
        return {
            "name": "ruleshield_optimization",
            "description": (
                "Trains model to produce responses that are more "
                "cacheable and rule-friendly"
            ),
            "reward_function": (
                "cosine_similarity(response, cached_response) * brevity_bonus"
            ),
            "status": "stub -- future implementation",
        }

    def create_gepa_config(self) -> dict[str, Any]:
        """Generate a GEPA config for evolving rule patterns.

        GEPA (Genetic-Pareto Prompt Evolution) can optimize:
          1. Rule patterns (better matching / higher recall).
          2. Response templates (better quality / user satisfaction).
          3. Confidence thresholds (better calibration).

        Returns a config dict compatible with hermes-agent-self-evolution.
        """
        return {
            "optimization_targets": [
                {
                    "type": "rule_patterns",
                    "metric": "recall",
                    "constraint": "precision > 0.95",
                },
                {
                    "type": "response_templates",
                    "metric": "user_satisfaction",
                    "constraint": "length < 200",
                },
            ],
            "status": "stub -- future implementation",
        }

    def export_trajectories(self, request_log_path: str) -> str:
        """Export request_log as JSONL trajectories for Hermes RL training.

        The output format is compatible with Hermes ``save_trajectories=True``.

        Returns the path to the generated JSONL file.
        """
        # Stub -- in production this would read the SQLite request_log,
        # convert each row to an OpenAI-format conversation, and write JSONL.
        return "~/.ruleshield/trajectories.jsonl"
