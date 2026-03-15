# Shared helpers for RuleShield demo scripts
# Source this file, don't execute it directly

AUTH="Authorization: Bearer ${RULESHIELD_TEST_KEY:-sk-test}"
URL="http://localhost:8337/v1/chat/completions"
MODEL="${RULESHIELD_TEST_MODEL:-claude-sonnet-4-6}"

GREEN=$'\033[32m'
YELLOW=$'\033[33m'
CYAN=$'\033[36m'
DIM=$'\033[2m'
RESET=$'\033[0m'

TOTAL=0
RULES=0
LLMS=0
CACHES=0

SEEN_FILE=$(mktemp)
trap "rm -f $SEEN_FILE" EXIT

send() {
    local msg="$1"
    local expected="$2"
    local max_tokens="${3:-30}"

    TOTAL=$((TOTAL + 1))

    # Use python to safely JSON-encode the message
    local json_msg
    json_msg=$(python3 -c "import json; print(json.dumps(\"$msg\"))" 2>/dev/null)
    if [ -z "$json_msg" ]; then
        json_msg="\"$msg\""
    fi

    RESULT=$(curl -s --max-time 30 "$URL" \
        -H "$AUTH" -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":$json_msg}],\"max_tokens\":$max_tokens}" 2>/dev/null)

    MODEL_RESP=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('model','?'))" 2>/dev/null)

    if echo "$MODEL_RESP" | grep -q "ruleshield"; then
        TYPE="RULE"
        COLOR="$GREEN"
        RULES=$((RULES + 1))
    elif grep -qxF "$msg" "$SEEN_FILE" 2>/dev/null; then
        TYPE="CACHE"
        COLOR="$CYAN"
        CACHES=$((CACHES + 1))
    else
        TYPE="LLM "
        COLOR="$YELLOW"
        LLMS=$((LLMS + 1))
    fi

    echo "$msg" >> "$SEEN_FILE"

    printf "  %s[%s]%s  %-55s %s(%s)%s\n" "$COLOR" "$TYPE" "$RESET" "\"$msg\"" "$DIM" "$expected" "$RESET"
    sleep 0.3
}

print_results() {
    echo ""
    echo "------------------------------------------------"
    echo "  Results: $TOTAL requests total"
    printf "    %sRULE%s:  %d  (pattern-matched, zero cost)\n" "$GREEN" "$RESET" "$RULES"
    printf "    %sLLM%s:   %d  (passed to real API)\n" "$YELLOW" "$RESET" "$LLMS"
    printf "    %sCACHE%s: %d  (served from cache)\n" "$CYAN" "$RESET" "$CACHES"
    local saved=$((RULES + CACHES))
    if [ "$TOTAL" -gt 0 ]; then
        local pct=$((saved * 100 / TOTAL))
        printf "    Savings: %d/%d = %s%d%%%s\n" "$saved" "$TOTAL" "$GREEN" "$pct" "$RESET"
    fi
    echo "------------------------------------------------"
    echo ""
}

print_header() {
    local title="$1"
    local desc="$2"
    echo ""
    echo "================================================"
    echo "  RuleShield Demo: $title"
    echo "================================================"
    echo ""
    echo "  $desc"
    echo ""
    printf "  Color key:  %sRULE%s = pattern match  %sLLM%s = passthrough  %sCACHE%s = cached\n" \
        "$GREEN" "$RESET" "$YELLOW" "$RESET" "$CYAN" "$RESET"
    echo ""
    sleep 1
}
