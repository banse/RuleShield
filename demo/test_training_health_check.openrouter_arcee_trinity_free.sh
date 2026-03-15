#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${MODEL:-arcee-ai/trinity-large-preview:free}"
FALLBACK_MODEL="${FALLBACK_MODEL:-stepfun/step-3.5-flash:free}"
MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-4}"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:8337}"
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

if (os.getenv("RULESHIELD_OPENROUTER_API_KEY") or "").strip():
    print("OpenRouter API key (RULESHIELD_OPENROUTER_API_KEY)")
elif (os.getenv("OPENROUTER_API_KEY") or "").strip():
    print("OpenRouter API key (OPENROUTER_API_KEY)")
elif parse_dotenv(Path.home() / ".hermes" / ".env").get("OPENROUTER_API_KEY", "").strip():
    print("OpenRouter API key (~/.hermes/.env)")
elif parse_dotenv(Path.home() / ".ruleshield" / ".env").get("OPENROUTER_API_KEY", "").strip():
    print("OpenRouter API key (~/.ruleshield/.env)")
else:
    print("OpenRouter (no key detected)")
PY
)"

echo "[profile] id=openrouter_arcee_trinity_free provider=OpenRouter model=$MODEL fallback=$FALLBACK_MODEL"
echo "Auth/Login:    $AUTH_METHOD"

# Model-specific preflight: verify the currently running gateway can route this
# model to OpenRouter before launching the full health-check workflow.
PREFLIGHT_CODE="$("$ROOT_DIR/.venv/bin/python" - <<'PY'
import json
import os
import sys
import httpx

proxy_url = os.environ.get("PROXY_URL", "http://127.0.0.1:8337").rstrip("/")
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

if [[ "$PREFLIGHT_CODE" != "ok" ]]; then
  echo "ERROR: Arcee/OpenRouter preflight failed: $PREFLIGHT_CODE" >&2
  echo "Hint: wrong gateway instance might be running. Try:" >&2
  echo "  $ROOT_DIR/demo/gateway_ctl.sh kill-all && $ROOT_DIR/demo/gateway_ctl.sh start" >&2
  exit 1
fi

MODEL="$MODEL" \
FALLBACK_MODEL="$FALLBACK_MODEL" \
MAX_ITER_HEALTH="$MAX_ITER_HEALTH" \
PROXY_URL="$PROXY_URL" \
bash "$ROOT_DIR/demo/test_training_health_check.sh"
