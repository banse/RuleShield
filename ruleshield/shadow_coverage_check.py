"""Shadow coverage diagnostics for RuleShield prompt scenarios.

Runs low-cost probe prompts against the local RuleShield proxy and reports,
for each prompt, whether shadow comparison data was persisted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import time
import sqlite3

import httpx

from ruleshield.prompt_training import _extract_runtime_bearer, _load_scenario_from_path

DEFAULT_PROXY_URL = "http://127.0.0.1:8337"
DEFAULT_MODEL = "gpt-5.1-codex-mini"
DEFAULT_OUTPUT_BASE = Path("test-runs") / "shadow-coverage-check"
DEFAULT_SCENARIOS = (
    Path("ruleshield/training_configs/hermes_user_short.yaml"),
    Path("ruleshield/training_configs/hermes_user_medium.yaml"),
    Path("ruleshield/training_configs/hermes_user_complex.yaml"),
)


@dataclass
class StepCoverageResult:
    scenario_id: str
    step_id: str
    prompt: str
    status_code: int
    probe_status: str
    resolution_header: str
    shadow_header: str
    response_text: str
    delta_total_comparisons: int
    delta_by_rule: dict[str, int]
    delta_rule_hits: dict[str, int]
    delta_rule_shadow_hits: dict[str, int]
    delta_db_comparisons: int
    db_rule_ids: list[str]
    diagnosis: str


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _fetch_shadow_snapshot(client: httpx.Client, proxy_url: str) -> dict[str, Any]:
    resp = client.get(f"{proxy_url.rstrip('/')}/api/shadow", timeout=20.0)
    resp.raise_for_status()
    data = resp.json() if resp.content else {}
    if not isinstance(data, dict):
        data = {}
    by_rule = {}
    for entry in data.get("by_rule", []) or []:
        if not isinstance(entry, dict):
            continue
        rid = str(entry.get("rule_id", ""))
        if not rid:
            continue
        by_rule[rid] = int(entry.get("comparisons", 0))
    return {
        "total": int(data.get("total_comparisons", 0)),
        "by_rule": by_rule,
        "enabled": bool(data.get("enabled", False)),
    }


def _fetch_rules_snapshot(client: httpx.Client, proxy_url: str) -> dict[str, dict[str, int]]:
    resp = client.get(f"{proxy_url.rstrip('/')}/api/rules", timeout=20.0)
    resp.raise_for_status()
    data = resp.json() if resp.content else {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    for entry in data.get("rules", []) or []:
        if not isinstance(entry, dict):
            continue
        rid = str(entry.get("id", ""))
        if not rid:
            continue
        out[rid] = {
            "hits": int(entry.get("hits", 0)),
            "shadow_hits": int(entry.get("shadow_hits", 0)),
        }
    return out


def _positive_deltas(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    keys = set(before) | set(after)
    out: dict[str, int] = {}
    for key in keys:
        delta = int(after.get(key, 0)) - int(before.get(key, 0))
        if delta > 0:
            out[key] = delta
    return out


def _shadow_db_path() -> Path:
    return Path("~/.ruleshield/cache.db").expanduser().resolve()


def _fetch_shadow_db_count() -> int:
    db_path = _shadow_db_path()
    if not db_path.exists():
        return 0
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        row = cur.execute("SELECT COUNT(*) FROM shadow_log").fetchone()
        return int(row[0] if row else 0)
    finally:
        con.close()


def _fetch_shadow_db_max_id() -> int:
    db_path = _shadow_db_path()
    if not db_path.exists():
        return 0
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        row = cur.execute("SELECT COALESCE(MAX(id), 0) FROM shadow_log").fetchone()
        return int(row[0] if row else 0)
    finally:
        con.close()


def _fetch_shadow_db_rows_after_id(max_id_before: int) -> list[dict[str, Any]]:
    db_path = _shadow_db_path()
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        rows = cur.execute(
            """
            SELECT id, rule_id, prompt_text, created_at
            FROM shadow_log
            WHERE id > ?
            ORDER BY id ASC
            """,
            (max_id_before,),
        ).fetchall()
    finally:
        con.close()

    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({
            "id": int(row[0]),
            "rule_id": str(row[1] or ""),
            "prompt_text": str(row[2] or ""),
            "created_at": str(row[3] or ""),
        })
    return out


def _wait_for_shadow_delta(
    *,
    client: httpx.Client,
    proxy_url: str,
    before_shadow: dict[str, Any],
    timeout_seconds: float = 2.0,
    interval_seconds: float = 0.25,
) -> dict[str, Any]:
    """Poll /api/shadow briefly to absorb async logging lag after streaming."""
    deadline = time.monotonic() + timeout_seconds
    latest = _fetch_shadow_snapshot(client, proxy_url)
    while time.monotonic() < deadline:
        if int(latest["total"]) > int(before_shadow["total"]):
            return latest
        if _positive_deltas(before_shadow["by_rule"], latest["by_rule"]):
            return latest
        time.sleep(interval_seconds)
        latest = _fetch_shadow_snapshot(client, proxy_url)
    return latest


def _wait_for_shadow_db_delta(
    *,
    max_id_before: int,
    timeout_seconds: float = 3.0,
    interval_seconds: float = 0.25,
) -> tuple[int, list[dict[str, Any]]]:
    """Poll shadow_log count directly to avoid API aggregation lag."""
    deadline = time.monotonic() + timeout_seconds
    current_max_id = _fetch_shadow_db_max_id()
    while time.monotonic() < deadline:
        if current_max_id > max_id_before:
            rows = _fetch_shadow_db_rows_after_id(max_id_before)
            return len(rows), rows
        time.sleep(interval_seconds)
        current_max_id = _fetch_shadow_db_max_id()
    return 0, []


def _extract_sse_text(stream: httpx.Response) -> str:
    parts: list[str] = []
    for line in stream.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode(errors="replace")
        if not line.startswith("data: "):
            continue
        raw = line[6:]
        if raw.strip() in ("", "[DONE]"):
            continue
        try:
            event = json.loads(raw)
        except Exception:
            continue
        event_type = str(event.get("type", ""))
        if event_type == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str) and delta:
                parts.append(delta)
        elif event_type == "response.output_text.done":
            done_text = event.get("text")
            if isinstance(done_text, str) and done_text:
                parts.append(done_text)
        elif event_type == "response.completed":
            response_obj = event.get("response", {})
            for item in response_obj.get("output", []) if isinstance(response_obj, dict) else []:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "message":
                    continue
                for content in item.get("content", []):
                    if not isinstance(content, dict):
                        continue
                    text = content.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
    return "".join(parts).strip()


def _send_probe_prompt(
    *,
    client: httpx.Client,
    proxy_url: str,
    model: str,
    prompt: str,
    bearer_token: str | None,
) -> dict[str, Any]:
    headers = {"content-type": "application/json"}
    if bearer_token:
        headers["authorization"] = f"Bearer {bearer_token}"  # nosec - bearer token from function parameter, not hardcoded
    payload = {
        "model": model,
        "instructions": "You are a concise assistant.",
        "input": [{"role": "user", "content": prompt}],
        "stream": True,
        "store": False,
    }

    with client.stream(
        "POST",
        f"{proxy_url.rstrip('/')}/responses",
        headers=headers,
        json=payload,
        timeout=45.0,
    ) as resp:
        status_code = int(resp.status_code)
        resolution = resp.headers.get("x-ruleshield-resolution", "")
        shadow_header = resp.headers.get("x-ruleshield-shadow", "")
        response_text = ""
        if status_code < 400:
            response_text = _extract_sse_text(resp)
        else:
            try:
                response_text = (resp.text or "").strip()
            except Exception:
                response_text = ""
        return {
            "status_code": status_code,
            "probe_status": f"http_{status_code}",
            "resolution_header": resolution,
            "shadow_header": shadow_header,
            "response_text": response_text,
        }


def run_shadow_coverage_check(
    *,
    proxy_url: str,
    model: str,
    scenario_paths: list[Path],
    output_dir: Path,
    max_steps: int | None,
    runtime_home: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = [_load_scenario_from_path(path) for path in scenario_paths]

    bearer = _extract_runtime_bearer(runtime_home, model=model)
    with httpx.Client() as client:
        health = client.get(f"{proxy_url.rstrip('/')}/health", timeout=15.0)
        health.raise_for_status()

        initial_shadow = _fetch_shadow_snapshot(client, proxy_url)
        initial_rules = _fetch_rules_snapshot(client, proxy_url)

        if not initial_shadow.get("enabled", False):
            raise RuntimeError("Shadow mode is disabled on the gateway. Enable shadow_mode first.")

        results: list[StepCoverageResult] = []
        steps_seen = 0
        for scenario in scenarios:
            for step in scenario.steps:
                if max_steps is not None and steps_seen >= max_steps:
                    break
                steps_seen += 1

                print(f"[coverage] scenario={scenario.id} step={step.id} start")
                before_shadow = _fetch_shadow_snapshot(client, proxy_url)
                before_rules = _fetch_rules_snapshot(client, proxy_url)
                before_shadow_db_max_id = _fetch_shadow_db_max_id()

                probe = _send_probe_prompt(
                    client=client,
                    proxy_url=proxy_url,
                    model=model,
                    prompt=step.prompt,
                    bearer_token=bearer,
                )

                # Shadow persistence runs after stream finalization; poll briefly.
                after_shadow = _wait_for_shadow_delta(
                    client=client,
                    proxy_url=proxy_url,
                    before_shadow=before_shadow,
                )
                delta_db_comparisons, db_rows = _wait_for_shadow_db_delta(
                    max_id_before=before_shadow_db_max_id,
                )
                after_rules = _fetch_rules_snapshot(client, proxy_url)

                delta_total = int(after_shadow["total"]) - int(before_shadow["total"])
                delta_by_rule = _positive_deltas(before_shadow["by_rule"], after_shadow["by_rule"])

                before_hits = {k: v.get("hits", 0) for k, v in before_rules.items()}
                after_hits = {k: v.get("hits", 0) for k, v in after_rules.items()}
                delta_rule_hits = _positive_deltas(before_hits, after_hits)

                before_shadow_hits = {k: v.get("shadow_hits", 0) for k, v in before_rules.items()}
                after_shadow_hits = {k: v.get("shadow_hits", 0) for k, v in after_rules.items()}
                delta_rule_shadow_hits = _positive_deltas(before_shadow_hits, after_shadow_hits)

                shadow_header = str(probe.get("shadow_header", "") or "")
                if int(probe["status_code"]) >= 400:
                    diagnosis = "request_failed"
                elif delta_db_comparisons > 0:
                    diagnosis = "shadow_logged"
                elif shadow_header and delta_total <= 0:
                    diagnosis = "shadow_header_without_persist"
                elif shadow_header or delta_total > 0:
                    diagnosis = "shadow_logged"
                elif delta_rule_hits:
                    diagnosis = "rule_hit_without_shadow_log"
                else:
                    diagnosis = "no_rule_match"

                result = StepCoverageResult(
                    scenario_id=scenario.id,
                    step_id=step.id,
                    prompt=step.prompt,
                    status_code=int(probe["status_code"]),
                    probe_status=str(probe["probe_status"]),
                    resolution_header=str(probe["resolution_header"]),
                    shadow_header=shadow_header,
                    response_text=str(probe["response_text"]),
                    delta_total_comparisons=delta_total,
                    delta_by_rule=delta_by_rule,
                    delta_rule_hits=delta_rule_hits,
                    delta_rule_shadow_hits=delta_rule_shadow_hits,
                    delta_db_comparisons=delta_db_comparisons,
                    db_rule_ids=[row.get("rule_id", "") for row in db_rows if row.get("rule_id")],
                    diagnosis=diagnosis,
                )
                results.append(result)
                print(
                    "[coverage] scenario={} step={} done status={} resolution={} shadow_header={} delta_cmp={} diag={}".format(
                        scenario.id,
                        step.id,
                        result.probe_status,
                        result.resolution_header or "-",
                        result.shadow_header or "-",
                        result.delta_total_comparisons,
                        result.diagnosis,
                    )
                )

            if max_steps is not None and steps_seen >= max_steps:
                break

        final_shadow = _fetch_shadow_snapshot(client, proxy_url)
        final_rules = _fetch_rules_snapshot(client, proxy_url)

    counts = {
        "total_steps": len(results),
        "shadow_logged": sum(1 for r in results if r.diagnosis == "shadow_logged"),
        "shadow_header_without_persist": sum(
            1 for r in results if r.diagnosis == "shadow_header_without_persist"
        ),
        "rule_hit_without_shadow_log": sum(1 for r in results if r.diagnosis == "rule_hit_without_shadow_log"),
        "no_rule_match": sum(1 for r in results if r.diagnosis == "no_rule_match"),
        "request_failed": sum(1 for r in results if r.diagnosis == "request_failed"),
    }

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "proxy_url": proxy_url,
        "model": model,
        "runtime_home": str(runtime_home),
        "scenario_paths": [str(path) for path in scenario_paths],
        "max_steps": max_steps,
        "initial_shadow": initial_shadow,
        "final_shadow": final_shadow,
        "initial_rules": initial_rules,
        "final_rules": final_rules,
        "counts": counts,
        "results": [asdict(r) for r in results],
    }

    report_path = output_dir / "shadow-coverage-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a per-step Shadow coverage diagnostic.")
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--scenario-config",
        action="append",
        dest="scenario_configs",
        help="Path to scenario YAML. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_BASE / _utc_stamp()),
        help="Directory where the coverage report JSON is written.",
    )
    parser.add_argument("--max-steps", type=int, default=None, help="Optional global step limit.")
    parser.add_argument(
        "--runtime-home",
        default=str(Path.home()),
        help="Home directory for runtime auth discovery (default: current user home).",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    scenario_paths = (
        [Path(path).expanduser().resolve() for path in args.scenario_configs]
        if args.scenario_configs
        else [(Path.cwd() / path).resolve() for path in DEFAULT_SCENARIOS]
    )
    for path in scenario_paths:
        if not path.is_file():
            raise SystemExit(f"Scenario config not found: {path}")

    report = run_shadow_coverage_check(
        proxy_url=str(args.proxy_url),
        model=str(args.model),
        scenario_paths=scenario_paths,
        output_dir=Path(args.output_dir).expanduser().resolve(),
        max_steps=args.max_steps,
        runtime_home=Path(args.runtime_home).expanduser().resolve(),
    )
    counts = report.get("counts", {})
    print("")
    print("== Shadow Coverage Summary ==")
    print(f"steps:                    {counts.get('total_steps', 0)}")
    print(f"shadow_logged:            {counts.get('shadow_logged', 0)}")
    print(
        "shadow_header_no_persist: "
        f"{counts.get('shadow_header_without_persist', 0)}"
    )
    print(f"rule_hit_without_shadow:  {counts.get('rule_hit_without_shadow_log', 0)}")
    print(f"no_rule_match:            {counts.get('no_rule_match', 0)}")
    print(f"request_failed:           {counts.get('request_failed', 0)}")
    print(f"report:                   {Path(args.output_dir).expanduser().resolve() / 'shadow-coverage-report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
