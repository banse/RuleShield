#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/tests/framework/suite_runner.sh"
cd "$ROOT_DIR"

suite_init "core"
trap 'suite_finish $?' EXIT

echo "== Core Suite =="
SUITE_PARENT_RUN_ID="$RUN_ID" bash tests/run-commit-suite.sh

echo "5) Story: health-check flow"
suite_case "story_health_check_flow" "Story: health-check flow" "tests/stories/story_health_check_flow.sh" \
  bash tests/stories/story_health_check_flow.sh

echo "6) Story: monitor contract"
suite_case "story_monitor_contract" "Story: monitor contract" "tests/stories/story_monitor_contract.sh" \
  bash tests/stories/story_monitor_contract.sh

echo "7) Story: feedback loop"
suite_case "story_feedback_loop" "Story: feedback loop" "tests/stories/story_feedback_loop.sh" \
  bash tests/stories/story_feedback_loop.sh

echo "8) Story: hermes passthrough"
suite_case "story_hermes_passthrough" "Story: hermes passthrough" "tests/stories/story_hermes_passthrough.sh" \
  bash tests/stories/story_hermes_passthrough.sh

echo "run-core-suite: ok"
