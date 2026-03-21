#!/usr/bin/env bash
# Run all auto-generated model e2e tests.
# Assumes RuleShield proxy is already running (or set RULESHIELD_PROXY_URL).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STORIES_DIR="$ROOT_DIR/tests/stories/auto"

if [ ! -d "$STORIES_DIR" ] || [ -z "$(ls -A "$STORIES_DIR"/story_model_*.sh 2>/dev/null)" ]; then
    echo "No auto-generated model stories found in $STORIES_DIR"
    echo "Run: python scripts/generate_model_tests.py"
    exit 1
fi

PASS=0
FAIL=0
TOTAL=0

for script in "$STORIES_DIR"/story_model_*.sh; do
    TOTAL=$((TOTAL + 1))
    echo ""
    echo "=== [$TOTAL] Running: $(basename "$script") ==="
    if bash "$script"; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        echo "FAILED: $script"
    fi
done

echo ""
echo "========================================="
echo "Model Suite Results: $PASS passed, $FAIL failed (of $TOTAL)"
echo "========================================="
[ "$FAIL" -eq 0 ]
