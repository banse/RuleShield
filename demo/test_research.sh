#!/bin/bash
# Research / Learning Session -- learning about Kubernetes
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_helpers.sh"

print_header "Research / Learning Session" \
    "A developer learns about Kubernetes with Hermes Agent."

send "hello" "greeting -> RULE"
send "explain kubernetes to me in simple terms" "explanation -> LLM" 100
send "ok" "acknowledgment -> RULE"
send "what about docker vs kubernetes?" "comparison -> LLM" 100
send "explain kubernetes to me in simple terms" "REPEAT -> expect CACHE" 100
send "thanks" "acknowledgment -> RULE"
send "how do pods work in kubernetes?" "explanation -> LLM" 100
send "and what are services in kubernetes?" "explanation -> LLM" 100
send "yes" "confirmation -> RULE"
send "how do pods work in kubernetes?" "REPEAT -> expect CACHE" 100
send "what about docker vs kubernetes?" "REPEAT -> expect CACHE" 100
send "got it" "acknowledgment -> RULE"
send "what should I learn next after kubernetes?" "planning -> LLM" 60
send "bye" "goodbye -> RULE"

print_results
