#!/usr/bin/env bash
set -euo pipefail

# Hermes-first RuleShield training suite:
# 1) Gateway health check
# 2) Reusable baseline health scenario
# 3) Short Hermes user scenario (few rule families)
# 4) Medium Hermes user scenario (broader rule families)
# 5) Complex Hermes user scenario (widest rule families + variants)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"
PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
PROXY_URL="${PROXY_URL:-$(ruleshield_default_proxy_url)}"
MODEL="${MODEL:-gpt-5.1-codex-mini}"
FALLBACK_MODEL="${FALLBACK_MODEL:-gpt-4.1-mini}"
OUTPUT_BASE="${OUTPUT_BASE:-$ROOT_DIR/test-runs/training-hermes-users}"

HEALTH_SCENARIO="${HEALTH_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/health_check_baseline.yaml}"
SHORT_SCENARIO="${SHORT_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/hermes_user_short.yaml}"
MEDIUM_SCENARIO="${MEDIUM_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/hermes_user_medium.yaml}"
COMPLEX_SCENARIO="${COMPLEX_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/hermes_user_complex.yaml}"

MAX_ITER_HEALTH="${MAX_ITER_HEALTH:-2}"
MAX_ITER_SHORT="${MAX_ITER_SHORT:-4}"
MAX_ITER_MEDIUM="${MAX_ITER_MEDIUM:-6}"
MAX_ITER_COMPLEX="${MAX_ITER_COMPLEX:-8}"

MAX_PROMPTS_SHORT="${MAX_PROMPTS_SHORT:-6}"
MAX_PROMPTS_MEDIUM="${MAX_PROMPTS_MEDIUM:-8}"
MAX_PROMPTS_COMPLEX="${MAX_PROMPTS_COMPLEX:-12}"

if [[ ! -x "$PYTHON_BIN" ]]; then
	echo "ERROR: python binary not executable: $PYTHON_BIN" >&2
	exit 1
fi

for scenario in "$HEALTH_SCENARIO" "$SHORT_SCENARIO" "$MEDIUM_SCENARIO" "$COMPLEX_SCENARIO"; do
	if [[ ! -f "$scenario" ]]; then
		echo "ERROR: scenario config not found: $scenario" >&2
		exit 1
	fi
done

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

print_stage() {
	local heading="$1"
	local summary_json="$2"
	echo ""
	echo "== $heading transcript output =="
	print_transcript "$summary_json"
	echo ""
}

latest_summary() {
	local root="$1"
	find "$root" -type f -name 'ruleshield-summary.json' | sort | tail -n 1
}

echo ""
echo "== Hermes-First RuleShield Training Suite =="
echo "Proxy:         $PROXY_URL"
echo "Model:         $MODEL"
echo "Auth/Login:    $AUTH_METHOD"
echo "Run directory: $RUN_DIR"
echo ""

echo "== Step 1/5: Gateway health check =="
if ! curl -fsS "$PROXY_URL/health" >"$RUN_DIR/health.json"; then
	echo "ERROR: RuleShield gateway is not reachable at $PROXY_URL" >&2
	exit 1
fi
cat "$RUN_DIR/health.json"
echo ""

echo "== Step 2/5: Baseline health-check scenario =="
run_training_with_fallback health \
	--scenario-config "$HEALTH_SCENARIO" \
	--max-iterations "$MAX_ITER_HEALTH" \
	--output-dir "$RUN_DIR/health-check"
print_stage "Health-check" "$(latest_summary "$RUN_DIR/health-check")"

echo "== Step 3/5: Hermes user short scenario =="
run_training_with_fallback short \
	--scenario-config "$SHORT_SCENARIO" \
	--max-prompts "$MAX_PROMPTS_SHORT" \
	--max-iterations "$MAX_ITER_SHORT" \
	--output-dir "$RUN_DIR/hermes-short"
print_stage "Hermes short" "$(latest_summary "$RUN_DIR/hermes-short")"

echo "== Step 4/5: Hermes user medium scenario =="
run_training_with_fallback medium \
	--scenario-config "$MEDIUM_SCENARIO" \
	--max-prompts "$MAX_PROMPTS_MEDIUM" \
	--max-iterations "$MAX_ITER_MEDIUM" \
	--output-dir "$RUN_DIR/hermes-medium"
print_stage "Hermes medium" "$(latest_summary "$RUN_DIR/hermes-medium")"

echo "== Step 5/5: Hermes user complex scenario =="
run_training_with_fallback complex \
	--scenario-config "$COMPLEX_SCENARIO" \
	--max-prompts "$MAX_PROMPTS_COMPLEX" \
	--max-iterations "$MAX_ITER_COMPLEX" \
	--output-dir "$RUN_DIR/hermes-complex"
print_stage "Hermes complex" "$(latest_summary "$RUN_DIR/hermes-complex")"

echo "== Final live snapshot =="
curl -s "$PROXY_URL/api/shadow" >"$RUN_DIR/shadow-final.json" || true
curl -s "$PROXY_URL/api/rules" >"$RUN_DIR/rules-final.json" || true
echo "shadow: $RUN_DIR/shadow-final.json"
echo "rules:  $RUN_DIR/rules-final.json"
echo ""

echo "Suite completed."
