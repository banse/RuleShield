from __future__ import annotations

import json
import os
from pathlib import Path

from ruleshield.prompt_training import run_prompt_training


def test_run_prompt_training_writes_reports_and_project_changes(tmp_path, monkeypatch):
    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def chat(self, prompt: str) -> str:
            project_dir = Path(os.environ["PWD"])
            target = project_dir / "app.js"
            existing = target.read_text(encoding="utf-8")
            target.write_text(existing + f"\n// {prompt[:32]}", encoding="utf-8")
            return f"Handled: {prompt[:40]}"

    monkeypatch.setattr(
        "ruleshield.prompt_training._import_ai_agent",
        lambda: (FakeAgent, "fake:FakeAgent"),
    )
    monkeypatch.setattr(
        "ruleshield.prompt_training._collect_ruleshield_summary",
        lambda proxy_url, started_at: {
            "stats_snapshot": {"total_requests": 6},
            "recent_requests": [{"resolution_type": "passthrough", "created_at": "2026-03-15 12:00:00"}],
            "request_breakdown": {"passthrough": 1},
            "shadow_snapshot": {"enabled": True, "total_comparisons": 2, "avg_similarity_pct": 22.2, "rules_ready": 0},
            "feedback_snapshot": {"entries": []},
            "recent_feedback": [],
            "recent_rule_events": [],
            "confidence_events": [],
            "activation_events": [],
        },
    )

    result = run_prompt_training(
        output_dir=tmp_path,
        proxy_url="http://127.0.0.1:8337",
        max_prompts=3,
    )

    assert result.prompts_sent == 3
    assert result.hermes_available is True
    assert Path(result.project_dir).is_dir()
    assert Path(result.summary_json_path).is_file()
    assert Path(result.summary_md_path).is_file()

    summary = json.loads(Path(result.summary_json_path).read_text(encoding="utf-8"))
    assert summary["scenario"]["id"] == "vibecoder_stats_dashboard"
    assert len(summary["transcript"]) == 3
    assert "app.js" in summary["workspace_changes"]["project"]["modified"]

    markdown = Path(result.summary_md_path).read_text(encoding="utf-8")
    assert "RuleShield Prompt Training Run" in markdown
    assert "Shadow Mode" in markdown
