#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_log_excerpt(root: Path, rel_path: str, max_lines: int = 14, max_chars: int = 2200) -> str:
    if not rel_path:
        return ""
    path = root / rel_path
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return ""
    tail = lines[-max_lines:]
    text = "\n".join(tail).strip()
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def _is_port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _extract_gateway_url_from_log(root: Path, rel_path: str) -> str:
    path = root / rel_path
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    # Prefer explicit "Proxy: http://127.0.0.1:<port>" lines from story scripts.
    m = re.search(r"Proxy:\s*http://127\.0\.0\.1:(\d+)", text)
    if not m:
        # Fallback to first local URL mentioned in the log.
        m = re.search(r"http://127\.0\.0\.1:(\d+)", text)
    if not m:
        return ""
    return f"http://127.0.0.1:{m.group(1)}"


def detect_test_gateway(root: Path, story_logs: list[dict[str, Any]]) -> dict[str, Any]:
    if not story_logs:
        return {
            "mode": "test-owned",
            "source": "none",
            "configured_port": None,
            "health_host": "127.0.0.1",
            "health_url": "",
            "status": "unknown",
        }

    url = ""
    for item in story_logs:
        log_path = str(item.get("log_path", "")).strip()
        url = _extract_gateway_url_from_log(root, log_path)
        if url:
            break
    if not url:
        return {
            "mode": "test-owned",
            "source": "story-log",
            "configured_port": None,
            "health_host": "127.0.0.1",
            "health_url": "",
            "status": "unknown",
        }

    port = int(url.rsplit(":", 1)[-1])
    host = "127.0.0.1"
    health_url = f"{url}/health"
    status = "online" if _is_port_open(host, port) else "offline"
    return {
        "mode": "test-owned",
        "source": "story-log",
        "configured_port": port,
        "health_host": host,
        "health_url": health_url,
        "status": status,
    }


@dataclass
class StorePaths:
    root: Path
    status_root: Path
    data_root: Path
    runs_root: Path
    tests_root: Path
    summary_file: Path
    catalog_file: Path

    @classmethod
    def from_root(cls, root: Path) -> "StorePaths":
        status_root = root / "tests" / "status"
        data_root = status_root / "data"
        return cls(
            root=root,
            status_root=status_root,
            data_root=data_root,
            runs_root=data_root / "runs",
            tests_root=data_root / "tests",
            summary_file=data_root / "summary.json",
            catalog_file=status_root / "catalog.json",
        )


def cmd_init_run(args: argparse.Namespace) -> int:
    paths = StorePaths.from_root(Path(args.root).resolve())
    run_file = paths.runs_root / f"{args.run_id}.json"
    payload = {
        "run_id": args.run_id,
        "suite_id": args.suite_id,
        "started_at": args.started_at,
        "ended_at": "",
        "status": "running",
        "exit_code": None,
        "cases": [],
    }
    write_json(run_file, payload)
    return 0


def cmd_record_case(args: argparse.Namespace) -> int:
    paths = StorePaths.from_root(Path(args.root).resolve())
    run_file = paths.runs_root / f"{args.run_id}.json"
    run_payload = read_json(run_file, {})
    if not run_payload:
        return 1

    case_payload = {
        "case_id": args.case_id,
        "name": args.name,
        "script_path": args.script_path,
        "status": args.status,
        "exit_code": int(args.exit_code),
        "started_at": args.started_at,
        "ended_at": args.ended_at,
        "duration_ms": int(args.duration_ms),
        "log_path": args.log_path,
        "error": args.error,
    }
    cases = run_payload.get("cases") or []
    cases.append(case_payload)
    run_payload["cases"] = cases
    write_json(run_file, run_payload)

    test_state_file = paths.tests_root / f"{args.case_id}.json"
    test_state = read_json(
        test_state_file,
        {"id": args.case_id, "name": args.name, "script_path": args.script_path, "last_run": None},
    )
    test_state["id"] = args.case_id
    test_state["name"] = args.name
    test_state["script_path"] = args.script_path
    test_state["last_run"] = {
        "run_id": args.run_id,
        "suite_id": run_payload.get("suite_id", ""),
        "started_at": args.started_at,
        "ended_at": args.ended_at,
        "duration_ms": int(args.duration_ms),
        "status": args.status,
        "exit_code": int(args.exit_code),
        "error": args.error,
        "log_path": args.log_path,
    }
    write_json(test_state_file, test_state)
    return 0


def cmd_finalize_run(args: argparse.Namespace) -> int:
    paths = StorePaths.from_root(Path(args.root).resolve())
    run_file = paths.runs_root / f"{args.run_id}.json"
    run_payload = read_json(run_file, {})
    if not run_payload:
        return 1

    run_payload["ended_at"] = args.ended_at or utc_now_iso()
    run_payload["exit_code"] = int(args.exit_code)
    run_payload["status"] = "success" if int(args.exit_code) == 0 else "failed"
    write_json(run_file, run_payload)
    rebuild_summary(paths)
    return 0


def rebuild_summary(paths: StorePaths) -> None:
    catalog = read_json(paths.catalog_file, {"tests": []})
    test_entries = catalog.get("tests") if isinstance(catalog, dict) else []
    if not isinstance(test_entries, list):
        test_entries = []

    tests_payload: list[dict[str, Any]] = []
    for entry in test_entries:
        if not isinstance(entry, dict):
            continue
        test_id = str(entry.get("id", "")).strip()
        if not test_id:
            continue
        state = read_json(paths.tests_root / f"{test_id}.json", {})
        tests_payload.append(
            {
                "id": test_id,
                "name": entry.get("name", test_id),
                "script_path": entry.get("script_path", ""),
                "group": entry.get("group", "core"),
                "last_run": state.get("last_run"),
            }
        )

    recent_runs: list[dict[str, Any]] = []
    story_logs: list[dict[str, Any]] = []
    for run_file in sorted(paths.runs_root.glob("*.json"), reverse=True):
        run = read_json(run_file, {})
        if not run:
            continue

        cases = run.get("cases") or []
        if isinstance(cases, list):
            for case in reversed(cases):
                if not isinstance(case, dict):
                    continue
                case_id = str(case.get("case_id", ""))
                if not case_id.startswith("story_"):
                    continue
                log_path = str(case.get("log_path", "")).strip()
                story_logs.append(
                    {
                        "run_id": run.get("run_id", ""),
                        "suite_id": run.get("suite_id", ""),
                        "case_id": case_id,
                        "name": case.get("name", case_id),
                        "status": case.get("status", "unknown"),
                        "started_at": case.get("started_at", ""),
                        "ended_at": case.get("ended_at", ""),
                        "duration_ms": case.get("duration_ms", 0),
                        "error": case.get("error", ""),
                        "log_path": log_path,
                        "log_excerpt": read_log_excerpt(paths.root, log_path),
                    }
                )
                if len(story_logs) >= 120:
                    break
        if len(story_logs) >= 120:
            break

        recent_runs.append(
            {
                "run_id": run.get("run_id", ""),
                "suite_id": run.get("suite_id", ""),
                "started_at": run.get("started_at", ""),
                "ended_at": run.get("ended_at", ""),
                "status": run.get("status", "unknown"),
                "exit_code": run.get("exit_code"),
                "cases": len(cases) if isinstance(cases, list) else 0,
            }
        )
        if len(recent_runs) >= 20:
            break

    summary = {
        "generated_at": utc_now_iso(),
        "gateway": detect_test_gateway(paths.root, story_logs),
        "tests": tests_payload,
        "recent_runs": recent_runs,
        "story_logs": story_logs,
    }
    write_json(paths.summary_file, summary)


def cmd_rebuild_summary(args: argparse.Namespace) -> int:
    rebuild_summary(StorePaths.from_root(Path(args.root).resolve()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Store test status for the standalone test status page.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_run = sub.add_parser("init-run")
    init_run.add_argument("--root", required=True)
    init_run.add_argument("--run-id", required=True)
    init_run.add_argument("--suite-id", required=True)
    init_run.add_argument("--started-at", required=True)
    init_run.set_defaults(func=cmd_init_run)

    record_case = sub.add_parser("record-case")
    record_case.add_argument("--root", required=True)
    record_case.add_argument("--run-id", required=True)
    record_case.add_argument("--case-id", required=True)
    record_case.add_argument("--name", required=True)
    record_case.add_argument("--script-path", required=True)
    record_case.add_argument("--status", required=True, choices=["success", "failed"])
    record_case.add_argument("--exit-code", required=True)
    record_case.add_argument("--started-at", required=True)
    record_case.add_argument("--ended-at", required=True)
    record_case.add_argument("--duration-ms", required=True)
    record_case.add_argument("--log-path", required=True)
    record_case.add_argument("--error", default="")
    record_case.set_defaults(func=cmd_record_case)

    finalize_run = sub.add_parser("finalize-run")
    finalize_run.add_argument("--root", required=True)
    finalize_run.add_argument("--run-id", required=True)
    finalize_run.add_argument("--exit-code", required=True)
    finalize_run.add_argument("--ended-at", default="")
    finalize_run.set_defaults(func=cmd_finalize_run)

    rebuild = sub.add_parser("rebuild-summary")
    rebuild.add_argument("--root", required=True)
    rebuild.set_defaults(func=cmd_rebuild_summary)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
