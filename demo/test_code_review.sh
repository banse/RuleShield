#!/bin/bash
# Code Review Session -- reviewing a PR
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_helpers.sh"

print_header "Code Review Session" \
    "A developer reviews a PR touching auth.py and models.py."

send "hi" "greeting -> RULE"
send "show me the diff for this PR" "tool use -> LLM" 100
send "ok" "acknowledgment -> RULE"
send "what changed in auth.py?" "analysis -> LLM" 100
send "and in models.py?" "analysis -> LLM" 100
send "got it" "acknowledgment -> RULE"
send "any security concerns with these changes?" "analysis -> LLM" 100
send "what about the auth.py changes specifically?" "similar -> LLM" 100
send "thanks" "acknowledgment -> RULE"
send "yes" "confirmation -> RULE"
send "show me the diff for this PR" "REPEAT -> expect CACHE" 100
send "any security concerns with these changes?" "REPEAT -> expect CACHE" 100
send "bye" "goodbye -> RULE"

print_results
