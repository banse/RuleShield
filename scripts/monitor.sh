#!/bin/bash
# RuleShield Monitor -- shows only request resolutions
# Usage: bash scripts/monitor.sh
#
# Output format:
#   [HH:MM:SS] RULE     "hello"                     -> Simple Greeting (0ms)
#   [HH:MM:SS] CACHE    "what is python?"            -> cached (2ms)
#   [HH:MM:SS] LLM      "explain kubernetes..."      -> claude-sonnet-4-6 (3200ms)
#   [HH:MM:SS] PASS     "complex codex request..."   -> gpt-5.4 (5100ms)

LOGFILE="${1:-/tmp/ruleshield-proxy.log}"

GREEN=$'\033[32m'
CYAN=$'\033[36m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'
MAGENTA=$'\033[35m'
DIM=$'\033[2m'
RESET=$'\033[0m'

echo ""
echo "${MAGENTA}RuleShield Monitor${RESET} -- watching $LOGFILE"
echo "${DIM}Ctrl+C to stop${RESET}"
echo ""

tail -f "$LOGFILE" 2>/dev/null | while IFS= read -r line; do
    # Skip aiosqlite noise
    echo "$line" | grep -qE "aiosqlite|operation func|executing func" && continue

    timestamp=$(echo "$line" | grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
    [ -z "$timestamp" ] && continue

    # Rule hit
    if echo "$line" | grep -q "rule hit\|Rule hit"; then
        prompt=$(echo "$line" | sed -n 's/.*rule hit: \(.*\) -> .*/\1/p' | head -c 40)
        rule=$(echo "$line" | sed -n 's/.* -> \(.*\)/\1/p')
        printf "[%s] ${GREEN}RULE${RESET}     %-42s -> %s\n" "$timestamp" "\"$prompt\"" "$rule"
        echo "[$(date +%H:%M:%S)] RULE     \"$prompt\" -> $rule" >> ~/.ruleshield/monitor.log

    # Cache hit
    elif echo "$line" | grep -q "cache hit\|Cache hit"; then
        prompt=$(echo "$line" | sed -n 's/.*cache hit for: \(.*\)/\1/p' | head -c 40)
        printf "[%s] ${CYAN}CACHE${RESET}    %-42s -> cached\n" "$timestamp" "\"$prompt\""
        echo "[$(date +%H:%M:%S)] CACHE    \"$prompt\" -> cached" >> ~/.ruleshield/monitor.log

    # Codex passthrough
    elif echo "$line" | grep -q "Codex passthrough POST"; then
        model=$(echo "$line" | sed -n 's/.*(model=\(.*\))/\1/p')
        printf "[%s] ${BLUE}PASS${RESET}     %-42s -> %s\n" "$timestamp" "[codex request]" "$model"

    # Codex stream completed
    elif echo "$line" | grep -q "Codex stream completed"; then
        tokens=$(echo "$line" | grep -oE '[0-9]+ in / [0-9]+ out')
        cost=$(echo "$line" | grep -oE '\$[0-9.]+')
        latency=$(echo "$line" | grep -oE '[0-9]+ms')
        printf "[%s] ${BLUE}PASS${RESET}     %-42s -> %s %s %s\n" "$timestamp" "[codex completed]" "$tokens tokens" "$cost" "$latency"
        echo "[$(date +%H:%M:%S)] PASS     codex $tokens $cost $latency" >> ~/.ruleshield/monitor.log

    # LLM passthrough (non-codex)
    elif echo "$line" | grep -qE "POST /v1/chat/completions.*200"; then
        printf "[%s] ${YELLOW}LLM${RESET}      %-42s -> forwarded\n" "$timestamp" "[chat completion]"

    # Router
    elif echo "$line" | grep -q "Router:"; then
        detail=$(echo "$line" | sed -n 's/.*Router: \(.*\)/\1/p')
        printf "[%s] ${MAGENTA}ROUTE${RESET}    %-42s\n" "$timestamp" "$detail"

    # Template hit
    elif echo "$line" | grep -q "Template match"; then
        printf "[%s] ${GREEN}TMPL${RESET}     %-42s -> template cached\n" "$timestamp" "[template match]"
        echo "[$(date +%H:%M:%S)] TMPL     template match" >> ~/.ruleshield/monitor.log
    fi
done
