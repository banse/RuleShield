#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/tests/framework/suite_runner.sh"
cd "$ROOT_DIR"

suite_init "full"
trap 'suite_finish $?' EXIT

echo "== Full Suite =="
SUITE_PARENT_RUN_ID="$RUN_ID" bash tests/run-core-suite.sh

echo "  [11/16] Running Story: health-check flow (OpenRouter StepFun)"
suite_case "story_health_check_flow_openrouter_stepfun" "Story: health-check flow (OpenRouter StepFun)" "tests/stories/story_health_check_flow_openrouter_stepfun.sh" \
  bash tests/stories/story_health_check_flow_openrouter_stepfun.sh

echo "  [12/16] Running Story: monitor-driven health-check e2e (browser)"
suite_case "story_monitor_healthcheck_e2e" "Story: monitor-driven health-check e2e (browser)" "tests/stories/story_monitor_healthcheck_e2e.sh" \
  bash tests/stories/story_monitor_healthcheck_e2e.sh

echo "  [13/16] Running Demo: clean install needs no post-install steps"
suite_case "story_clean_install_no_post_steps" "Demo: clean install needs no post-install steps" "demo/test_clean_install_no_post_steps.sh" \
  bash demo/test_clean_install_no_post_steps.sh

echo "  [14/16] Running Extended: hermes user suite"
suite_case "extended_hermes_user_suite" "Extended: hermes user suite" "demo/test_training_hermes_user_suite.sh" \
  bash demo/test_training_hermes_user_suite.sh

echo "  [15/16] Running Extended: vibecoder suite"
suite_case "extended_vibecoder_suite" "Extended: vibecoder suite" "demo/test_training_vibecoder_suite.sh" \
  bash demo/test_training_vibecoder_suite.sh

echo "  [16/16] Running Extended: shadow coverage check"
suite_case "extended_shadow_coverage" "Extended: shadow coverage check" "demo/test_shadow_coverage_check.sh" \
  bash demo/test_shadow_coverage_check.sh

echo "run-full-suite: ok"
