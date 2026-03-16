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
URL="http://127.0.0.1:${PORT}/v1/chat/completions"

send_prompt() {
	local prompt="$1"
	curl -fsS "$URL" \
		-H "Authorization: Bearer sk-test" \
		-H "Content-Type: application/json" \
		-d "{\"model\":\"arcee-ai/trinity-large-preview:free\",\"messages\":[{\"role\":\"user\",\"content\":\"$prompt\"}],\"max_tokens\":32}"
}

RESP1="$(send_prompt "hello")"
RESP2="$(send_prompt "thanks")"
RESP3="$(send_prompt "bye")"

RESP1="$RESP1" RESP2="$RESP2" RESP3="$RESP3" "$PYTHON_BIN" - <<'PY'
import json
import os

responses = [os.environ["RESP1"], os.environ["RESP2"], os.environ["RESP3"]]
rule_like = 0
for raw in responses:
    body = json.loads(raw)
    model = str(body.get("model", ""))
    choices = body.get("choices") or []
    content = ""
    if choices:
        content = str(((choices[0].get("message") or {}).get("content")) or "")
    if model.startswith("ruleshield"):
        rule_like += 1
    if not content.strip():
        raise SystemExit("response content was empty")

if rule_like < 1:
    raise SystemExit("expected at least one RuleShield-resolved response")
PY

echo "story_rule_trigger_flow: ok"
