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

# Send a technical prompt that should NOT match any built-in rule,
# forcing a genuine upstream passthrough to the LLM provider.
RESP="$(curl -fsS "$URL" \
	-H "Authorization: Bearer sk-test" \
	-H "Content-Type: application/json" \
	-d '{"model":"arcee-ai/trinity-large-preview:free","messages":[{"role":"user","content":"Explain the difference between TCP and UDP in networking"}],"max_tokens":64}')"

RESP="$RESP" "$PYTHON_BIN" - <<'PY'
import json
import os
import sys

raw = os.environ["RESP"]
body = json.loads(raw)

# 1. Validate structure: choices[0].message.content must be non-empty
choices = body.get("choices") or []
if not choices:
    sys.exit("FAIL: response has no choices")

content = ((choices[0].get("message") or {}).get("content") or "").strip()
if not content:
    sys.exit("FAIL: choices[0].message.content is empty")

# 2. Validate the response was forwarded upstream (not resolved by a rule)
model = str(body.get("model", ""))
if model.startswith("ruleshield-rule") or model.startswith("ruleshield-cache"):
    sys.exit(f"FAIL: expected upstream passthrough but got model={model}")

print(f"passthrough ok  model={model}  content_len={len(content)}")
PY

echo "story_hermes_passthrough: ok"
