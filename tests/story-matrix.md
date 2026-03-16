# RuleShield Story Matrix

This matrix defines the product-contract tests.

## Core stories

| Story ID | User story | Test entrypoint | Gate |
|----------|------------|-----------------|------|
| A | Fresh local install/init/restore works | `tests/stories/story_install_init_restore.sh` | commit |
| B | Gateway honors configured port | `tests/stories/story_gateway_honors_config_port.sh` | commit |
| C | Hermes prompts flow through RuleShield | `tests/stories/story_health_check_flow.sh` | core |
| D | Repetitive prompts trigger visible RuleShield behavior | `tests/stories/story_rule_trigger_flow.sh` | commit |
| E | Recommended health-check flow remains runnable | `tests/stories/story_health_check_flow.sh` | core |
| F | Monitor data contract stays truthful | `tests/stories/story_monitor_contract.sh` | core |
| G | Feedback loop influences rule quality | `tests/stories/story_feedback_loop.sh` | core |
| H | Hermes rollback is clean | `tests/stories/story_install_init_restore.sh` | commit |
| I | Clean install runs without post-install tweaks | `demo/test_clean_install_no_post_steps.sh` | full |

## Extended scenarios

| Scenario | Entrypoint | Gate |
|----------|------------|------|
| Hermes user suite | `demo/test_training_hermes_user_suite.sh` | full |
| Vibecoder suite | `demo/test_training_vibecoder_suite.sh` | full |
| Shadow coverage diagnostics | `demo/test_shadow_coverage_check.sh` | full |
| Health-check flow (OpenRouter StepFun) | `tests/stories/story_health_check_flow_openrouter_stepfun.sh` | full |
| Monitor-driven health-check E2E (browser) | `tests/stories/story_monitor_healthcheck_e2e.sh` | full |
| OpenRouter profile variants | `demo/test_*openrouter*.sh` | full |

## Feature coverage rule

Every user-visible feature must map to at least one core or extended story.

If a feature:
- changes an existing user workflow, update the mapped story test
- adds a new user workflow, add a new story test and map it here

No mapped story coverage means the feature is not ready to commit.
