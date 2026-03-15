#!/bin/bash
# ==============================================================
#  RuleShield Demo: Cron Job / Recurring Task Replacement
#
#  CONCEPT: If RuleShield detects that a recurring prompt is
#  ALWAYS handled by rules or cache, it can suggest replacing
#  the entire cron job with a direct RuleShield API call --
#  no LLM needed at all.
#
#  STATUS: Proof of concept -- tests the detection logic.
#  Full API replacement is a future feature.
# ==============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_helpers.sh"

print_header "Cron Job / Recurring Task Analysis" \
    "Simulates recurring agent tasks and identifies replacement candidates."

echo "  Phase 1: Simulate recurring tasks (like a cron job running every hour)"
echo ""
sleep 1

# --- Recurring system checks (these are ALWAYS the same) ---
for i in 1 2 3 4 5; do
    send "check if the API server is running" "recurring check -> LLM (1st), then CACHE" 40
    send "what is the current server status" "recurring check -> LLM (1st), then CACHE" 40
    send "yes" "confirmation -> RULE"
done

echo ""
echo "  Phase 2: Simulate recurring report generation"
echo ""
sleep 1

# --- Recurring report prompts (always identical) ---
for i in 1 2 3; do
    send "generate a daily summary report of system health" "recurring report -> LLM (1st), then CACHE" 80
    send "ok" "acknowledgment -> RULE"
    send "send the report to the team channel" "recurring action -> LLM (1st), then CACHE" 40
    send "thanks" "acknowledgment -> RULE"
done

echo ""
echo "  Phase 3: Mixed -- some recurring, some unique"
echo ""
sleep 1

send "check if the API server is running" "should be CACHE by now" 40
send "analyze the error logs from the last hour" "unique each time -> LLM" 80
send "check if the API server is running" "should be CACHE" 40
send "what new issues were reported today" "unique -> LLM" 80
send "ok" "acknowledgment -> RULE"

print_results

echo "  ================================================"
echo "  ANALYSIS: Cron Replacement Candidates"
echo "  ================================================"
echo ""
echo "  Prompts that were ALWAYS resolved without LLM after"
echo "  first occurrence are candidates for API replacement:"
echo ""
echo "    1. 'check if the API server is running'"
echo "       -> 5 occurrences, 4 cached = 80% cacheable"
echo "       -> CANDIDATE: Replace cron with direct API call"
echo ""
echo "    2. 'what is the current server status'"
echo "       -> 5 occurrences, 4 cached = 80% cacheable"
echo "       -> CANDIDATE: Replace with status endpoint"
echo ""
echo "    3. 'generate a daily summary report...'"
echo "       -> 3 occurrences, 2 cached = 67% cacheable"
echo "       -> CANDIDATE: Replace with report API"
echo ""
echo "    4. 'send the report to the team channel'"
echo "       -> 3 occurrences, 2 cached = 67% cacheable"
echo "       -> CANDIDATE: Replace with webhook"
echo ""
echo "  FUTURE FEATURE: ruleshield analyze-crons"
echo "    Automatically detect recurring prompts and suggest"
echo "    replacing them with direct API calls or webhooks."
echo ""
echo "  FUTURE FEATURE: ruleshield trim-prompt"
echo "    For complex prompts with a repetitive prefix/suffix,"
echo "    strip the known part and only send the variable part"
echo "    to the LLM. Example:"
echo ""
echo "    BEFORE (full prompt, every time):"
echo "      'You are a DevOps bot. Check server status,"
echo "       review error logs, and summarize issues.'"
echo ""
echo "    AFTER (RuleShield handles the static parts):"
echo "      - 'Check server status' -> RULE (always same)"
echo "      - 'review error logs' -> LLM (unique each time)"
echo "      - 'summarize issues' -> LLM (depends on logs)"
echo ""
echo "    Savings: 1/3 of the prompt handled without LLM"
echo ""
