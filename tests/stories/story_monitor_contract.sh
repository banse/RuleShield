#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"

TMP_HOME="$(mktemp -d)"
LOG_FILE="$(mktemp)"
PID_FILE="$(mktemp)"

cleanup() {
	stop_gateway_from_pid_file "$PID_FILE"
	rm -f "$LOG_FILE"
	rm -rf "$TMP_HOME"
}
trap cleanup EXIT

PORT="$(start_gateway_for_home "$TMP_HOME" "$LOG_FILE" "$PID_FILE")"
BASE_URL="http://127.0.0.1:${PORT}"

SCRIPTS_JSON="$(curl -fsS "$BASE_URL/api/test-monitor/scripts")"
PROFILES_JSON="$(curl -fsS "$BASE_URL/api/test-monitor/model-profiles")"
RUNS_JSON="$(curl -fsS "$BASE_URL/api/test-monitor/runs?limit=10")"

SCRIPTS_JSON="$SCRIPTS_JSON" PROFILES_JSON="$PROFILES_JSON" RUNS_JSON="$RUNS_JSON" \
python3 - <<'PY'
import json
import os

scripts_payload = json.loads(os.environ["SCRIPTS_JSON"])
profiles_payload = json.loads(os.environ["PROFILES_JSON"])
runs_payload = json.loads(os.environ["RUNS_JSON"])

if not isinstance(scripts_payload.get("scripts"), list):
    raise SystemExit("monitor scripts payload missing scripts list")
if not isinstance(scripts_payload.get("active_runs"), int):
    raise SystemExit("monitor scripts payload missing active_runs int")
if not isinstance(scripts_payload.get("total"), int):
    raise SystemExit("monitor scripts payload missing total int")

scripts = scripts_payload["scripts"]
if scripts:
    sample = scripts[0]
    required = [
        "path",
        "name",
        "type",
        "default_model_profile_id",
        "status",
        "active_run_id",
        "last_run_id",
    ]
    missing = [key for key in required if key not in sample]
    if missing:
        raise SystemExit(f"monitor scripts entry missing keys: {missing}")

profiles = profiles_payload.get("profiles")
if not isinstance(profiles, list) or not profiles:
    raise SystemExit("model profiles missing or empty")
if not isinstance(profiles_payload.get("default_profile_id"), str):
    raise SystemExit("default_profile_id missing")

profile_sample = profiles[0]
for key in ("id", "label", "provider", "model"):
    if key not in profile_sample:
        raise SystemExit(f"model profile missing key: {key}")

runs = runs_payload.get("runs")
if not isinstance(runs, list):
    raise SystemExit("runs payload missing runs list")
if not isinstance(runs_payload.get("limit"), int):
    raise SystemExit("runs payload missing limit int")
PY

echo "story_monitor_contract: ok"
