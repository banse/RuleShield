#!/usr/bin/env bash
set -euo pipefail

# RuleShield training suite:
# 1) Gateway health check
# 2) Initial reusable health-check scenario
# 3) Full baseline scenario (vibecoder dashboard)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"
PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
PROXY_URL="${PROXY_URL:-$(ruleshield_default_proxy_url)}"
MODEL="${MODEL:-gpt-5.1-codex-mini}"
FALLBACK_MODEL="${FALLBACK_MODEL:-gpt-4.1-mini}"
OUTPUT_BASE="${OUTPUT_BASE:-$ROOT_DIR/test-runs/training-suite}"
MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-2}"
MAX_ITER_FULL="${MAX_ITER_FULL:-8}"
MAX_PROMPTS_FULL="${MAX_PROMPTS_FULL:-12}"
SCENARIO_CONFIG="${SCENARIO_CONFIG:-$ROOT_DIR/ruleshield/training_configs/health_check_baseline.yaml}"
FULL_SCENARIO="${FULL_SCENARIO:-vibecoder_stats_dashboard}"

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
	local label="$1"
	shift
	local scenario_args=("$@")
	local primary_log="$RUN_DIR/${label}-primary.log"
	local fallback_log="$RUN_DIR/${label}-fallback.log"

	set +e
	run_training "${scenario_args[@]}" --model "$MODEL" 2>&1 | tee "$primary_log"
	local rc=$?
	set -e

	if [[ $rc -eq 0 ]]; then
		return 0
	fi

	if rg -q "Error code: 402|Prompt tokens limit exceeded|requires more credits" "$primary_log"; then
		echo ""
		echo "[fallback] scope=$label reason=credits_or_token_limit from_model=$MODEL to_model=$FALLBACK_MODEL"
		echo "[fallback] scope=$label action=retry_with_fallback_model"
		set +e
		run_training "${scenario_args[@]}" --model "$FALLBACK_MODEL" 2>&1 | tee "$fallback_log"
		rc=$?
		set -e
		echo "[fallback] scope=$label result=completed exit_code=$rc log=$fallback_log"
		return $rc
	fi

	return $rc
}

echo ""
echo "== RuleShield Training Suite =="
echo "Proxy:         $PROXY_URL"
echo "Model:         $MODEL"
echo "Auth/Login:    $AUTH_METHOD"
echo "Run directory: $RUN_DIR"
echo ""

echo "== Step 1/3: Gateway health check =="
if ! curl -fsS "$PROXY_URL/health" >"$RUN_DIR/health.json"; then
	echo "ERROR: RuleShield gateway is not reachable at $PROXY_URL" >&2
	exit 1
fi
cat "$RUN_DIR/health.json"
echo ""

echo "== Step 2/3: Initial health-check training =="
run_training_with_fallback health \
	--scenario-config "$SCENARIO_CONFIG" \
	--max-iterations "$MAX_ITER_HEALTH" \
	--output-dir "$RUN_DIR/health-check"
echo ""
HEALTH_SUMMARY_JSON="$(find "$RUN_DIR/health-check" -type f -name 'ruleshield-summary.json' | sort | tail -n 1)"
echo "== Health-check transcript output =="
print_transcript "$HEALTH_SUMMARY_JSON"
echo ""

echo "== Step 3/3: Full baseline training (vibecoder dashboard) =="
run_training_with_fallback vibecoder \
	--scenario "$FULL_SCENARIO" \
	--max-prompts "$MAX_PROMPTS_FULL" \
	--max-iterations "$MAX_ITER_FULL" \
	--output-dir "$RUN_DIR/vibecoder-full"
echo ""
FULL_SUMMARY_JSON="$(find "$RUN_DIR/vibecoder-full" -type f -name 'ruleshield-summary.json' | sort | tail -n 1)"
echo "== Vibecoder transcript output =="
print_transcript "$FULL_SUMMARY_JSON"
echo ""

echo "== Final live snapshot =="
curl -s "$PROXY_URL/api/shadow" >"$RUN_DIR/shadow-final.json" || true
curl -s "$PROXY_URL/api/rules" >"$RUN_DIR/rules-final.json" || true
echo "shadow: $RUN_DIR/shadow-final.json"
echo "rules:  $RUN_DIR/rules-final.json"
echo ""

echo "Suite completed."
