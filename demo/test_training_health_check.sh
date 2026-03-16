#!/usr/bin/env bash
set -euo pipefail

# Standalone RuleShield health-check training run.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
PROXY_URL="${PROXY_URL:-$(ruleshield_default_proxy_url)}"
MODEL="${MODEL:-gpt-5.1-codex-mini}"
FALLBACK_MODEL="${FALLBACK_MODEL:-gpt-4.1-mini}"
MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-2}"
SCENARIO_CONFIG="${SCENARIO_CONFIG:-$ROOT_DIR/ruleshield/training_configs/health_check_baseline.yaml}"
OUTPUT_BASE="${OUTPUT_BASE:-$ROOT_DIR/test-runs/training-health-check}"

if [[ ! -x "$PYTHON_BIN" ]]; then
	echo "ERROR: python binary not executable: $PYTHON_BIN" >&2
	exit 1
fi

if [[ ! -f "$SCENARIO_CONFIG" ]]; then
	echo "ERROR: health-check scenario config not found: $SCENARIO_CONFIG" >&2
	exit 1
fi

detect_auth_method() {
	"$PYTHON_BIN" - <<'PY'
import os
from pathlib import Path

model = (os.getenv("MODEL") or "").strip().lower()
provider_hint = (os.getenv("RULESHIELD_TEST_PROVIDER") or "").strip().lower()

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

def is_openrouter_route() -> bool:
    if provider_hint == "openrouter":
        return True
    if model.endswith(":free"):
        return True
    return "/" in model

if is_openrouter_route():
    if parse_dotenv(Path.home() / ".hermes" / ".env").get("OPENROUTER_API_KEY", "").strip():
        print("OpenRouter API key (~/.hermes/.env)")
    else:
        print("OpenRouter (no key in ~/.hermes/.env)")
else:
    if parse_dotenv(Path.home() / ".hermes" / ".env").get("OPENAI_API_KEY", "").strip():
        print("OpenAI API key (~/.hermes/.env)")
    else:
        print("OpenAI (no key in ~/.hermes/.env)")
PY
}

AUTH_METHOD="$(detect_auth_method)"

RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$OUTPUT_BASE/$RUN_STAMP"
mkdir -p "$RUN_DIR"

print_transcript() {
	local summary_json="$1"
	if [[ -z "$summary_json" || ! -f "$summary_json" ]]; then
		echo "No transcript summary found."
		return
	fi

	"$ROOT_DIR/.venv/bin/python" - "$summary_json" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
try:
    data = json.loads(summary_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"Could not read transcript summary: {exc}")
    raise SystemExit(0)

transcript = data.get("transcript") or []
if not transcript:
    print("No transcript entries found.")
    raise SystemExit(0)

print("== Prompt/Response Transcript ==")
for idx, step in enumerate(transcript, start=1):
    step_id = str(step.get("step_id", f"step_{idx}"))
    prompt = str(step.get("prompt", "")).strip() or "[empty]"
    response = str(step.get("response_text", "")).strip() or "[empty]"
    error = step.get("error")
    probe_status = step.get("probe_status")
    print(f"PROMPT {idx} ({step_id}): {prompt}")
    print(f"RESPONSE {idx} ({step_id}): {response}")
    if error:
        print(f"ERROR {idx} ({step_id}): {error}")
    if probe_status:
        print(f"PROBE {idx} ({step_id}): {probe_status}")
PY
}

run_training() {
	PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -u -m ruleshield.cli run-prompt-training "$@"
}

run_training_with_fallback() {
	local scenario_args=("$@")
	local primary_log="$RUN_DIR/primary-training.log"
	local fallback_log="$RUN_DIR/fallback-training.log"

	set +e
	run_training "${scenario_args[@]}" --model "$MODEL" 2>&1 | tee "$primary_log"
	local rc=$?
	set -e

	if [[ $rc -eq 0 ]]; then
		return 0
	fi

	if rg -q "Error code: 402|Prompt tokens limit exceeded|requires more credits" "$primary_log"; then
		echo ""
		echo "[fallback] reason=credits_or_token_limit from_model=$MODEL to_model=$FALLBACK_MODEL"
		echo "[fallback] action=retry_with_fallback_model"
		set +e
		run_training "${scenario_args[@]}" --model "$FALLBACK_MODEL" 2>&1 | tee "$fallback_log"
		rc=$?
		set -e
		echo "[fallback] result=completed exit_code=$rc log=$fallback_log"
		return $rc
	fi

	return $rc
}

echo ""
echo "== RuleShield Health Check =="
echo "Proxy:         $PROXY_URL"
echo "Model:         $MODEL"
echo "Auth/Login:    $AUTH_METHOD"
echo "Run directory: $RUN_DIR"
echo ""

echo "== Step 1/2: Gateway health =="
curl -fsS "$PROXY_URL/health" >"$RUN_DIR/health.json"
cat "$RUN_DIR/health.json"
echo ""

echo "== Step 2/2: Health-check training scenario =="
run_training_with_fallback \
	--scenario-config "$SCENARIO_CONFIG" \
	--max-iterations "$MAX_ITER_HEALTH" \
	--output-dir "$RUN_DIR/training"
echo ""

SUMMARY_JSON="$(find "$RUN_DIR/training" -type f -name 'ruleshield-summary.json' | sort | tail -n 1)"
echo "== Transcript output =="
print_transcript "$SUMMARY_JSON"
echo ""

echo "Health check completed."
