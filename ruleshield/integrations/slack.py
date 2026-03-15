"""RuleShield Slack Integration -- sends savings alerts via webhook.

Configure via:
  RULESHIELD_SLACK_WEBHOOK=https://hooks.slack.com/services/...

Or in ~/.ruleshield/config.yaml:
  slack_webhook: https://hooks.slack.com/services/...
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("ruleshield.slack")


class SlackNotifier:
    """Sends cost-savings notifications to a Slack channel via incoming webhook."""

    def __init__(self, webhook_url: str = "") -> None:
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
        self._last_milestone: int = 0  # track last notified savings milestone

    async def notify_savings_milestone(self, stats: dict[str, Any]) -> bool:
        """Send notification when savings hit a milestone ($1, $5, $10, $50, $100, etc.)."""
        if not self.enabled:
            return False

        savings = stats.get("savings_usd", 0)
        milestone = self._next_milestone(savings)
        if milestone <= self._last_milestone:
            return False  # already notified for this milestone

        self._last_milestone = milestone

        blocks = self._build_milestone_message(stats, milestone)
        return await self._send(blocks)

    async def notify_daily_summary(self, stats: dict[str, Any]) -> bool:
        """Send daily savings summary."""
        if not self.enabled:
            return False
        blocks = self._build_daily_summary(stats)
        return await self._send(blocks)

    async def notify_rule_activated(self, rule_name: str, confidence: float) -> bool:
        """Notify when a new rule is auto-activated."""
        if not self.enabled:
            return False
        blocks = self._build_rule_notification(rule_name, confidence)
        return await self._send(blocks)

    async def send_test(self) -> bool:
        """Send a test notification to verify webhook configuration."""
        if not self.enabled:
            return False
        blocks = self._build_test_message()
        return await self._send(blocks)

    # ------------------------------------------------------------------
    # Milestone tracking
    # ------------------------------------------------------------------

    def _next_milestone(self, savings: float) -> int:
        """Find the highest milestone reached."""
        milestones = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000, 10000]
        reached = 0
        for m in milestones:
            if savings >= m:
                reached = m
        return reached

    # ------------------------------------------------------------------
    # Message builders (Slack Block Kit)
    # ------------------------------------------------------------------

    @staticmethod
    def _savings_bar(pct: float, width: int = 10) -> str:
        """Build a text-based savings bar using block characters.

        ``pct`` is a percentage 0-100.  Returns a string like
        ``[=====-----] 50%`` using unicode block elements.
        """
        filled = max(0, min(width, round(pct / 100 * width)))
        empty = width - filled
        bar = "\u2588" * filled + "\u2591" * empty
        return f"|{bar}| {pct:.1f}%"

    def _build_milestone_message(
        self, stats: dict[str, Any], milestone: int
    ) -> list[dict[str, Any]]:
        """Build Slack Block Kit message for a savings milestone."""
        savings_usd = stats.get("savings_usd", 0)
        total_requests = stats.get("total_requests", 0)
        cache_hits = stats.get("cache_hits", 0)
        rule_hits = stats.get("rule_hits", 0)
        llm_calls = stats.get("llm_calls", 0)
        savings_pct = stats.get("savings_pct", 0)

        bar = self._savings_bar(savings_pct)

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"RuleShield Savings Milestone: ${milestone}!",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*You've saved ${savings_usd:,.2f} on LLM costs!*\n"
                        f"Savings rate: `{bar}`"
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Requests*\n{total_requests:,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Cache Hits*\n{cache_hits:,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Rule Hits*\n{rule_hits:,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*LLM Calls*\n{llm_calls:,}",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Powered by *RuleShield Hermes* -- LLM cost optimizer proxy",
                    }
                ],
            },
        ]

    def _build_daily_summary(self, stats: dict[str, Any]) -> list[dict[str, Any]]:
        """Build daily summary message."""
        savings_usd = stats.get("savings_usd", 0)
        savings_pct = stats.get("savings_pct", 0)
        total_requests = stats.get("total_requests", 0)
        cache_hits = stats.get("cache_hits", 0)
        rule_hits = stats.get("rule_hits", 0)
        llm_calls = stats.get("llm_calls", 0)
        cost_without = stats.get("cost_without", 0)
        cost_with = stats.get("cost_with", 0)

        bar = self._savings_bar(savings_pct)

        # Identify top rules if provided
        top_rules = stats.get("top_rules", [])
        rules_text = ""
        if top_rules:
            rules_lines = [
                f"  {i+1}. `{r['name']}` -- {r['hits']} hits"
                for i, r in enumerate(top_rules[:5])
            ]
            rules_text = "\n*Top Rules:*\n" + "\n".join(rules_lines)

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "RuleShield Daily Summary",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Savings Today:* ${savings_usd:,.2f}\n"
                        f"Savings rate: `{bar}`\n\n"
                        f"*Cost without RuleShield:* ${cost_without:,.4f}\n"
                        f"*Cost with RuleShield:* ${cost_with:,.4f}"
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Requests*\n{total_requests:,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Cache Hits*\n{cache_hits:,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Rule Hits*\n{rule_hits:,}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*LLM Calls*\n{llm_calls:,}",
                    },
                ],
            },
            *([
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": rules_text},
                }
            ] if rules_text else []),
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Powered by *RuleShield Hermes* -- LLM cost optimizer proxy",
                    }
                ],
            },
        ]

    def _build_rule_notification(
        self, rule_name: str, confidence: float
    ) -> list[dict[str, Any]]:
        """Build rule activation notification."""
        conf_pct = confidence * 100
        if conf_pct >= 90:
            level = "HIGH"
        elif conf_pct >= 70:
            level = "MEDIUM"
        else:
            level = "LOW"

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "RuleShield: New Rule Activated",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"A new cost-saving rule has been auto-activated:\n\n"
                        f"*Rule:* `{rule_name}`\n"
                        f"*Confidence:* {conf_pct:.0f}% ({level})\n\n"
                        "This rule will now intercept matching prompts and "
                        "return cached responses instead of calling the LLM."
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Powered by *RuleShield Hermes* -- LLM cost optimizer proxy",
                    }
                ],
            },
        ]

    def _build_test_message(self) -> list[dict[str, Any]]:
        """Build a test/verification message."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "RuleShield Slack Integration Active",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Your Slack webhook is configured correctly.\n\n"
                        "You will receive notifications when:\n"
                        "  - Savings milestones are reached ($1, $5, $10, ...)\n"
                        "  - Daily summaries are generated\n"
                        "  - New rules are auto-activated"
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status*\nConnected",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Notifications*\nEnabled",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Powered by *RuleShield Hermes* -- LLM cost optimizer proxy",
                    }
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    async def _send(self, blocks: list[dict[str, Any]]) -> bool:
        """Send message via webhook."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.webhook_url,
                    json={"blocks": blocks},
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    logger.info("Slack notification sent successfully")
                    return True
                else:
                    logger.warning(
                        "Slack webhook returned status %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return False
        except Exception as e:
            logger.warning("Slack notification failed: %s", e)
            return False
