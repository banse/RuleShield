# Cron Profile Runtime Guide

This guide shows the smallest honest production path for active cron optimization profiles.

## Goal

Use RuleShield to:

- detect a recurring workflow
- compact it into a reusable profile
- validate the compact path in shadow
- activate the profile
- call the active profile from Hermes, Python, or an external scheduler

RuleShield does not own your scheduler in V1. It exposes a stable compact execution surface that your automation can call.

## Runtime Contract

Once a profile is active, execute it with:

```bash
curl -s -X POST http://127.0.0.1:8337/api/cron-profiles/<profile_id>/execute \
  -H 'content-type: application/json' \
  -d '{"payload_text":"<dynamic content here>"}'
```

The payload should contain only the dynamic content for the recurring task. Fixed workflow instructions stay in the profile.

## Hermes Automation Pattern

The recommended Hermes pattern is:

1. fetch or assemble the dynamic payload outside the LLM
2. send the payload to the active RuleShield profile
3. take the compact response and post it to the target channel

Example operator flow:

```text
fetch inbox -> normalize content -> call active cron profile -> deliver digest
```

## Python Example

```python
import requests

payload_text = """
Finance:
- Vendor invoice needs review

Product:
- Release note draft needs summary
""".strip()

res = requests.post(
    "http://127.0.0.1:8337/api/cron-profiles/daily_digest_abcd1234/execute",
    json={"payload_text": payload_text},
    timeout=30,
)
res.raise_for_status()
data = res.json()
print(data["execution"]["response_text"])
```

## Hermes Python Library Example

Use Hermes as the orchestration shell and RuleShield as the compact execution endpoint.

```python
import requests
from hermes import AIAgent

agent = AIAgent(quiet_mode=True, skip_memory=True, skip_context_files=True)

payload_text = "Normalized email bundle here"
response = requests.post(
    "http://127.0.0.1:8337/api/cron-profiles/daily_digest_abcd1234/execute",
    json={"payload_text": payload_text},
    timeout=30,
).json()

agent.chat(
    "Deliver this digest to the operator channel exactly as written:\n\n"
    + response["execution"]["response_text"]
)
```

## Good Payload Design

Active profiles work best when payloads are:

- already fetched
- already normalized
- stripped of repeated instructions
- focused on the variable content only

Bad:

```text
Please check my inbox every day at 8am, categorize the emails, summarize them, and return markdown.
```

Good:

```text
Finance:
- Invoice from vendor

Support:
- Customer asked for refund status
```

## Operational Advice

- Use `cron-lab` for draft tuning and activation.
- Use `shadow-run` before activation whenever the compact prompt changes.
- Watch validation confidence and execution history separately.
- Archive old profiles instead of deleting them immediately when a workflow changes.

## V1 Boundaries

This runtime path does not yet:

- own the scheduler
- fetch external sources automatically
- manage delivery integrations

Those pieces stay deterministic and external by design. RuleShield owns prompt compaction, validation, and the compact execution surface.
