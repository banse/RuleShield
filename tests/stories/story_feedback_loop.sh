#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"

TMP_HOME="$(mktemp -d)"
LOG_FILE="$(mktemp)"
PID_FILE="$(mktemp)"
PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"

cleanup() {
	stop_gateway_from_pid_file "$PID_FILE"
	rm -f "$LOG_FILE"
	rm -rf "$TMP_HOME"
}
trap cleanup EXIT

PORT="$(start_gateway_for_home "$TMP_HOME" "$LOG_FILE" "$PID_FILE")"
BASE_URL="http://127.0.0.1:${PORT}"

RULES_JSON="$(curl -fsS "$BASE_URL/api/rules")"
TARGET_RULE_ID="$(
RULES_JSON="$RULES_JSON" "$PYTHON_BIN" - <<'PY'
import json
import os

payload = json.loads(os.environ["RULES_JSON"])
rules = payload.get("rules") or []
if not rules:
    raise SystemExit("no rules available for feedback story test")
print(str(rules[0].get("id", "")).strip())
PY
)"

if [[ -z "$TARGET_RULE_ID" ]]; then
	echo "ERROR: could not determine target rule id" >&2
	exit 1
fi

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" TARGET_RULE_ID="$TARGET_RULE_ID" "$PYTHON_BIN" - <<'PY'
import asyncio
import os
from pathlib import Path

from ruleshield.feedback import RuleFeedback
from ruleshield.rules import RuleEngine

rule_id = os.environ["TARGET_RULE_ID"]

async def main() -> None:
    engine = RuleEngine()
    await engine.init()
    feedback = RuleFeedback(engine, db_path=str(Path.home() / ".ruleshield" / "cache.db"))
    await feedback.init()
    await feedback.record_accept(rule_id, "hello")
    await feedback.record_reject(rule_id, "hello", "hello there", "hi there")
    await feedback.close()

asyncio.run(main())
PY

FEEDBACK_JSON="$(curl -fsS "$BASE_URL/api/feedback?limit=20")"
EVENTS_JSON="$(curl -fsS "$BASE_URL/api/rule-events?limit=30")"

TARGET_RULE_ID="$TARGET_RULE_ID" FEEDBACK_JSON="$FEEDBACK_JSON" EVENTS_JSON="$EVENTS_JSON" "$PYTHON_BIN" - <<'PY'
import json
import os

rule_id = os.environ["TARGET_RULE_ID"]
feedback_payload = json.loads(os.environ["FEEDBACK_JSON"])
events_payload = json.loads(os.environ["EVENTS_JSON"])

entries = feedback_payload.get("entries") or []
stats = feedback_payload.get("stats") or []
events = events_payload.get("events") or []

rule_entries = [e for e in entries if str(e.get("rule_id", "")) == rule_id]
if len(rule_entries) < 2:
    raise SystemExit("feedback entries not persisted for target rule")

feedback_types = {str(e.get("feedback", "")) for e in rule_entries}
if "accept" not in feedback_types or "reject" not in feedback_types:
    raise SystemExit("expected both accept and reject feedback entries")

rule_stats = [s for s in stats if str(s.get("rule_id", "")) == rule_id]
if not rule_stats:
    raise SystemExit("feedback stats missing target rule")
if int(rule_stats[0].get("total_feedback", 0)) < 2:
    raise SystemExit("feedback stats total_feedback did not update")

rule_events = [e for e in events if str(e.get("rule_id", "")) == rule_id]
if not rule_events:
    raise SystemExit("rule events missing for target rule")
if not any(str(e.get("event_type", "")) == "confidence_update" for e in rule_events):
    raise SystemExit("confidence_update event missing for target rule")
PY

echo "story_feedback_loop: ok"
