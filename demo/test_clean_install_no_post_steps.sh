#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"

PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
MONITOR_PROFILE_ID="${MONITOR_PROFILE_ID:-}"

resolve_installed_proxy_url() {
	PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - <<'PY'
from ruleshield.config import load_settings
settings = load_settings()
print(f"http://127.0.0.1:{settings.port}")
PY
}

echo "== Demo: clean install with no post-install tweaks =="

# Install path must be idempotent.
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m ruleshield.cli init --hermes >/dev/null
PROXY_URL="$(resolve_installed_proxy_url)"
PORT="${PROXY_URL##*:}"
echo "Proxy (from installed config): $PROXY_URL"

# Use normal gateway lifecycle (not test-only uvicorn start).
PORT="$PORT" "$ROOT_DIR/demo/gateway_ctl.sh" restart >/dev/null

echo "== Step 1/3: health =="
curl -fsS "${PROXY_URL%/}/health" >/dev/null
echo "ok"

echo "== Step 2/3: monitor scripts endpoint =="
SCRIPTS_JSON="$(curl -fsS "${PROXY_URL%/}/api/test-monitor/scripts")"
SCRIPTS_JSON="$SCRIPTS_JSON" "$PYTHON_BIN" - <<'PY'
import json
import os

payload = json.loads(os.environ["SCRIPTS_JSON"])
scripts = payload.get("scripts")
if not isinstance(scripts, list):
    raise SystemExit("monitor scripts payload missing scripts list")
names = {str(item.get("name", "")) for item in scripts if isinstance(item, dict)}
if "test_training_health_check.sh" not in names:
    raise SystemExit("monitor scripts did not include test_training_health_check.sh")
print("ok")
PY

echo "== Step 3/3: runtime config endpoint =="
curl -fsS "${PROXY_URL%/}/api/runtime-config" >/dev/null
echo "ok"

echo "== Step 4/4: monitor start + run =="
PROXY_URL="$PROXY_URL" MONITOR_PROFILE_ID="$MONITOR_PROFILE_ID" "$PYTHON_BIN" - <<'PY'
import json
import os
import time
from urllib.request import Request, urlopen

base = os.environ["PROXY_URL"].rstrip("/")
requested_profile = os.environ.get("MONITOR_PROFILE_ID", "").strip()

def get_json(path: str) -> dict:
    with urlopen(f"{base}{path}", timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_json(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{base}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

scripts_payload = get_json("/api/test-monitor/scripts")
scripts = scripts_payload.get("scripts")
if not isinstance(scripts, list) or not scripts:
    raise SystemExit("monitor scripts endpoint returned no scripts")

script_path = ""
for item in scripts:
    if not isinstance(item, dict):
        continue
    if str(item.get("name", "")) == "test_training_health_check.sh" and "/demo/" in str(item.get("path", "")):
        script_path = str(item["path"])
        break
if not script_path:
    raise SystemExit("could not resolve demo/test_training_health_check.sh from monitor scripts payload")

profiles_payload = get_json("/api/test-monitor/model-profiles")
profiles = profiles_payload.get("profiles")
if not isinstance(profiles, list) or not profiles:
    raise SystemExit("monitor model profiles endpoint returned no profiles")

profile_ids = {str(item.get("id", "")) for item in profiles if isinstance(item, dict)}
profile_id = requested_profile or str(profiles_payload.get("default_profile_id", "")).strip()
if not profile_id:
    raise SystemExit("could not resolve monitor profile id")
if profile_id not in profile_ids:
    raise SystemExit(f"monitor profile not found: {profile_id}")

start_payload = post_json(
    "/api/test-monitor/start",
    {"script_path": script_path, "model_profile_id": profile_id},
)
run_id = str(start_payload.get("run_id", "")).strip()
if not run_id:
    raise SystemExit(f"monitor start failed: {start_payload}")

deadline = time.time() + 360
last_events = []
status = ""
while time.time() < deadline:
    events_payload = get_json(f"/api/test-monitor/runs/{run_id}/events?limit=600")
    status = str(events_payload.get("status", ""))
    last_events = events_payload.get("events") or []
    if status in {"inactive", "failed"}:
        break
    time.sleep(1.5)
else:
    raise SystemExit(f"monitor run timeout (run_id={run_id})")

if status != "inactive":
    tail = "\n".join(str(item.get("text", "")) for item in last_events[-25:])
    raise SystemExit(f"monitor run failed (run_id={run_id}, status={status})\n{tail}")

print(f"ok run_id={run_id} profile={profile_id}")
PY

echo "demo_clean_install_no_post_steps: ok"
