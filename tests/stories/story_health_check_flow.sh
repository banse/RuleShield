#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TESTS_DIR="$ROOT_DIR/tests"
source "$TESTS_DIR/_stories_helpers.sh"

PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
TEST_PORT="${TEST_PORT:-8392}"
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

SCENARIO_CONFIG="${SCENARIO_CONFIG:-$ROOT_DIR/ruleshield/training_configs/health_check_baseline.yaml}"
MODEL="${MODEL:-arcee-ai/trinity-large-preview:free}"
OUTPUT_BASE="${OUTPUT_BASE:-$ROOT_DIR/test-runs/training-health-check-story}"
MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-1}"
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$OUTPUT_BASE/$RUN_STAMP"

if [[ ! -f "$SCENARIO_CONFIG" ]]; then
	echo "ERROR: health scenario config not found: $SCENARIO_CONFIG" >&2
	exit 1
fi

curl -fsS "http://127.0.0.1:${TEST_PORT}/health" >/dev/null

PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -u -m ruleshield.cli run-prompt-training \
	--proxy-url "http://127.0.0.1:${TEST_PORT}" \
	--model "$MODEL" \
	--scenario-config "$SCENARIO_CONFIG" \
	--max-iterations "$MAX_ITER_HEALTH" \
	--output-dir "$RUN_DIR"

SUMMARY_JSON="$(find "$RUN_DIR" -type f -name 'ruleshield-summary.json' | sort | tail -n 1)"
if [[ -z "$SUMMARY_JSON" || ! -f "$SUMMARY_JSON" ]]; then
	echo "ERROR: missing ruleshield-summary.json in $RUN_DIR" >&2
	exit 1
fi

echo "story_health_check_flow: ok"
