#!/bin/bash
# RuleShield Demo Suite -- runs all 3 scenarios
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_DB="${HOME}/.ruleshield/cache.db"

BOLD=$'\033[1m'
RESET=$'\033[0m'

echo ""
echo "${BOLD}=====================================================${RESET}"
echo "${BOLD}  RuleShield Hermes -- Demo Suite${RESET}"
echo "${BOLD}=====================================================${RESET}"
echo ""
echo "  Running 3 scenarios to demonstrate cost optimization."
echo "  Each scenario starts with a fresh cache database."
echo ""
sleep 1

for scenario in test_morning_workflow test_code_review test_research; do
    rm -f "$CACHE_DB"
    bash "$SCRIPT_DIR/${scenario}.sh"

    if command -v ruleshield &>/dev/null; then
        ruleshield stats 2>/dev/null || true
    fi

    sleep 1
done

echo "${BOLD}=====================================================${RESET}"
echo "${BOLD}  All scenarios complete.${RESET}"
echo "${BOLD}=====================================================${RESET}"
echo ""
