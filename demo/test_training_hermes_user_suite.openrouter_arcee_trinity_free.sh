#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${MODEL:-arcee-ai/trinity-large-preview:free}"
FALLBACK_MODEL="${FALLBACK_MODEL:-stepfun/step-3.5-flash:free}"
SCENARIO_DIR="$ROOT_DIR/ruleshield/training_configs"

MODEL="$MODEL" \
FALLBACK_MODEL="$FALLBACK_MODEL" \
SHORT_SCENARIO="${SHORT_SCENARIO:-$SCENARIO_DIR/hermes_user_arcee_short.yaml}" \
MEDIUM_SCENARIO="${MEDIUM_SCENARIO:-$SCENARIO_DIR/hermes_user_arcee_medium.yaml}" \
COMPLEX_SCENARIO="${COMPLEX_SCENARIO:-$SCENARIO_DIR/hermes_user_arcee_complex.yaml}" \
MAX_PROMPTS_SHORT="${MAX_PROMPTS_SHORT:-4}" \
MAX_PROMPTS_MEDIUM="${MAX_PROMPTS_MEDIUM:-6}" \
MAX_PROMPTS_COMPLEX="${MAX_PROMPTS_COMPLEX:-9}" \
bash "$ROOT_DIR/demo/test_training_hermes_user_suite.sh"
