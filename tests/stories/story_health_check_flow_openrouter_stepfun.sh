#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"

PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
TEST_PORT="${TEST_PORT:-8393}"
LOG_FILE="$(mktemp)"
PID_FILE="$(mktemp)"
TMP_HOME="$(mktemp -d)"

cleanup() {
	stop_gateway_from_pid_file "$PID_FILE"
	rm -f "$LOG_FILE"
	rm -rf "$TMP_HOME"
}
trap cleanup EXIT

mkdir -p "$TMP_HOME/.hermes" "$TMP_HOME/.ruleshield"
import_test_keys_for_home "$TMP_HOME"

ensure_test_ruleshield_config "$TMP_HOME" "$TEST_PORT"

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m uvicorn ruleshield.proxy:app \
	--host 127.0.0.1 \
	--port "$TEST_PORT" \
	--log-level warning \
	--app-dir "$ROOT_DIR" >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
wait_for_health "http://127.0.0.1:${TEST_PORT}/health"

# Duplicate health-check flow for a second provider profile via OpenRouter.
HOME="$TMP_HOME" \
PROXY_URL="http://127.0.0.1:${TEST_PORT}" \
MODEL="${MODEL:-stepfun/step-3.5-flash:free}" \
FALLBACK_MODEL="${FALLBACK_MODEL:-arcee-ai/trinity-large-preview:free}" \
MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-1}" \
bash "$ROOT_DIR/demo/test_training_health_check.sh"

echo "story_health_check_flow_openrouter_stepfun: ok"
