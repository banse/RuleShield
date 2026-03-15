#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${MODEL:-stepfun/step-3.5-flash:free}"
FALLBACK_MODEL="${FALLBACK_MODEL:-arcee-ai/trinity-large-preview:free}"

MODEL="$MODEL" FALLBACK_MODEL="$FALLBACK_MODEL" bash "$ROOT_DIR/demo/test_training_vibecoder_suite.sh"
