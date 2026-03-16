#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"

PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
MODEL_PROFILE_ID="${MODEL_PROFILE_ID:-openrouter_arcee_trinity_free}"
RUN_TIMEOUT_SECONDS="${RUN_TIMEOUT_SECONDS:-300}"
LIGHTPANDA_BIN="${LIGHTPANDA_BIN:-$ROOT_DIR/tools/lightpanda}"
TMP_HOME="$(mktemp -d)"
LOG_FILE="$(mktemp)"
PID_FILE="$(mktemp)"

cleanup() {
	stop_gateway_from_pid_file "$PID_FILE"
	rm -f "$LOG_FILE"
	rm -rf "$TMP_HOME"
}
trap cleanup EXIT

mkdir -p "$TMP_HOME/.hermes" "$TMP_HOME/.ruleshield"

PORT="$(start_gateway_for_home "$TMP_HOME" "$LOG_FILE" "$PID_FILE")"
BASE_URL="http://127.0.0.1:${PORT}"

curl -fsS "$BASE_URL/health" >/dev/null

BASE_URL="$BASE_URL" MODEL_PROFILE_ID="$MODEL_PROFILE_ID" RUN_TIMEOUT_SECONDS="$RUN_TIMEOUT_SECONDS" LIGHTPANDA_BIN="$LIGHTPANDA_BIN" \
GATEWAY_LOG_FILE="$LOG_FILE" \
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - <<'PY'
import json
import os
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

base_url = os.environ["BASE_URL"].rstrip("/")
profile_id = os.environ["MODEL_PROFILE_ID"].strip()
timeout_seconds = int(os.environ.get("RUN_TIMEOUT_SECONDS", "300"))
lightpanda_bin = os.environ["LIGHTPANDA_BIN"].strip()
gateway_log_file = os.environ.get("GATEWAY_LOG_FILE", "").strip()


def get_json(path: str) -> dict:
    with urlopen(f"{base_url}{path}", timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base_url}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def event_lines(events: list[dict], tail: int = 60) -> list[str]:
    out = []
    for event in events[-tail:]:
        out.append(str(event.get("text", "")))
    return out


def extract_failure_lines(lines: list[str], limit: int = 12) -> list[str]:
    keys = (
        "error",
        "traceback",
        "exception",
        "failed",
        "status=failed",
        "process exited",
        "code=",
        "auth/login",
        "fallback",
    )
    picked: list[str] = []
    for line in lines:
        low = line.lower()
        if any(k in low for k in keys):
            picked.append(line)
    if not picked:
        picked = lines[-min(20, len(lines)) :]
    return picked[-limit:]

def read_gateway_log_tail(path: str, tail: int = 60) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return ""
    if not lines:
        return ""
    return "\n".join(lines[-tail:])


def safe_get_json(path: str, retries: int = 3, sleep_s: float = 0.8) -> dict:
    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            return get_json(path)
        except Exception as exc:
            last_exc = exc
            time.sleep(sleep_s)
    if last_exc is None:
        raise RuntimeError(f"request failed: {path}")
    raise last_exc


if not os.path.isfile(lightpanda_bin) or not os.access(lightpanda_bin, os.X_OK):
    raise SystemExit(f"lightpanda binary not found/executable: {lightpanda_bin}")

scripts_payload = get_json("/api/test-monitor/scripts")
scripts = scripts_payload.get("scripts")
if not isinstance(scripts, list) or not scripts:
    raise SystemExit("monitor scripts list missing/empty")

health_script_path = ""
for entry in scripts:
    name = str(entry.get("name", ""))
    path = str(entry.get("path", ""))
    if name == "test_training_health_check.sh" and "/demo/" in path:
        health_script_path = path
        break
if not health_script_path:
    for entry in scripts:
        name = str(entry.get("name", ""))
        path = str(entry.get("path", ""))
        if name.startswith("test_training_health_check") and "/demo/" in path:
            health_script_path = path
            break
if not health_script_path:
    raise SystemExit("could not find demo health-check script in monitor scripts")

profiles_payload = get_json("/api/test-monitor/model-profiles")
profiles = profiles_payload.get("profiles")
if not isinstance(profiles, list) or not profiles:
    raise SystemExit("monitor model profiles list missing/empty")
if profile_id not in {str(p.get("id", "")) for p in profiles}:
    raise SystemExit(f"requested model_profile_id not found: {profile_id}")

env = os.environ.copy()
env["LIGHTPANDA_DISABLE_TELEMETRY"] = "true"
fetch = subprocess.run(
    [lightpanda_bin, "fetch", "--dump", "html", f"{base_url}/health"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    timeout=25,
    env=env,
)
if fetch.returncode != 0:
    raise SystemExit(
        f"lightpanda fetch failed (code={fetch.returncode}): "
        f"{fetch.stderr.strip() or fetch.stdout.strip()}"
    )
if "ok" not in (fetch.stdout or "").lower():
    raise SystemExit("lightpanda health fetch did not contain status ok")

try:
    start_payload = post_json(
        "/api/test-monitor/start",
        {"script_path": health_script_path, "model_profile_id": profile_id},
    )
except Exception as exc:
    raise SystemExit(f"monitor start request failed: {exc}")

run_id = str(start_payload.get("run_id", "")).strip()
if not run_id:
    raise SystemExit(f"monitor start did not return run_id: {start_payload}")

deadline = time.time() + timeout_seconds
last_events = []
final_status = ""
poll_errors: list[str] = []

while time.time() < deadline:
    try:
        events_payload = safe_get_json(f"/api/test-monitor/runs/{run_id}/events?limit=1200", retries=2, sleep_s=0.7)
    except Exception as exc:
        poll_errors.append(f"{type(exc).__name__}: {exc}")
        if len(poll_errors) > 8:
            poll_errors = poll_errors[-8:]
        time.sleep(1.0)
        continue
    final_status = str(events_payload.get("status", ""))
    last_events = events_payload.get("events") or []
    if final_status in {"inactive", "failed"}:
        break
    time.sleep(1.5)
else:
    err_block = "\n".join(poll_errors[-5:]) if poll_errors else "[none]"
    tail = "\n".join(event_lines(last_events, tail=30))
    gateway_tail = read_gateway_log_tail(gateway_log_file, tail=80)
    raise SystemExit(
        "monitor run timeout\n"
        f"run_id={run_id}\n"
        f"status={final_status or 'unknown'}\n"
        f"profile_id={profile_id}\n"
        f"poll_errors:\n{err_block}\n"
        f"tail:\n{tail}\n"
        f"gateway_tail:\n{gateway_tail}"
    )

if final_status != "inactive":
    tail_lines = event_lines(last_events, tail=80)
    focus_lines = extract_failure_lines(tail_lines, limit=16)
    focus_block = "\n".join(focus_lines)
    tail_block = "\n".join(tail_lines[-30:])
    gateway_tail = read_gateway_log_tail(gateway_log_file, tail=120)
    raise SystemExit(
        "monitor run failed\n"
        f"run_id={run_id}\n"
        f"status={final_status}\n"
        f"profile_id={profile_id}\n"
        f"script_path={health_script_path}\n"
        "failure_context:\n"
        f"{focus_block}\n"
        "tail:\n"
        f"{tail_block}\n"
        "gateway_tail:\n"
        f"{gateway_tail}"
    )

event_text = "\n".join(str(ev.get("text", "")) for ev in last_events)
if f"id={profile_id}" not in event_text:
    raise SystemExit("monitor run missing expected profile marker in events")
if "== RuleShield Health Check ==" not in event_text:
    raise SystemExit("health-check header not found in monitor run events")
if "Health check completed." not in event_text:
    raise SystemExit("health-check completion line not found in monitor run events")

ruleshield_payload = safe_get_json(f"/api/test-monitor/runs/{run_id}/ruleshield", retries=2, sleep_s=0.7)
if not isinstance(ruleshield_payload, dict):
    raise SystemExit("ruleshield run payload missing")
if str(ruleshield_payload.get("run_id", "")) != run_id:
    raise SystemExit("ruleshield run payload has wrong run_id")

print(f"run_id={run_id} status=inactive profile={profile_id}")
PY

echo "story_monitor_healthcheck_e2e: ok (profile=${MODEL_PROFILE_ID})"
