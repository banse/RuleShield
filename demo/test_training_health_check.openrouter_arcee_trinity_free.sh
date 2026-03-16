#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"
MODEL="${MODEL:-arcee-ai/trinity-large-preview:free}"
FALLBACK_MODEL="${FALLBACK_MODEL:-stepfun/step-3.5-flash:free}"
MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-4}"
PROXY_URL="${PROXY_URL:-$(ruleshield_default_proxy_url)}"
AUTO_GATEWAY_RESTART="${AUTO_GATEWAY_RESTART:-1}"

# Never self-restart the gateway when launched via the live test monitor,
# otherwise the monitor backend kills itself mid-run.
if [[ "${RULESHIELD_TEST_MONITOR:-0}" == "1" ]]; then
  AUTO_GATEWAY_RESTART="0"
fi

if [[ "$AUTO_GATEWAY_RESTART" == "1" && -x "$ROOT_DIR/demo/gateway_ctl.sh" ]]; then
  "$ROOT_DIR/demo/gateway_ctl.sh" restart >/dev/null
fi

AUTH_METHOD="$("$ROOT_DIR/.venv/bin/python" - <<'PY'
import os
from pathlib import Path

def parse_dotenv(path: Path):
    out = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

if parse_dotenv(Path.home() / ".hermes" / ".env").get("OPENROUTER_API_KEY", "").strip():
    print("OpenRouter API key (~/.hermes/.env)")
else:
    print("OpenRouter (no key in ~/.hermes/.env)")
PY
)"

echo "[profile] id=openrouter_arcee_trinity_free provider=OpenRouter model=$MODEL fallback=$FALLBACK_MODEL"
echo "Auth/Login:    $AUTH_METHOD"
echo "[preflight] start proxy=$PROXY_URL model=$MODEL"

ROUTER_CONFIG_FETCH_OUTPUT="$(PROXY_URL="$PROXY_URL" "$ROOT_DIR/.venv/bin/python" - <<'PY'
import os
import httpx

proxy_url = (os.environ.get("PROXY_URL", "") or "").rstrip("/")
try:
    r = httpx.get(f"{proxy_url}/api/runtime-config", timeout=10.0)
    print(f"debug:router_config_fetch:status={r.status_code}")
    if r.status_code != 200:
        print("router_enabled=unknown")
        raise SystemExit(0)
    payload = r.json()
    val = payload.get("router_enabled")
    if isinstance(val, bool):
        print(f"router_enabled={'true' if val else 'false'}")
    else:
        print("router_enabled=unknown")
except Exception as exc:
    print(f"debug:router_config_fetch:error={type(exc).__name__}:{exc}")
    print("router_enabled=unknown")
PY
)"
ORIGINAL_ROUTER_ENABLED="$(printf '%s\n' "$ROUTER_CONFIG_FETCH_OUTPUT" | awk -F'=' '/^router_enabled=/{print $2}' | tail -n 1)"
echo "$ROUTER_CONFIG_FETCH_OUTPUT"
echo "debug:router_enabled_initial=${ORIGINAL_ROUTER_ENABLED:-unknown}"

restore_router_config() {
  if [[ "${ORIGINAL_ROUTER_ENABLED:-unknown}" == "unknown" ]]; then
    echo "debug:router_restore:skipped=unknown_initial_state"
    return 0
  fi
  local target
  if [[ "$ORIGINAL_ROUTER_ENABLED" == "true" ]]; then
    target="true"
  else
    target="false"
  fi
  PROXY_URL="$PROXY_URL" TARGET_ROUTER_ENABLED="$target" "$ROOT_DIR/.venv/bin/python" - <<'PY' || true
import json
import os
import httpx

proxy_url = (os.environ.get("PROXY_URL", "") or "").rstrip("/")
target = (os.environ.get("TARGET_ROUTER_ENABLED", "true").strip().lower() == "true")
resp = httpx.post(
    f"{proxy_url}/api/runtime-config",
    headers={"Content-Type": "application/json"},
    content=json.dumps({"router_enabled": target}),
    timeout=10.0,
)
print(f"debug:router_restore:status={resp.status_code};target={target}")
if resp.status_code != 200:
    print(f"error:router_restore_failed:{resp.status_code}:{(resp.text or '')[:300]}")
PY
}
trap restore_router_config EXIT

if [[ "$ORIGINAL_ROUTER_ENABLED" == "true" ]]; then
  echo "[preflight] router_enabled=true detected -> temporarily disabling for OpenRouter free-model path"
  PROXY_URL="$PROXY_URL" "$ROOT_DIR/.venv/bin/python" - <<'PY'
import json
import os
import sys
import httpx

proxy_url = (os.environ.get("PROXY_URL", "") or "").rstrip("/")
r = httpx.post(
    f"{proxy_url}/api/runtime-config",
    headers={"Content-Type": "application/json"},
    content=json.dumps({"router_enabled": False}),
    timeout=10.0,
)
print(f"debug:router_disable:status={r.status_code}")
if r.status_code != 200:
    print(f"error:router_disable_failed:{r.status_code}:{(r.text or '')[:300]}")
    raise SystemExit(1)
print("ok:router_disabled_for_preflight")

verify = httpx.get(f"{proxy_url}/api/runtime-config", timeout=10.0)
print(f"debug:router_verify_after_disable:status={verify.status_code}")
if verify.status_code != 200:
    print(f"error:router_verify_failed:{verify.status_code}:{(verify.text or '')[:300]}")
    raise SystemExit(1)
cfg = verify.json() if verify.headers.get("content-type", "").startswith("application/json") else {}
current = cfg.get("router_enabled")
print(f"debug:router_verify_after_disable:value={current}")
if current is not False:
    print(f"error:router_verify_mismatch:expected_false:actual={current}")
    raise SystemExit(1)
PY
elif [[ "$ORIGINAL_ROUTER_ENABLED" == "false" ]]; then
  echo "debug:router_disable:skipped_already_false"
else
  echo "debug:router_disable:skipped_unknown_state"
fi

# Model-specific preflight: verify the currently running gateway can route this
# model to OpenRouter before launching the full health-check workflow.
set +e
PREFLIGHT_OUTPUT="$(PROXY_URL="$PROXY_URL" MODEL="$MODEL" "$ROOT_DIR/.venv/bin/python" - <<'PY'
import json
import os
import sys
import httpx

proxy_url = os.environ.get("PROXY_URL", "").rstrip("/")
model = os.environ.get("MODEL", "arcee-ai/trinity-large-preview:free")

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Reply with exactly: PING"}],
    "stream": False,
}

try:
    resp = httpx.post(
        f"{proxy_url}/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=40.0,
    )
except Exception as exc:
    print(f"error:preflight_connection:{type(exc).__name__}:{exc}")
    sys.exit(2)

resolution = resp.headers.get("x-ruleshield-resolution", "")
routed_model = resp.headers.get("x-ruleshield-routed-model", "")
complexity = resp.headers.get("x-ruleshield-complexity", "")
print(
    "debug:preflight_proxy_headers:"
    f"status={resp.status_code};"
    f"resolution={resolution or '-'};"
    f"routed_model={routed_model or '-'};"
    f"complexity={complexity or '-'}"
)

if resp.status_code != 200:
    txt = (resp.text or "")[:500].replace("\n", " ")
    print(f"error:preflight_http_{resp.status_code}:{txt}")
    sys.exit(3)

try:
    data = resp.json()
except Exception:
    print("error:preflight_invalid_json")
    sys.exit(4)

err = data.get("error")
if err:
    text = str(err).lower()
    if "not supported when using codex with a chatgpt account" in text:
        print("error:preflight_routed_to_chatgpt_codex")
        sys.exit(5)
    print(f"error:preflight_error_payload:{str(err)[:400]}")
    sys.exit(6)

print("ok")
PY
)"
PREFLIGHT_RC=$?
set -e
PREFLIGHT_LAST_LINE="$(printf '%s\n' "${PREFLIGHT_OUTPUT:-}" | awk 'NF {line=$0} END {print line}')"
echo "[preflight] rc=$PREFLIGHT_RC"
if [[ -n "${PREFLIGHT_OUTPUT:-}" ]]; then
  echo "[preflight] output=$PREFLIGHT_OUTPUT"
fi

if [[ "$PREFLIGHT_RC" -ne 0 || "${PREFLIGHT_LAST_LINE:-}" != "ok" || "${PREFLIGHT_OUTPUT:-}" == *"error:"* ]]; then
  echo "ERROR: Arcee/OpenRouter preflight failed (rc=$PREFLIGHT_RC): ${PREFLIGHT_OUTPUT:-<empty>}" >&2
  echo "Hint: wrong gateway instance might be running. Try:" >&2
  echo "  $ROOT_DIR/demo/gateway_ctl.sh kill-all && $ROOT_DIR/demo/gateway_ctl.sh start" >&2
  exit 1
fi

echo "[preflight] success"

MODEL="$MODEL" \
FALLBACK_MODEL="$FALLBACK_MODEL" \
MAX_ITER_HEALTH="$MAX_ITER_HEALTH" \
PROXY_URL="$PROXY_URL" \
bash "$ROOT_DIR/demo/test_training_health_check.sh"
