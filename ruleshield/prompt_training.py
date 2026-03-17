"""Automated RuleShield prompt-training runner.

This module drives Hermes through its Python API so RuleShield can observe
realistic prompt traffic in shadow mode. The first built-in scenario keeps the
workflow intentionally small and deterministic to control runtime and token
cost.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import shutil
import subprocess
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml

from ruleshield.config import Settings, load_settings

DEFAULT_PROXY_URL = "http://127.0.0.1:8337"
DEFAULT_OUTPUT_DIR = Path("test-runs") / "ruleshield-training"
DEFAULT_MODEL = "gpt-5.1-codex-mini"
DEFAULT_HEALTH_SCENARIO_PATH = (
    Path(__file__).resolve().parent / "training_configs" / "health_check_baseline.yaml"
)
DEFAULT_TRAINING_TOOLSETS = ["terminal", "file"]
DEFAULT_TRAINING_MAX_TOKENS = 32

_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Work Session Dashboard</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main class="shell">
      <header class="hero">
        <p class="eyebrow">Personal analytics</p>
        <h1>Work Session Dashboard</h1>
        <p class="lede">A tiny dashboard for focus, throughput, and weekly rhythm.</p>
      </header>
      <section id="cards" class="cards"></section>
      <section class="panel">
        <div class="panel-head">
          <h2>Weekly Completion Trend</h2>
          <p>Last 7 days based on the local JSON fixtures.</p>
        </div>
        <div id="trend" class="trend"></div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>Category Breakdown</h2>
          <p>Tasks completed by category this week.</p>
        </div>
        <ul id="categories" class="category-list"></ul>
      </section>
    </main>
    <script type="module" src="./app.js"></script>
  </body>
</html>
"""

_DASHBOARD_CSS = """:root {
  color-scheme: light;
  --bg: #f4efe5;
  --paper: #fffaf2;
  --ink: #1e1c19;
  --muted: #6a6258;
  --line: #d8cfbf;
  --accent: #1d6b57;
  --accent-soft: #d8eee7;
  --warm: #d88d3c;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(216, 141, 60, 0.22), transparent 32%),
    linear-gradient(180deg, #f8f2e6 0%, var(--bg) 100%);
}

.shell {
  width: min(980px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 48px 0 80px;
}

.hero {
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  color: var(--muted);
}

h1, h2, p {
  margin-top: 0;
}

.lede {
  max-width: 52ch;
  color: var(--muted);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.card,
.panel {
  background: color-mix(in srgb, var(--paper) 90%, white 10%);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: 0 14px 40px rgba(30, 28, 25, 0.05);
}

.card {
  padding: 18px;
}

.card-label {
  margin: 0 0 10px;
  font-size: 0.9rem;
  color: var(--muted);
}

.card-value {
  margin: 0;
  font-size: 2rem;
}

.panel {
  padding: 20px;
  margin-top: 16px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: baseline;
  flex-wrap: wrap;
}

.panel-head p {
  color: var(--muted);
}

.trend {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
  align-items: end;
  min-height: 220px;
  margin-top: 18px;
}

.bar-wrap {
  display: grid;
  gap: 8px;
}

.bar {
  min-height: 24px;
  border-radius: 14px 14px 6px 6px;
  background: linear-gradient(180deg, var(--warm) 0%, var(--accent) 100%);
}

.bar-value,
.bar-label {
  font-size: 0.85rem;
  color: var(--muted);
  text-align: center;
}

.category-list {
  list-style: none;
  margin: 18px 0 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.category-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: var(--accent-soft);
  border-radius: 12px;
}
"""

_DASHBOARD_JS = """const cardsEl = document.querySelector('#cards');
const trendEl = document.querySelector('#trend');
const categoriesEl = document.querySelector('#categories');

async function loadData() {
  const [sessionsRes, tasksRes] = await Promise.all([
    fetch('./data/focus-sessions.json'),
    fetch('./data/tasks.json')
  ]);

  const sessions = await sessionsRes.json();
  const tasks = await tasksRes.json();
  renderDashboard(sessions, tasks);
}

function renderDashboard(sessions, tasks) {
  const totalFocus = sessions.reduce((sum, item) => sum + item.minutes, 0);
  const completedTasks = tasks.filter((task) => task.status === 'done');
  const today = sessions.at(-1);
  const busiest = [...sessions].sort((a, b) => b.minutes - a.minutes)[0];

  const categoryCounts = completedTasks.reduce((acc, task) => {
    acc[task.category] = (acc[task.category] || 0) + 1;
    return acc;
  }, {});

  const streak = countFocusStreak(sessions);

  const cards = [
    { label: 'Focus Minutes', value: totalFocus },
    { label: 'Completed Tasks', value: completedTasks.length },
    { label: 'Current Streak', value: `${streak} days` },
    { label: 'Busiest Day', value: busiest.day }
  ];

  cardsEl.innerHTML = cards
    .map((card) => `
      <article class="card">
        <p class="card-label">${card.label}</p>
        <p class="card-value">${card.value}</p>
      </article>
    `)
    .join('');

  const maxMinutes = Math.max(...sessions.map((item) => item.minutes), 1);
  trendEl.innerHTML = sessions
    .map((item) => {
      const height = Math.max(24, Math.round((item.minutes / maxMinutes) * 180));
      return `
        <div class="bar-wrap">
          <div class="bar-value">${item.minutes}m</div>
          <div class="bar" style="height: ${height}px"></div>
          <div class="bar-label">${item.day}</div>
        </div>
      `;
    })
    .join('');

  categoriesEl.innerHTML = Object.entries(categoryCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([category, count]) => `
      <li class="category-row">
        <span>${category}</span>
        <strong>${count}</strong>
      </li>
    `)
    .join('');
}

function countFocusStreak(sessions) {
  let streak = 0;
  for (let index = sessions.length - 1; index >= 0; index -= 1) {
    if (sessions[index].minutes <= 0) {
      break;
    }
    streak += 1;
  }
  return streak;
}

loadData().catch((error) => {
  cardsEl.innerHTML = `<article class="card"><p class="card-label">Load Error</p><p class="card-value">${error.message}</p></article>`;
});
"""

_SESSIONS_JSON = """[
  {"day":"Mon","minutes":85},
  {"day":"Tue","minutes":120},
  {"day":"Wed","minutes":95},
  {"day":"Thu","minutes":135},
  {"day":"Fri","minutes":110},
  {"day":"Sat","minutes":45},
  {"day":"Sun","minutes":70}
]
"""

_TASKS_JSON = """[
  {"title":"Fix proxy routing stats","category":"Engineering","status":"done"},
  {"title":"Write cron optimizer docs","category":"Docs","status":"done"},
  {"title":"Review shadow feedback run","category":"Research","status":"done"},
  {"title":"Refine dashboard visuals","category":"Design","status":"todo"},
  {"title":"Prepare hackathon slides","category":"Docs","status":"done"},
  {"title":"Analyze prompt clusters","category":"Research","status":"done"},
  {"title":"Polish MCP server docs","category":"Docs","status":"done"}
]
"""

_SEED_README = """# Prompt Training Seed Project

Build a small dashboard from the local fixture files.

Scope rules:
- only use files in this directory
- keep the dashboard static and simple
- do not install packages
- prefer editing the existing HTML, CSS, and JS files
"""


@dataclass(frozen=True)
class TrainingStep:
    id: str
    prompt: str
    fallback_prompt: str | None = None


@dataclass(frozen=True)
class TrainingScenario:
    id: str
    name: str
    description: str
    max_prompts: int
    steps: tuple[TrainingStep, ...]


@dataclass
class TrainingStepResult:
    step_id: str
    prompt: str
    response_text: str
    used_fallback: bool = False
    error: str | None = None
    probe_status: str | None = None


@dataclass
class TrainingRunResult:
    run_id: str
    scenario_id: str
    run_dir: str
    project_dir: str
    reports_dir: str
    prompts_sent: int
    transcript_path: str
    summary_json_path: str
    summary_md_path: str
    duration_seconds: float
    isolation_ok: bool
    hermes_import_target: str
    hermes_available: bool


def _scenario_from_dict(data: dict[str, Any], fallback_id: str = "custom_scenario") -> TrainingScenario:
    scenario_id = str(data.get("id", fallback_id))
    name = str(data.get("name", scenario_id))
    description = str(data.get("description", "Custom prompt-training scenario."))
    max_prompts = int(data.get("max_prompts", 6))
    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list) or not raw_steps:
        raise RuntimeError("Scenario config must contain a non-empty 'steps' list.")

    steps: list[TrainingStep] = []
    for idx, raw in enumerate(raw_steps, start=1):
        if not isinstance(raw, dict):
            raise RuntimeError(f"Scenario step {idx} is not an object.")
        prompt = str(raw.get("prompt", "")).strip()
        if not prompt:
            raise RuntimeError(f"Scenario step {idx} is missing a prompt.")
        step_id = str(raw.get("id", f"step_{idx}"))
        fallback_prompt = raw.get("fallback_prompt")
        steps.append(
            TrainingStep(
                id=step_id,
                prompt=prompt,
                fallback_prompt=str(fallback_prompt) if fallback_prompt else None,
            )
        )

    return TrainingScenario(
        id=scenario_id,
        name=name,
        description=description,
        max_prompts=max_prompts,
        steps=tuple(steps),
    )


def _load_scenario_from_path(path: str | Path) -> TrainingScenario:
    scenario_path = Path(path).expanduser().resolve()
    if not scenario_path.is_file():
        raise RuntimeError(f"Scenario config not found: {scenario_path}")
    try:
        data = yaml.safe_load(scenario_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise RuntimeError(f"Failed to parse scenario config {scenario_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Scenario config must be a mapping object: {scenario_path}")
    return _scenario_from_dict(data, fallback_id=scenario_path.stem)


def _slug_timestamp(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y%m%d-%H%M%S")


def _safe_parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _snapshot_tree(root: Path) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return snapshot
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        snapshot[str(path.relative_to(root))] = {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    return snapshot


def _diff_snapshots(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    created = sorted(set(after) - set(before))
    modified = sorted(
        path
        for path in set(before).intersection(after)
        if before[path] != after[path]
    )
    return {"created": created, "modified": modified}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _seed_project(project_dir: Path) -> None:
    _ensure_dir(project_dir / "data")
    (project_dir / "index.html").write_text(_DASHBOARD_HTML, encoding="utf-8")
    (project_dir / "styles.css").write_text(_DASHBOARD_CSS, encoding="utf-8")
    (project_dir / "app.js").write_text(_DASHBOARD_JS, encoding="utf-8")
    (project_dir / "README.md").write_text(_SEED_README, encoding="utf-8")
    (project_dir / "data" / "focus-sessions.json").write_text(_SESSIONS_JSON, encoding="utf-8")
    (project_dir / "data" / "tasks.json").write_text(_TASKS_JSON, encoding="utf-8")


def _get_builtin_scenarios() -> dict[str, TrainingScenario]:
    scenarios = {
        "vibecoder_stats_dashboard": TrainingScenario(
            id="vibecoder_stats_dashboard",
            name="Vibecoder Stats Dashboard",
            description="A short coding-assistant session that evolves a static dashboard from local fixtures.",
            max_prompts=12,
            steps=(
                TrainingStep(
                    id="inspect",
                    prompt=(
                        "Inspect this tiny dashboard project and immediately give a concrete 3-step implementation plan. "
                        "Only use files in the current project directory. Do not ask questions."
                    ),
                    fallback_prompt=(
                        "Keep the plan simple and stay inside the current project files only. "
                        "Make reasonable assumptions and proceed without clarification."
                    ),
                ),
                TrainingStep(
                    id="implement",
                    prompt=(
                        "Implement the plan now by editing existing files in this project. "
                        "Do not ask for project structure again. Keep it lightweight and avoid installing anything. "
                        "At the end, list changed files."
                    ),
                    fallback_prompt=(
                        "Proceed with direct edits to index.html, styles.css, and app.js using local JSON data. "
                        "Do not ask questions."
                    ),
                ),
                TrainingStep(
                    id="refine_layout",
                    prompt=(
                        "Refine the layout in code now so it feels intentional, readable, and a little warmer "
                        "without making it complex. Keep changes small and list changed files."
                    ),
                    fallback_prompt=(
                        "Apply one typography improvement and one spacing/color improvement directly in existing files."
                    ),
                ),
                TrainingStep(
                    id="add_insight",
                    prompt=(
                        "Add one useful additional insight card derived from the existing local data. "
                        "Implement it now and list changed files."
                    ),
                    fallback_prompt=(
                        "Use only existing data files and add a single new derived metric card in app.js."
                    ),
                ),
                TrainingStep(
                    id="fix_and_polish",
                    prompt=(
                        "Find one obvious rough edge in the current dashboard and fix it now. "
                        "Keep the change small and list changed files."
                    ),
                    fallback_prompt=(
                        "If no bug is obvious, apply one small quality improvement and implement it directly."
                    ),
                ),
                TrainingStep(
                    id="summarize",
                    prompt=(
                        "Summarize completed changes in 5 bullet points with: changed files, key metrics shown, "
                        "and remaining limitations. Keep it concise."
                    ),
                ),
            ),
        ),
        "ruleshield_health_check": TrainingScenario(
            id="ruleshield_health_check",
            name="RuleShield Health Check",
            description=(
                "Fast health-check scenario that targets common RuleShield intent families "
                "to validate routing and baseline telemetry."
            ),
            max_prompts=6,
            steps=(
                TrainingStep(id="status_ping", prompt="status"),
                TrainingStep(id="list_files", prompt="list files in this project"),
                TrainingStep(id="readme_summary", prompt="read README.md and summarize it briefly"),
                TrainingStep(id="show_changes", prompt="show me what changed"),
                TrainingStep(id="explain_output", prompt="explain what happened"),
                TrainingStep(id="run_confirm", prompt="run ls in this project and confirm when done"),
            ),
        ),
    }
    if DEFAULT_HEALTH_SCENARIO_PATH.is_file():
        try:
            scenarios["ruleshield_health_check"] = _load_scenario_from_path(
                DEFAULT_HEALTH_SCENARIO_PATH
            )
        except Exception:
            pass
    return scenarios


def _load_scenario(scenario_id: str, scenario_config: str | Path | None = None) -> TrainingScenario:
    if scenario_config:
        return _load_scenario_from_path(scenario_config)
    scenarios = _get_builtin_scenarios()
    try:
        return scenarios[scenario_id]
    except KeyError as exc:
        available = ", ".join(sorted(scenarios))
        raise RuntimeError(f"Unknown scenario '{scenario_id}'. Available: {available}") from exc


def _import_ai_agent() -> tuple[type[Any], str]:
    env_target = os.getenv("RULESHIELD_HERMES_AGENT_IMPORT", "").strip()
    candidates = [env_target] if env_target else []
    candidates.extend(["run_agent:AIAgent", "hermes:AIAgent"])

    errors: list[str] = []
    for target in candidates:
        if not target:
            continue
        module_name, _, attr_name = target.partition(":")
        attr = attr_name or "AIAgent"
        try:
            module = importlib.import_module(module_name)
            agent_cls = getattr(module, attr)
            return agent_cls, target
        except Exception as exc:
            errors.append(f"{target}: {type(exc).__name__}: {exc}")

    details = "; ".join(errors) if errors else "no import targets were configured"
    raise RuntimeError(
        "Hermes Python API is not importable. Install the Hermes library or set "
        "RULESHIELD_HERMES_AGENT_IMPORT to the correct import path. "
        f"Tried: {details}"
    )


def _detect_hermes_python() -> tuple[str, Path | None] | None:
    hermes_bin = shutil.which("hermes")
    if not hermes_bin:
        return None

    hermes_bin_path = Path(hermes_bin).resolve()
    try:
        first_line = hermes_bin_path.read_text(encoding="utf-8").splitlines()[0]
    except Exception:
        return None

    if not first_line.startswith("#!"):
        return None
    python_path = first_line[2:].strip()
    if python_path and Path(python_path).exists():
        hermes_root = None
        try:
            candidate = hermes_bin_path.parents[2]
            if (candidate / "run_agent.py").is_file():
                hermes_root = candidate
        except Exception:
            hermes_root = None
        return python_path, hermes_root
    return None


def _ensure_external_helper(run_dir: Path) -> Path:
    helper_path = run_dir / "_hermes_external_runner.py"
    if helper_path.exists():
        return helper_path

    helper_code = textwrap.dedent(
        """\
        from __future__ import annotations

        import inspect
        import json
        import os
        import sys
        from pathlib import Path

        def _extract_text(value):
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                for key in ("output_text", "final_text", "answer", "text"):
                    if key in value:
                        text = _extract_text(value[key])
                        if text:
                            return text

                # OpenAI chat-completions shape.
                choices = value.get("choices")
                if isinstance(choices, list) and choices:
                    text = _extract_text(choices[0])
                    if text:
                        return text

                # Codex Responses shape.
                output = value.get("output")
                if isinstance(output, list):
                    text = _extract_text(output)
                    if text:
                        return text

                for key in ("content", "message", "response"):
                    if key in value:
                        text = _extract_text(value[key])
                        if text:
                            return text

                return json.dumps(value, ensure_ascii=True)
            if isinstance(value, list):
                parts = [_extract_text(item) for item in value if item is not None]
                parts = [part for part in parts if part]
                return "\\n".join(parts)
            if hasattr(value, "model_dump"):
                return _extract_text(value.model_dump())
            if hasattr(value, "dict"):
                return _extract_text(value.dict())
            return str(value)

        def _build_agent(model, max_iterations, project_dir, base_url):
            model_lc = (model or "").strip().lower()
            is_openrouter_model = model_lc.endswith(":free") or "/" in model_lc
            provider = "openrouter" if is_openrouter_model else "openai-codex"
            api_mode = "chat_completions" if is_openrouter_model else "codex_responses"
            api_key = (
                (os.getenv("OPENROUTER_API_KEY") or "").strip()
                if is_openrouter_model
                else (os.getenv("OPENAI_API_KEY") or "").strip()
            ) or None

            import_target = ""
            try:
                from run_agent import AIAgent as Agent
                import_target = "run_agent:AIAgent"
            except Exception:
                # Hermes local installs often require the project root in sys.path
                # for run_agent -> agent.* imports.
                root_hint = Path(sys.executable).resolve().parents[2]
                if root_hint.is_dir():
                    sys.path.insert(0, str(root_hint))
                try:
                    from run_agent import AIAgent as Agent
                    import_target = "run_agent:AIAgent"
                except Exception:
                    from hermes import AIAgent as Agent
                    import_target = "hermes:AIAgent"

            kwargs = {
                "model": model,
                "base_url": base_url,
                "api_key": api_key,
                "provider": provider,
                "api_mode": api_mode,
                "quiet_mode": True,
                "skip_context_files": True,
                "skip_memory": True,
                "max_iterations": max_iterations,
                "enabled_toolsets": ["terminal", "file"],
                "disabled_toolsets": ["browser"],
                "cwd": str(project_dir),
                "workdir": str(project_dir),
            }
            try:
                signature = inspect.signature(Agent)
                supported = set(signature.parameters)
                kwargs = {key: value for key, value in kwargs.items() if key in supported}
            except Exception:
                pass
            try:
                agent = Agent(**kwargs)
            except TypeError:
                kwargs.pop("disabled_toolsets", None)
                kwargs.pop("cwd", None)
                kwargs.pop("workdir", None)
                agent = Agent(**kwargs)
            return agent, import_target

        def _send(agent, prompt):
            last_text = ""
            for method_name in ("chat", "run", "ask", "invoke", "send_message", "complete", "respond"):
                method = getattr(agent, method_name, None)
                if callable(method):
                    text = _extract_text(method(prompt))
                    if text.strip():
                        return text
                    last_text = text
            if callable(agent):
                text = _extract_text(agent(prompt))
                if text.strip():
                    return text
                last_text = text
            if last_text:
                return last_text
            return ""

        def main():
            model = sys.argv[1]
            max_iterations = int(sys.argv[2])
            project_dir = Path(sys.argv[3]).resolve()
            base_url = sys.argv[4]
            payload = json.loads(sys.stdin.read())
            prompt = payload.get("prompt", "")
            try:
                agent, import_target = _build_agent(model, max_iterations, project_dir, base_url)
                response_text = _send(agent, prompt)
                out = {"ok": True, "response_text": response_text, "import_target": import_target}
            except Exception as exc:
                out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            print(json.dumps(out, ensure_ascii=True))

        if __name__ == "__main__":
            main()
        """
    )
    helper_path.write_text(helper_code, encoding="utf-8")
    return helper_path


def _send_prompt_external(
    *,
    python_bin: str,
    helper_path: Path,
    prompt: str,
    model: str,
    max_iterations: int,
    project_dir: Path,
    hermes_root: Path | None,
    proxy_url: str,
) -> dict[str, Any]:
    env = os.environ.copy()
    if hermes_root is not None:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{hermes_root}{os.pathsep}{existing}" if existing else str(hermes_root)
        )

    proc = subprocess.run(
        [
            python_bin,
            str(helper_path),
            model,
            str(max_iterations),
            str(project_dir),
            f"{proxy_url.rstrip('/')}/v1",
        ],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        cwd=str(project_dir),
        env=env,
        timeout=180,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    if not stdout:
        stderr = (proc.stderr or "").strip()
        return {"ok": False, "error": f"External Hermes runner produced no output. {stderr}"}
    try:
        parsed = json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": f"Invalid external runner output: {stdout[:300]}"}

    if parsed.get("ok") and not str(parsed.get("response_text", "")).strip():
        # Some models can return tool calls without final assistant text within
        # a low iteration budget. Treat this as a non-fatal placeholder so the
        # run can continue and still produce shadow/feedback signals.
        log_lines = stdout.splitlines()[:-1]
        tail = "\n".join(log_lines[-12:]).strip().lower()
        if "tool_calls" in tail:
            parsed["response_text"] = "[tool_calls_without_final_text]"
            return parsed

        # Keep recent runner logs to make genuine empty responses debuggable.
        stderr_tail = (proc.stderr or "").strip()[-800:]
        detail_parts = []
        if tail:
            detail_parts.append(f"runner_stdout_tail:\n{tail}")
        if stderr_tail:
            detail_parts.append(f"runner_stderr_tail:\n{stderr_tail}")
        detail = "\n\n".join(detail_parts).strip()
        return {
            "ok": False,
            "error": f"External Hermes returned empty response.{f' {detail}' if detail else ''}",
        }
    return parsed


def _is_openrouter_like_model(model: str) -> bool:
    model_lc = (model or "").strip().lower()
    return bool(model_lc) and (model_lc.endswith(":free") or "/" in model_lc)


def _build_agent(
    agent_cls: type[Any],
    *,
    model: str,
    max_iterations: int,
    project_dir: Path,
    proxy_url: str,
) -> Any:
    is_openrouter_model = _is_openrouter_like_model(model)
    provider = "openrouter" if is_openrouter_model else "openai-codex"
    api_mode = "chat_completions" if is_openrouter_model else "codex_responses"
    api_key = (
        (os.getenv("OPENROUTER_API_KEY") or "").strip()
        if is_openrouter_model
        else (os.getenv("OPENAI_API_KEY") or "").strip()
    ) or None

    candidate_kwargs = {
        "model": model,
        "base_url": f"{proxy_url.rstrip('/')}/v1",
        "api_key": api_key,
        "provider": provider,
        "api_mode": api_mode,
        "quiet_mode": True,
        "skip_context_files": True,
        "skip_memory": True,
        "max_iterations": max_iterations,
        "enabled_toolsets": DEFAULT_TRAINING_TOOLSETS,
        "disabled_toolsets": ["browser"],
        "cwd": str(project_dir),
        "workdir": str(project_dir),
    }

    try:
        signature = inspect.signature(agent_cls)
    except (TypeError, ValueError):
        signature = None

    kwargs = candidate_kwargs
    if signature is not None:
        supported = set(signature.parameters)
        kwargs = {key: value for key, value in candidate_kwargs.items() if key in supported}

    try:
        return agent_cls(**kwargs)
    except TypeError:
        reduced = dict(kwargs)
        reduced.pop("disabled_toolsets", None)
        reduced.pop("cwd", None)
        reduced.pop("workdir", None)
        return agent_cls(**reduced)


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("output_text", "final_text", "answer", "text"):
            if key in value:
                text = _extract_text(value[key])
                if text:
                    return text

        choices = value.get("choices")
        if isinstance(choices, list) and choices:
            text = _extract_text(choices[0])
            if text:
                return text

        output = value.get("output")
        if isinstance(output, list):
            text = _extract_text(output)
            if text:
                return text

        for key in ("content", "message", "response"):
            if key in value:
                text = _extract_text(value[key])
                if text:
                    return text

        return json.dumps(value, ensure_ascii=True, indent=2)
    if isinstance(value, list):
        parts = [_extract_text(item) for item in value if item is not None]
        parts = [part for part in parts if part]
        return "\n".join(parts)
    if hasattr(value, "model_dump"):
        return _extract_text(value.model_dump())
    if hasattr(value, "dict"):
        return _extract_text(value.dict())
    return str(value)


def _send_prompt(agent: Any, prompt: str) -> str:
    last_text = ""
    for method_name in ("chat", "run", "ask", "invoke", "send_message", "complete", "respond"):
        method = getattr(agent, method_name, None)
        if callable(method):
            text = _extract_text(method(prompt))
            if text.strip():
                return text
            last_text = text
    if callable(agent):
        text = _extract_text(agent(prompt))
        if text.strip():
            return text
        last_text = text
    if last_text:
        return last_text
    return ""


def _write_runtime_hermes_config(runtime_home: Path, proxy_url: str) -> None:
    hermes_dir = _ensure_dir(runtime_home / ".hermes")
    config_path = hermes_dir / "config.yaml"
    cfg: dict[str, Any] = {}
    if config_path.exists():
        try:
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            cfg = {}
    model_cfg = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
    model_cfg["base_url"] = f"{proxy_url.rstrip('/')}/v1"
    cfg["model"] = model_cfg
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


def _copy_runtime_auth_state(runtime_home: Path, source_home: str | None) -> None:
    if not source_home:
        return
    source_hermes = Path(source_home) / ".hermes"
    if not source_hermes.is_dir():
        return
    target_hermes = _ensure_dir(runtime_home / ".hermes")
    candidate_files = (
        "auth.json",
        "auth.lock",
        ".env",
        "config.yaml",
        "state.db",
        "state.db-shm",
        "state.db-wal",
        "processes.json",
    )
    for filename in candidate_files:
        src = source_hermes / filename
        dst = target_hermes / filename
        if src.is_file():
            try:
                shutil.copy2(src, dst)
            except Exception:
                continue

    # Hermes Codex auth may be sourced from ~/.codex/auth.json.
    source_codex_auth = Path(source_home) / ".codex" / "auth.json"
    if source_codex_auth.is_file():
        target_codex_dir = _ensure_dir(runtime_home / ".codex")
        target_codex_auth = target_codex_dir / "auth.json"
        try:
            shutil.copy2(source_codex_auth, target_codex_auth)
            try:
                auth_obj = json.loads(target_codex_auth.read_text(encoding="utf-8"))
                if isinstance(auth_obj, dict):
                    tokens = auth_obj.get("tokens")
                    access_token = None
                    if isinstance(tokens, dict):
                        raw = tokens.get("access_token")
                        if raw is not None:
                            text = str(raw).strip()
                            if text and text.lower() not in {"none", "null"}:
                                access_token = text
                    current_key = auth_obj.get("OPENAI_API_KEY")
                    key_text = str(current_key).strip() if current_key is not None else ""
                    if access_token and (not key_text or key_text.lower() in {"none", "null"}):
                        auth_obj["OPENAI_API_KEY"] = access_token
                        target_codex_auth.write_text(
                            json.dumps(auth_obj, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
            except Exception:
                pass
        except Exception:
            pass


def _sanitize_runtime_dotenv(runtime_home: Path, *, clear_openrouter_key: bool) -> None:
    """Remove provider keys that force the wrong auth path in isolated runs."""
    env_path = runtime_home / ".hermes" / ".env"
    if not env_path.is_file():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    sanitized: list[str] = []
    for line in lines:
        if clear_openrouter_key and line.startswith("OPENROUTER_API_KEY="):
            sanitized.append("OPENROUTER_API_KEY=")
            continue
        if line.startswith("LLM_MODEL="):
            # Let the runner-provided model argument control the request model.
            sanitized.append("LLM_MODEL=")
            continue
        sanitized.append(line)
    env_path.write_text("\n".join(sanitized) + "\n", encoding="utf-8")


def _apply_runtime_env(
    settings: Settings,
    runtime_home: Path,
    project_dir: Path,
    proxy_url: str,
    model: str,
) -> dict[str, str | None]:
    previous = {
        "HOME": os.environ.get("HOME"),
        "TMPDIR": os.environ.get("TMPDIR"),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
        "PWD": os.environ.get("PWD"),
    }
    tmp_dir = _ensure_dir(runtime_home / "tmp")
    os.environ["HOME"] = str(runtime_home)
    os.environ["TMPDIR"] = str(tmp_dir)
    os.environ["PWD"] = str(project_dir)
    _copy_runtime_auth_state(runtime_home, previous.get("HOME"))
    wants_openrouter = _is_openrouter_like_model(model)
    _sanitize_runtime_dotenv(runtime_home, clear_openrouter_key=not wants_openrouter)
    _write_runtime_hermes_config(runtime_home, proxy_url)

    # Keep auth behavior aligned with manual Hermes runs.
    os.environ.pop("OPENAI_API_KEY", None)
    if not wants_openrouter:
        os.environ.pop("OPENROUTER_API_KEY", None)
    return previous


def _restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _filter_recent_entries(entries: list[dict[str, Any]], started_at: datetime) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        entry_time = _safe_parse_timestamp(str(entry.get("created_at", "")))
        if entry_time is None or entry_time >= started_at:
            filtered.append(entry)
    return filtered


def _count_resolution_types(requests: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in requests:
        key = str(entry.get("resolution_type") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def _extract_runtime_bearer(runtime_home: Path, model: str | None = None) -> str | None:
    def _clean_token(value: Any) -> str | None:
        if value is None:
            return None
        token = str(value).strip()
        if not token:
            return None
        if token.lower() in {"none", "null"}:
            return None
        return token

    # Runtime auth for training/monitor flows is sourced from Hermes .env.
    env_vars = _parse_dotenv(runtime_home / ".hermes" / ".env")
    prefers_openrouter = _is_openrouter_like_model(model or "")
    # nosec - environment variable names, not secret values
    primary_key = "OPENROUTER_API_KEY" if prefers_openrouter else "OPENAI_API_KEY"
    secondary_key = "OPENAI_API_KEY" if prefers_openrouter else "OPENROUTER_API_KEY"
    for key in (primary_key, secondary_key):
        token = _clean_token(env_vars.get(key))
        if token:
            return token
    return None


def _emit_proxy_probe(
    *,
    proxy_url: str,
    model: str,
    prompt: str,
    runtime_home: Path,
) -> str:
    token = _extract_runtime_bearer(runtime_home, model=model)
    headers: dict[str, str] = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"

    payload = {
        "model": model,
        "instructions": "You are a concise assistant.",
        "input": [{"role": "user", "content": prompt}],
        "stream": True,
        "store": False,
    }
    try:
        # Use the Codex Responses endpoint for a faithful proxy health probe.
        with httpx.stream(
            "POST",
            f"{proxy_url.rstrip('/')}/responses",
            headers=headers,
            json=payload,
            timeout=25.0,
        ) as response:
            return f"http_{response.status_code}"
    except Exception as exc:
        return f"error:{type(exc).__name__}"


def _send_prompt_direct_via_proxy(
    *,
    proxy_url: str,
    model: str,
    prompt: str,
    runtime_home: Path,
) -> str:
    """Low-overhead fallback when Hermes agent calls fail with hard 402 limits."""
    token = _extract_runtime_bearer(runtime_home, model=model)
    headers: dict[str, str] = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"

    payload = {
        "model": model,
        "instructions": "You are a concise assistant.",
        "input": [{"role": "user", "content": prompt}],
        "stream": True,
        "store": False,
    }
    text_parts: list[str] = []
    with httpx.stream(
        "POST",
        f"{proxy_url.rstrip('/')}/responses",
        headers=headers,
        json=payload,
        timeout=40.0,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode(errors="replace")
            if line.startswith("data: "):
                raw = line[6:]
                if raw.strip() in ("[DONE]", ""):
                    continue
                try:
                    event = json.loads(raw)
                except Exception:
                    continue
            else:
                # Some providers emit plain JSON SSE lines.
                try:
                    event = json.loads(line)
                except Exception:
                    continue

            event_type = str(event.get("type", ""))
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str):
                    text_parts.append(delta)
            elif event_type == "response.output_text.done":
                text = event.get("text")
                if isinstance(text, str):
                    text_parts.append(text)

    return "".join(text_parts).strip()


def _fetch_json(client: httpx.Client, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def _collect_ruleshield_summary(proxy_url: str, started_at: datetime) -> dict[str, Any]:
    base = proxy_url.rstrip("/")
    with httpx.Client() as client:
        stats = _fetch_json(client, f"{base}/api/stats")
        # /api/requests currently allows max=200.
        requests_payload = _fetch_json(client, f"{base}/api/requests", params={"limit": 200})
        shadow = _fetch_json(client, f"{base}/api/shadow")
        feedback = _fetch_json(client, f"{base}/api/feedback", params={"limit": 300})
        rule_events = _fetch_json(client, f"{base}/api/rule-events", params={"limit": 300})

    recent_requests = _filter_recent_entries(list(requests_payload.get("requests", [])), started_at)
    recent_feedback = _filter_recent_entries(list(feedback.get("entries", [])), started_at)
    recent_rule_events = _filter_recent_entries(list(rule_events.get("events", [])), started_at)

    confidence_events = [
        entry for entry in recent_rule_events if entry.get("event_type") == "confidence_update"
    ]
    activation_events = [
        entry for entry in recent_rule_events if str(entry.get("event_type", "")).startswith("rule_")
    ]

    return {
        "stats_snapshot": stats,
        "recent_requests": recent_requests,
        "request_breakdown": _count_resolution_types(recent_requests),
        "shadow_snapshot": shadow,
        "feedback_snapshot": feedback,
        "recent_feedback": recent_feedback,
        "recent_rule_events": recent_rule_events,
        "confidence_events": confidence_events,
        "activation_events": activation_events,
    }


def _build_markdown_summary(
    *,
    scenario: TrainingScenario,
    run_id: str,
    started_at: datetime,
    run_error: str | None,
    result_summary: dict[str, Any],
    workspace_changes: dict[str, Any],
    transcript: list[dict[str, Any]],
) -> str:
    lines = [
        f"# RuleShield Prompt Training Run: {run_id}",
        "",
        f"- Scenario: `{scenario.id}`",
        f"- Started (UTC): `{started_at.strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- Prompts sent: `{len(transcript)}`",
        "",
    ]

    if run_error:
        lines.extend(
            [
                "## Run Error",
                "",
                f"- `{run_error}`",
                "",
            ]
        )

    lines.extend(
        [
        "## RuleShield Summary",
        "",
        ]
    )

    request_breakdown = result_summary.get("request_breakdown", {})
    if request_breakdown:
        for key, value in sorted(request_breakdown.items()):
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- No recent request entries detected for this run window.")

    shadow_snapshot = result_summary.get("shadow_snapshot", {})
    lines.extend(
        [
            "",
            "## Shadow Mode",
            "",
            f"- Enabled: `{shadow_snapshot.get('enabled', False)}`",
            f"- Total comparisons: `{shadow_snapshot.get('total_comparisons', 0)}`",
            f"- Average similarity: `{shadow_snapshot.get('avg_similarity_pct', 0.0)}%`",
            f"- Rules ready: `{shadow_snapshot.get('rules_ready', 0)}`",
        ]
    )

    confidence_events = result_summary.get("confidence_events", [])
    lines.extend(["", "## Feedback Loop Signals", ""])
    if confidence_events:
        for entry in confidence_events[:12]:
            details = entry.get("details") or {}
            before = details.get("previous_confidence", "?")
            after = details.get("new_confidence", "?")
            direction = details.get("direction", "?")
            lines.append(
                f"- {entry.get('rule_id', 'unknown')}: `{before} -> {after}` ({direction})"
            )
    else:
        lines.append("- No confidence changes detected in this run window.")

    lines.extend(["", "## Workspace Changes", ""])
    lines.append(f"- Project files created: `{len(workspace_changes.get('project', {}).get('created', []))}`")
    lines.append(f"- Project files modified: `{len(workspace_changes.get('project', {}).get('modified', []))}`")
    lines.append(f"- Runtime-home files created: `{len(workspace_changes.get('runtime_home', {}).get('created', []))}`")
    lines.append(f"- Runtime-home files modified: `{len(workspace_changes.get('runtime_home', {}).get('modified', []))}`")

    lines.extend(["", "## Transcript", ""])
    for entry in transcript:
        lines.append(f"### {entry['step_id']}")
        lines.append("")
        lines.append(f"Prompt: {entry['prompt']}")
        lines.append("")
        lines.append("Response:")
        lines.append("")
        response_text = entry["response_text"].strip() or "[empty]"
        lines.append("```text")
        lines.append(response_text[:3000])
        lines.append("```")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _emit_training_log(message: str) -> None:
    """Emit progress output that is visible in the test monitor immediately."""
    print(message, flush=True)


def run_prompt_training(
    *,
    scenario_id: str = "vibecoder_stats_dashboard",
    scenario_config: str | Path | None = None,
    model: str = DEFAULT_MODEL,
    max_prompts: int | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    proxy_url: str = DEFAULT_PROXY_URL,
    max_iterations: int = 8,
    settings: Settings | None = None,
) -> TrainingRunResult:
    settings_obj = settings or load_settings()
    scenario = _load_scenario(scenario_id, scenario_config=scenario_config)
    prompt_limit = max_prompts or scenario.max_prompts

    run_started = datetime.now(timezone.utc)
    run_id = _slug_timestamp(run_started)
    run_dir = _ensure_dir(Path(output_dir) / run_id)
    project_dir = _ensure_dir(run_dir / "project")
    runtime_home = _ensure_dir(run_dir / "runtime-home")
    reports_dir = _ensure_dir(run_dir / "reports")

    _seed_project(project_dir)
    project_before = _snapshot_tree(project_dir)
    runtime_before = _snapshot_tree(runtime_home)

    previous_env = _apply_runtime_env(
        settings_obj, runtime_home, project_dir, proxy_url, model
    )
    transcript: list[dict[str, Any]] = []
    hermes_import_target = ""
    hermes_available = False
    failure_error: str | None = None

    start_monotonic = datetime.now(timezone.utc)
    try:
        agent_cls, hermes_import_target = _import_ai_agent()
        agent = _build_agent(
            agent_cls,
            model=model,
            max_iterations=max_iterations,
            project_dir=project_dir,
            proxy_url=proxy_url,
        )
        hermes_available = True

        for step in scenario.steps[:prompt_limit]:
            used_fallback = False
            prompt = step.prompt
            error_message: str | None = None
            probe_status: str | None = None
            _emit_training_log(f"[training] step={step.id} start")
            _emit_training_log(f"PROMPT ({step.id}): {prompt}")

            try:
                response_text = _send_prompt(agent, prompt)
            except Exception as exc:
                error_message = str(exc)
                if step.fallback_prompt:
                    used_fallback = True
                    _emit_training_log(
                        f"[fallback] step={step.id} type=step_prompt reason=primary_send_exception"
                    )
                    prompt = step.fallback_prompt
                    response_text = _send_prompt(agent, prompt)
                else:
                    raise

            probe_status = _emit_proxy_probe(
                proxy_url=proxy_url,
                model=model,
                prompt=prompt,
                runtime_home=runtime_home,
            )
            _emit_training_log(
                f"RESPONSE ({step.id}): {response_text.strip() or '[empty]'}"
            )
            if error_message:
                _emit_training_log(f"ERROR ({step.id}): {error_message}")
            _emit_training_log(f"PROBE ({step.id}): {probe_status}")
            _emit_training_log(
                f"[training] step={step.id} done response_chars={len(response_text.strip())} probe={probe_status}"
            )

            transcript.append(
                asdict(
                    TrainingStepResult(
                        step_id=step.id,
                        prompt=prompt,
                        response_text=response_text,
                        used_fallback=used_fallback,
                        error=error_message,
                        probe_status=probe_status,
                    )
                )
            )
    except Exception as exc:
        runtime = _detect_hermes_python()
        if not runtime:
            _emit_training_log(
                f"[error] type=runner_selection reason=local_import_failed no_external_runtime detail={type(exc).__name__}: {exc}"
            )
            failure_error = str(exc)
        else:
            fallback_python, hermes_root = runtime
            helper_path = _ensure_external_helper(run_dir)
            hermes_available = True
            hermes_import_target = f"external-python:{fallback_python}"
            _emit_training_log(
                f"[runner] mode=external reason=local_import_unavailable python={fallback_python}"
            )
            _emit_training_log(
                f"[runner] local_import_detail={type(exc).__name__}: {exc}"
            )
            try:
                for step in scenario.steps[:prompt_limit]:
                    used_fallback = False
                    prompt = step.prompt
                    error_message: str | None = None
                    probe_status: str | None = None
                    _emit_training_log(f"[training] step={step.id} start")
                    _emit_training_log(f"PROMPT ({step.id}): {prompt}")

                    result = _send_prompt_external(
                        python_bin=fallback_python,
                        helper_path=helper_path,
                        prompt=prompt,
                        model=model,
                        max_iterations=max_iterations,
                        project_dir=project_dir,
                        hermes_root=hermes_root,
                        proxy_url=proxy_url,
                    )
                    if not result.get("ok", False):
                        error_message = str(result.get("error", "unknown external runner error"))
                        if step.fallback_prompt:
                            used_fallback = True
                            _emit_training_log(
                                f"[fallback] step={step.id} type=step_prompt reason=external_runner_error"
                            )
                            prompt = step.fallback_prompt
                            result = _send_prompt_external(
                                python_bin=fallback_python,
                                helper_path=helper_path,
                                prompt=prompt,
                                model=model,
                                max_iterations=max_iterations,
                                project_dir=project_dir,
                                hermes_root=hermes_root,
                                proxy_url=proxy_url,
                            )
                    if not result.get("ok", False):
                        failure_text = str(result.get("error", "external Hermes execution failed"))
                        if "Error code: 402" in failure_text or "Prompt tokens limit exceeded" in failure_text:
                            _emit_training_log(
                                f"[fallback] step={step.id} type=direct_proxy reason=hermes_402_limit"
                            )
                            try:
                                direct_text = _send_prompt_direct_via_proxy(
                                    proxy_url=proxy_url,
                                    model=model,
                                    prompt=prompt,
                                    runtime_home=runtime_home,
                                )
                                if direct_text:
                                    result = {
                                        "ok": True,
                                        "response_text": direct_text,
                                        "import_target": str(result.get("import_target", hermes_import_target)),
                                    }
                                    error_message = (
                                        (error_message + " | " if error_message else "")
                                        + "Hermes 402 fallback via direct /responses"
                                    )
                                    _emit_training_log(
                                        f"[fallback] step={step.id} type=direct_proxy result=success"
                                    )
                            except Exception as direct_exc:
                                failure_text += f" | direct fallback failed: {type(direct_exc).__name__}: {direct_exc}"
                                _emit_training_log(
                                    f"[fallback] step={step.id} type=direct_proxy result=failed detail={type(direct_exc).__name__}: {direct_exc}"
                                )
                                result = {"ok": False, "error": failure_text}
                    if not result.get("ok", False):
                        raise RuntimeError(str(result.get("error", "external Hermes execution failed")))

                    probe_status = _emit_proxy_probe(
                        proxy_url=proxy_url,
                        model=model,
                        prompt=prompt,
                        runtime_home=runtime_home,
                    )

                    hermes_import_target = str(result.get("import_target", hermes_import_target))
                    response_text = str(result.get("response_text", ""))
                    _emit_training_log(
                        f"RESPONSE ({step.id}): {response_text.strip() or '[empty]'}"
                    )
                    if error_message:
                        _emit_training_log(f"ERROR ({step.id}): {error_message}")
                    _emit_training_log(f"PROBE ({step.id}): {probe_status}")
                    _emit_training_log(
                        f"[training] step={step.id} done response_chars={len(response_text.strip())} probe={probe_status}"
                    )
                    transcript.append(
                        asdict(
                            TrainingStepResult(
                                step_id=step.id,
                                prompt=prompt,
                                response_text=response_text,
                                used_fallback=used_fallback,
                                error=error_message,
                                probe_status=probe_status,
                            )
                        )
                    )
            except Exception as fallback_exc:
                failure_error = str(fallback_exc)
    finally:
        _restore_env(previous_env)

    project_after = _snapshot_tree(project_dir)
    runtime_after = _snapshot_tree(runtime_home)
    workspace_changes = {
        "project": _diff_snapshots(project_before, project_after),
        "runtime_home": _diff_snapshots(runtime_before, runtime_after),
    }

    try:
        ruleshield_summary = _collect_ruleshield_summary(proxy_url, run_started)
    except Exception as exc:
        ruleshield_summary = {
            "error": str(exc),
            "stats_snapshot": {},
            "recent_requests": [],
            "request_breakdown": {},
            "shadow_snapshot": {},
            "feedback_snapshot": {},
            "recent_feedback": [],
            "recent_rule_events": [],
            "confidence_events": [],
            "activation_events": [],
        }
    isolation_ok = True
    summary_payload = {
        "run_id": run_id,
        "scenario": asdict(scenario),
        "model": model,
        "proxy_url": proxy_url,
        "started_at": run_started.isoformat(),
        "duration_seconds": round((datetime.now(timezone.utc) - start_monotonic).total_seconds(), 2),
        "hermes_import_target": hermes_import_target,
        "hermes_available": hermes_available,
        "workspace_changes": workspace_changes,
        "isolation_ok": isolation_ok,
        "transcript": transcript,
        "ruleshield_summary": ruleshield_summary,
        "error": failure_error,
    }

    transcript_path = reports_dir / "transcript.json"
    summary_json_path = reports_dir / "ruleshield-summary.json"
    summary_md_path = reports_dir / "ruleshield-summary.md"

    transcript_path.write_text(json.dumps(transcript, indent=2), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    summary_md_path.write_text(
        _build_markdown_summary(
            scenario=scenario,
            run_id=run_id,
            started_at=run_started,
            run_error=failure_error,
            result_summary=ruleshield_summary,
            workspace_changes=workspace_changes,
            transcript=transcript,
        ),
        encoding="utf-8",
    )

    if failure_error:
        raise RuntimeError(
            f"{failure_error} Run artifacts were written to {run_dir}."
        )

    return TrainingRunResult(
        run_id=run_id,
        scenario_id=scenario.id,
        run_dir=str(run_dir),
        project_dir=str(project_dir),
        reports_dir=str(reports_dir),
        prompts_sent=len(transcript),
        transcript_path=str(transcript_path),
        summary_json_path=str(summary_json_path),
        summary_md_path=str(summary_md_path),
        duration_seconds=summary_payload["duration_seconds"],
        isolation_ok=isolation_ok,
        hermes_import_target=hermes_import_target,
        hermes_available=hermes_available,
    )
