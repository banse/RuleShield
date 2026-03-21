"""Rule loading, validation, and state persistence for rulecore."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from rulecore.conditions import validate_condition_tree

logger = logging.getLogger("rulecore.loader")


def load_rules(rules_dir: str, bundled_dir: str | None = None) -> list[dict[str, Any]]:
    """Load rules from JSON files in a directory."""
    rules_path = Path(rules_dir)
    rules_path.mkdir(parents=True, exist_ok=True)

    json_files = [fp for fp in rules_path.glob("*.json") if fp.name != "_state.json"]

    if not json_files and bundled_dir:
        bundled = Path(bundled_dir)
        if bundled.is_dir():
            for src in bundled.glob("*.json"):
                dest = rules_path / src.name
                if not dest.exists():
                    shutil.copy2(str(src), str(dest))
            json_files = [fp for fp in rules_path.glob("*.json") if fp.name != "_state.json"]

    for subdir_name in ("promoted", "candidates"):
        subdir = rules_path / subdir_name
        if subdir.is_dir():
            json_files.extend(subdir.glob("*.json"))

    rules: list[dict[str, Any]] = []
    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            loaded = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            deployment = "candidate" if fp.parent.name == "candidates" else "production"
            for rule in loaded:
                if not isinstance(rule, dict):
                    continue
                if ("patterns" not in rule and "condition_tree" not in rule) or "response" not in rule:
                    continue
                if "condition_tree" in rule:
                    if not validate_condition_tree(rule["condition_tree"]):
                        logger.warning("Skipping rule %s: invalid condition_tree", rule.get("id", "<unknown>"))
                        continue
                rule.setdefault("deployment", deployment)
                rule.setdefault("hit_count", 0)
                rule.setdefault("shadow_hit_count", 0)
                rules.append(rule)
        except (json.JSONDecodeError, OSError):
            continue

    rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
    apply_persisted_state(rules, rules_dir)
    return rules


def apply_persisted_state(rules: list[dict[str, Any]], rules_dir: str) -> None:
    """Merge runtime state from _state.json into loaded rules."""
    state_path = Path(rules_dir) / "_state.json"
    if not state_path.is_file():
        return
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            state_entries = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return
    state_map: dict[str, dict[str, Any]] = {}
    for entry in state_entries:
        rid = entry.get("id")
        if rid:
            state_map[rid] = entry
    for rule in rules:
        rid = rule.get("id")
        if rid and rid in state_map:
            saved = state_map[rid]
            rule["hit_count"] = saved.get("hit_count", rule.get("hit_count", 0))
            rule["shadow_hit_count"] = saved.get("shadow_hit_count", rule.get("shadow_hit_count", 0))
            rule["confidence"] = saved.get("confidence", rule.get("confidence", 1.0))
            rule["enabled"] = saved.get("enabled", rule.get("enabled", True))
            rule["deployment"] = saved.get("deployment", rule.get("deployment", "production"))


def save_state(rules: list[dict[str, Any]], rules_dir: str) -> None:
    """Persist runtime state to _state.json."""
    state_path = Path(rules_dir) / "_state.json"
    serialisable = []
    for rule in rules:
        serialisable.append({
            "id": rule.get("id"),
            "hit_count": rule.get("hit_count", 0),
            "shadow_hit_count": rule.get("shadow_hit_count", 0),
            "confidence": rule.get("confidence", 1.0),
            "enabled": rule.get("enabled", True),
            "deployment": rule.get("deployment", "production"),
        })
    try:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, indent=2)
    except OSError:
        pass
