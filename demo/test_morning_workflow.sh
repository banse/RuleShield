#!/bin/bash
# Developer Morning Workflow -- debugging a FastAPI app
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_helpers.sh"

print_header "Developer Morning Workflow" \
    "A developer debugs a FastAPI TODO app with Hermes Agent."

send "hey" "greeting -> RULE"
send "what did we work on yesterday?" "memory recall -> LLM" 60
send "ok got it" "acknowledgment -> RULE"
send "show me the files in the current directory" "tool use -> LLM" 60
send "read the main.py file" "file read -> LLM" 100
send "read the main.py file" "REPEAT -> expect CACHE" 100
send "thanks" "acknowledgment -> RULE"
send "there is a bug in the delete endpoint, can you spot it?" "analysis -> LLM" 100
send "yes" "confirmation -> RULE"
send "run the tests to confirm" "tool use -> LLM" 60
send "show me the test output again" "similar -> LLM" 60
send "ok" "acknowledgment -> RULE"
send "now fix the delete endpoint so it actually removes the todo" "code fix -> LLM" 100
send "yes" "confirmation -> RULE"
send "read the main.py file" "REPEAT 3rd time -> expect CACHE" 100
send "run the tests again" "similar -> LLM" 60
send "thanks" "acknowledgment -> RULE"
send "what should we work on next?" "planning -> LLM" 60
send "bye" "goodbye -> RULE"

print_results
