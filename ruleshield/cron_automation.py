"""Automation suggestions for active cron optimization profiles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_DAY_MAP = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}


def _infer_schedule(prompt_text: str) -> str:
    """Infer a UI-compatible weekly schedule from the source prompt."""
    lower = prompt_text.lower()
    byday = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    if "every weekday" in lower:
        byday = ["MO", "TU", "WE", "TH", "FR"]
    elif "every weekend" in lower:
        byday = ["SA", "SU"]
    else:
        explicit_days = [code for day, code in _DAY_MAP.items() if day in lower]
        if explicit_days:
            byday = explicit_days

    hour = 9
    minute = 0
    match = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

    byday_text = ",".join(byday)
    return f"FREQ=WEEKLY;BYDAY={byday_text};BYHOUR={hour};BYMINUTE={minute}"


def build_automation_suggestion(
    profile: dict[str, Any],
    *,
    cwd: str | Path,
) -> dict[str, str]:
    """Build a Codex automation suggestion for an active cron profile."""
    profile_id = str(profile.get("id", "")).strip()
    profile_name = str(profile.get("name", profile_id)).strip() or profile_id
    prompt_text = str(profile.get("source", {}).get("prompt_text", "")).strip()
    rrule = _infer_schedule(prompt_text)
    cwd_text = str(Path(cwd).expanduser())
    prompt = (
        f"Run the active RuleShield cron profile `{profile_id}`. "
        f"First fetch or assemble the current dynamic payload for the recurring workflow "
        f'"{profile_name}", then call `http://127.0.0.1:8337/api/cron-profiles/{profile_id}/execute` '
        f"with that payload, and return the compact result."
    )
    directive = (
        '::automation-update{mode="suggested create" '
        f'name="{profile_name}" '
        f'prompt="{prompt}" '
        f'rrule="{rrule}" '
        f'cwds="{cwd_text}" '
        'status="ACTIVE"}'
    )
    return {
        "name": profile_name,
        "prompt": prompt,
        "rrule": rrule,
        "cwd": cwd_text,
        "directive": directive,
    }
