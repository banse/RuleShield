#!/usr/bin/env bash
set -euo pipefail

# Per-step Shadow coverage diagnostic:
# - sends low-cost prompts from Hermes scenario configs
# - records per-step delta in /api/shadow and /api/rules
# - flags rules that hit without persisting shadow comparisons

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"
PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
PROXY_URL="${PROXY_URL:-$(ruleshield_default_proxy_url)}"
MODEL="${MODEL:-gpt-5.1-codex-mini}"
OUTPUT_BASE="${OUTPUT_BASE:-$ROOT_DIR/test-runs/shadow-coverage-check}"
MAX_STEPS="${MAX_STEPS:-}"

SHORT_SCENARIO="${SHORT_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/hermes_user_short.yaml}"
MEDIUM_SCENARIO="${MEDIUM_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/hermes_user_medium.yaml}"
COMPLEX_SCENARIO="${COMPLEX_SCENARIO:-$ROOT_DIR/ruleshield/training_configs/hermes_user_complex.yaml}"

if [[ ! -x "$PYTHON_BIN" ]]; then
	echo "ERROR: python binary not executable: $PYTHON_BIN" >&2
	exit 1
fi

for scenario in "$SHORT_SCENARIO" "$MEDIUM_SCENARIO" "$COMPLEX_SCENARIO"; do
	if [[ ! -f "$scenario" ]]; then
		echo "ERROR: scenario config not found: $scenario" >&2
		exit 1
	fi
done

RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$OUTPUT_BASE/$RUN_STAMP"
mkdir -p "$RUN_DIR"

echo ""
echo "== RuleShield Shadow Coverage Check =="
echo "Proxy:         $PROXY_URL"
echo "Model:         $MODEL"
echo "Run directory: $RUN_DIR"
echo ""

echo "== Step 1/2: Gateway health =="
curl -fsS "$PROXY_URL/health" >"$RUN_DIR/health.json"
cat "$RUN_DIR/health.json"
echo ""

echo "== Step 2/2: Per-step shadow coverage =="
CMD=(
	"$PYTHON_BIN" -u -m ruleshield.shadow_coverage_check
	--proxy-url "$PROXY_URL"
	--model "$MODEL"
	--output-dir "$RUN_DIR"
	--scenario-config "$SHORT_SCENARIO"
	--scenario-config "$MEDIUM_SCENARIO"
	--scenario-config "$COMPLEX_SCENARIO"
)

if [[ -n "$MAX_STEPS" ]]; then
	CMD+=(--max-steps "$MAX_STEPS")
fi

PYTHONPATH="$ROOT_DIR" "${CMD[@]}" | tee "$RUN_DIR/coverage.log"
echo ""

echo "Coverage check completed."
echo "Report: $RUN_DIR/shadow-coverage-report.json"
