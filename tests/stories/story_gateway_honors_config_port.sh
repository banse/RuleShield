#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"

PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
TMP_HOME="$(mktemp -d)"
LOG_FILE="$(mktemp)"
PID_FILE="$(mktemp)"

cleanup() {
	stop_gateway_from_pid_file "$PID_FILE"
	rm -f "$LOG_FILE"
	rm -rf "$TMP_HOME"
}
trap cleanup EXIT

mkdir -p "$TMP_HOME/.ruleshield"
cat >"$TMP_HOME/.ruleshield/config.yaml" <<'YAML'
port: 8391
YAML

PORT="$(start_gateway_for_home "$TMP_HOME" "$LOG_FILE" "$PID_FILE")"

if [[ "$PORT" != "8391" ]]; then
	echo "ERROR: gateway ignored configured port. expected=8391 got=$PORT" >&2
	exit 1
fi

curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - <<'PY'
from ruleshield.config import load_settings
port = load_settings().port
if port != 8391:
    raise SystemExit(f"load_settings().port mismatch: {port}")
PY

echo "story_gateway_honors_config_port: ok (port=$PORT)"
