"""RuleShield Hermes -- CLI entry point.

Full Click-based CLI for initializing, starting, monitoring, and managing
the RuleShield cost-optimizer proxy.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

console = Console()

_BRAND = "magenta"
_CACHE_CLR = "bright_green"
_RULE_CLR = "bright_cyan"
_LLM_CLR = "yellow"
_DIM = "dim"

RULESHIELD_DIR = Path.home() / ".ruleshield"
RULES_DIR = RULESHIELD_DIR / "rules"
DB_PATH = RULESHIELD_DIR / "cache.db"
PID_PATH = RULESHIELD_DIR / "proxy.pid"


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option("0.1.0", prog_name="RuleShield Hermes")
def main() -> None:
    """RuleShield Hermes -- LLM cost optimizer proxy.

    \b
    RL integration:  Hermes RL Training (GRPO/Atropos) and Self-Evolution
    (DSPy/GEPA) stubs are available via ruleshield.feedback.HermesRLInterface.
    """
    pass


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@main.command()
@click.option("--hermes", is_flag=True, help="Auto-configure Hermes Agent integration.")
def init(hermes: bool) -> None:
    """Initialize RuleShield configuration and rules."""
    from ruleshield.config import (
        RULESHIELD_DIR as CFG_DIR,
        patch_hermes_config,
        write_default_config,
    )

    console.print()
    console.print(
        Panel(
            Text("RuleShield Hermes Setup", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(1, 4),
        )
    )
    console.print()

    # Step 1: Create directory structure
    console.print(f"  [bold]1.[/bold] Creating [cyan]~/.ruleshield/[/cyan] directory...", end=" ")
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    console.print("[bright_green]done[/bright_green]")

    # Step 2: Write default config
    console.print(f"  [bold]2.[/bold] Writing default [cyan]config.yaml[/cyan]...", end=" ")
    config_path = write_default_config()
    console.print("[bright_green]done[/bright_green]")

    # Step 3: Copy default rules
    console.print(f"  [bold]3.[/bold] Installing default rules...", end=" ")
    bundled_rules = Path(__file__).resolve().parent.parent / "rules" / "default_hermes.json"
    dest_rules = RULES_DIR / "default_hermes.json"
    if bundled_rules.is_file():
        shutil.copy2(str(bundled_rules), str(dest_rules))
        console.print("[bright_green]done[/bright_green]")
    else:
        console.print("[yellow]skipped (bundled rules not found)[/yellow]")

    # Step 4: Hermes integration
    if hermes:
        console.print(f"  [bold]4.[/bold] Configuring Hermes Agent integration...", end=" ")
        success = patch_hermes_config()
        if success:
            console.print("[bright_green]done[/bright_green]")
        else:
            console.print("[yellow]skipped (Hermes config not found at ~/.hermes/cli-config.yaml)[/yellow]")
            console.print()
            console.print(
                "     [dim]To configure manually, set [cyan]api_base: http://127.0.0.1:8337[/cyan]"
                " in your Hermes config.[/dim]"
            )
    else:
        console.print(f"  [bold]4.[/bold] Hermes integration [dim]skipped (use --hermes to enable)[/dim]")

    # Success summary
    console.print()
    console.print(
        Panel(
            Text("Setup Complete!", justify="center", style="bold bright_green"),
            border_style="bright_green",
            padding=(0, 4),
        )
    )

    # Quick Start guide
    console.print()
    qs_table = Table(
        title="Quick Start",
        title_style=f"bold {_BRAND}",
        show_header=False,
        border_style="grey37",
        padding=(0, 2),
        expand=False,
    )
    qs_table.add_column("Step", style="bold", justify="right", width=4)
    qs_table.add_column("Command", style="cyan")
    qs_table.add_column("Description", style=_DIM)

    qs_table.add_row("1.", "ruleshield start", "Start the proxy server")
    qs_table.add_row("2.", "export RULESHIELD_API_KEY=sk-...", "Set your API key")
    qs_table.add_row("3.", "ruleshield stats", "View cost savings")
    qs_table.add_row("4.", "ruleshield rules", "List active rules")

    console.print(qs_table)
    console.print()
    console.print(f"  Config:  [cyan]{config_path}[/cyan]")
    console.print(f"  Rules:   [cyan]{RULES_DIR}[/cyan]")
    console.print(f"  Proxy:   [cyan]http://localhost:8337[/cyan]")
    console.print()


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


@main.command()
@click.option("--port", type=int, default=None, help="Override proxy port.")
@click.option("--daemon", is_flag=True, help="Run proxy in the background.")
def start(port: int | None, daemon: bool) -> None:
    """Start the RuleShield proxy server."""
    from ruleshield.config import load_settings
    from ruleshield.metrics import print_startup_banner

    settings = load_settings()
    if port is not None:
        settings.port = port

    print_startup_banner()

    console.print(f"  Proxy running on [bold cyan]http://localhost:{settings.port}[/bold cyan]")
    console.print(f"  Forwarding to    [dim]{settings.provider_url}[/dim]")
    console.print(f"  Cache: [{'bright_green' if settings.cache_enabled else 'red'}]"
                  f"{'enabled' if settings.cache_enabled else 'disabled'}[/]  "
                  f"Rules: [{'bright_green' if settings.rules_enabled else 'red'}]"
                  f"{'enabled' if settings.rules_enabled else 'disabled'}[/]")
    console.print()
    console.print(f"  [dim]Press Ctrl+C to stop[/dim]")
    console.print()

    import uvicorn

    uvicorn.run(
        "ruleshield.proxy:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level,
    )


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


@main.command()
def stop() -> None:
    """Stop the proxy server (if running as daemon)."""
    if not PID_PATH.exists():
        console.print("[yellow]No running proxy found.[/yellow]")
        console.print("[dim]If the proxy is running in the foreground, use Ctrl+C to stop it.[/dim]")
        return

    try:
        pid = int(PID_PATH.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        PID_PATH.unlink(missing_ok=True)
        console.print(f"[bright_green]Proxy (PID {pid}) stopped.[/bright_green]")
    except ProcessLookupError:
        PID_PATH.unlink(missing_ok=True)
        console.print("[yellow]Proxy process not found (stale PID file removed).[/yellow]")
    except Exception as exc:
        console.print(f"[red]Failed to stop proxy: {exc}[/red]")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def _query_stats_from_db() -> dict[str, Any]:
    """Query aggregated stats from the SQLite request_log table."""
    stats: dict[str, Any] = {
        "total_requests": 0,
        "cache_hits": 0,
        "rule_hits": 0,
        "passthrough": 0,
        "llm_calls": 0,
        "cost_without": 0.0,
        "cost_with": 0.0,
        "estimated_cost_saved": 0.0,
    }

    if not DB_PATH.exists():
        return stats

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()

        # Total requests
        cur.execute("SELECT COUNT(*) FROM request_log")
        stats["total_requests"] = cur.fetchone()[0]

        # By resolution type
        cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'cache'")
        stats["cache_hits"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'rule'")
        stats["rule_hits"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'passthrough'")
        stats["passthrough"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'llm'")
        stats["llm_calls"] = cur.fetchone()[0]

        # Cost: LLM calls are the actual cost, cache/rule hits are savings
        cur.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM request_log WHERE resolution_type = 'llm'")
        stats["cost_with"] = round(float(cur.fetchone()[0]), 6)

        cur.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM request_log")
        total_cost = round(float(cur.fetchone()[0]), 6)

        # Estimate: total cost approximates what it would have cost without RuleShield
        stats["cost_without"] = total_cost if total_cost > 0 else 0.0
        stats["estimated_cost_saved"] = stats["cost_without"] - stats["cost_with"]

        conn.close()
    except Exception:
        pass

    return stats


@main.command()
def stats() -> None:
    """Show cost savings statistics."""
    from ruleshield.metrics import print_stats_summary

    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy and send some requests first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    stats_data = _query_stats_from_db()
    print_stats_summary(stats_data)


# ---------------------------------------------------------------------------
# shadow-stats
# ---------------------------------------------------------------------------


@main.command("shadow-stats")
@click.option("--rule", "rule_id", default=None, help="Only show stats for one rule id.")
@click.option("--recent", type=int, default=None, help="Only analyze the most recent N shadow comparisons.")
def shadow_stats(rule_id: str | None, recent: int | None) -> None:
    """Show shadow mode comparison statistics.

    \b
    Shadow mode runs rules AND the LLM in parallel, discards the rule
    response, and logs a comparison.  This command shows how accurately
    each rule would have answered compared to the real LLM.
    Rules with high similarity (>80%) are flagged as ready for activation.
    """
    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy with shadow_mode enabled first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    import sqlite3 as _sqlite3

    try:
        conn = _sqlite3.connect(str(DB_PATH))
        conn.row_factory = _sqlite3.Row
        cur = conn.cursor()

        # Check if the shadow_log table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='shadow_log'"
        )
        if cur.fetchone() is None:
            console.print()
            console.print("[yellow]No shadow data yet.[/yellow] The shadow_log table has not been created.")
            console.print(
                "[dim]Enable shadow mode in config (shadow_mode: true) and send some requests.[/dim]"
            )
            console.print()
            conn.close()
            return

        where_clauses: list[str] = []
        params: list[Any] = []
        if rule_id:
            where_clauses.append("rule_id = ?")
            params.append(rule_id)

        base_query = "SELECT * FROM shadow_log"
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)
        if recent is not None:
            base_query = f"SELECT * FROM ({base_query} ORDER BY id DESC LIMIT ?) recent"
            params.append(recent)

        # Total comparisons
        cur.execute(f"SELECT COUNT(*) FROM ({base_query})", params)
        total = cur.fetchone()[0]

        if total == 0:
            console.print()
            console.print("[yellow]No shadow comparisons recorded yet.[/yellow]")
            console.print(
                "[dim]Enable shadow_mode in ~/.ruleshield/config.yaml and send requests"
                " that match rules.[/dim]"
            )
            console.print()
            conn.close()
            return

        # Average similarity
        cur.execute(f"SELECT AVG(similarity) FROM ({base_query})", params)
        avg_sim = float(cur.fetchone()[0] or 0)

        # Per-rule breakdown
        cur.execute(
            f"""
            SELECT
                rule_id,
                COUNT(*) AS total,
                AVG(similarity) AS avg_sim,
                SUM(CASE WHEN match_quality = 'good' THEN 1 ELSE 0 END) AS good,
                SUM(CASE WHEN match_quality = 'partial' THEN 1 ELSE 0 END) AS partial,
                SUM(CASE WHEN match_quality = 'poor' THEN 1 ELSE 0 END) AS poor
            FROM ({base_query})
            GROUP BY rule_id
            ORDER BY total DESC
            """,
            params,
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        console.print(f"[red]Failed to read shadow data: {exc}[/red]")
        return

    # --- Overview panel ---
    console.print()
    avg_style = _CACHE_CLR if avg_sim >= 0.8 else ("yellow" if avg_sim >= 0.4 else "red")
    console.print(
        Panel(
            Text("Shadow Mode Statistics", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(0, 4),
        )
    )
    console.print()
    console.print(f"  Total comparisons:  [bold]{total}[/bold]")
    console.print(f"  Average similarity: [{avg_style}]{avg_sim * 100:.1f}%[/{avg_style}]")
    console.print()

    # --- Per-rule table ---
    tbl = Table(
        title="Per-Rule Accuracy",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("Rule ID", style="white", min_width=18)
    tbl.add_column("Comparisons", justify="right", width=13, style=_RULE_CLR)
    tbl.add_column("Avg Similarity", justify="right", width=15)
    tbl.add_column("Good", justify="right", width=8, style=_CACHE_CLR)
    tbl.add_column("Partial", justify="right", width=8, style="yellow")
    tbl.add_column("Poor", justify="right", width=8, style="red")
    tbl.add_column("Status", justify="center", width=12)

    ready_rules: list[str] = []

    for row in rows:
        rule_id = row["rule_id"]
        rule_total = row["total"]
        rule_avg = float(row["avg_sim"] or 0)
        good = row["good"] or 0
        partial = row["partial"] or 0
        poor = row["poor"] or 0

        sim_pct = f"{rule_avg * 100:.1f}%"
        sim_style = _CACHE_CLR if rule_avg >= 0.8 else ("yellow" if rule_avg >= 0.4 else "red")

        if rule_avg > 0.8:
            status = Text("READY", style="bold bright_green")
            ready_rules.append(rule_id)
        elif rule_avg > 0.4:
            status = Text("TUNING", style="bold yellow")
        else:
            status = Text("LOW", style="bold red")

        tbl.add_row(
            rule_id,
            str(rule_total),
            Text(sim_pct, style=sim_style),
            str(good),
            str(partial),
            str(poor),
            status,
        )

    console.print(tbl)

    # --- Summary ---
    console.print()
    if ready_rules:
        console.print(
            f"  [{_CACHE_CLR}]{len(ready_rules)} rule(s) ready for activation "
            f"(similarity > 80%):[/{_CACHE_CLR}]"
        )
        for rid in ready_rules:
            console.print(f"    [{_CACHE_CLR}]- {rid}[/{_CACHE_CLR}]")
    else:
        console.print(
            "  [dim]No rules ready for activation yet (need similarity > 80%).[/dim]"
        )

    try:
        conn = _sqlite3.connect(str(DB_PATH))
        conn.row_factory = _sqlite3.Row
        cur = conn.cursor()
        example_query = """
            SELECT
                rule_id,
                prompt_text,
                rule_response,
                llm_response,
                similarity
            FROM shadow_log
            WHERE match_quality = 'poor'
        """
        example_params: list[Any] = []
        if rule_id:
            example_query += " AND rule_id = ?"
            example_params.append(rule_id)
        example_query += " ORDER BY similarity ASC, created_at DESC LIMIT 3"
        cur.execute(example_query, example_params)
        examples = cur.fetchall()
        conn.close()
    except Exception as exc:
        console.print(f"[red]Failed to load shadow examples: {exc}[/red]")
        console.print()
        return

    if examples:
        console.print()
        console.print("[bold]Tune Next:[/bold] Lowest-similarity shadow examples")
        for idx, row in enumerate(examples, 1):
            console.print(
                Panel(
                    "\n".join(
                        [
                            f"[bold]Rule:[/bold] {row['rule_id']}",
                            f"[bold]Similarity:[/bold] {float(row['similarity'] or 0) * 100:.1f}%",
                            f"[bold]Prompt:[/bold] {row['prompt_text'] or '-'}",
                            f"[bold]Rule:[/bold] {row['rule_response'] or '-'}",
                            f"[bold]LLM:[/bold] {row['llm_response'] or '-'}",
                        ]
                    ),
                    title=f"Example {idx}",
                    border_style="red",
                    padding=(0, 1),
                )
            )
    console.print()


@main.command("shadow-reset")
@click.option("--rule", "rule_id", default=None, help="Only clear shadow history for one rule id.")
@click.option("--yes", "-y", is_flag=True, help="Actually delete the matching shadow comparisons.")
def shadow_reset(rule_id: str | None, yes: bool) -> None:
    """Clear shadow comparison history globally or for a single rule."""
    import asyncio

    target = f"rule '{rule_id}'" if rule_id else "all rules"
    if not yes:
        console.print(f"[yellow]Dry run:[/yellow] would clear shadow history for {target}.")
        console.print("[dim]Pass --yes to actually delete those comparisons.[/dim]")
        return

    async def run() -> int:
        from ruleshield.cache import CacheManager

        cm = CacheManager(db_path=str(DB_PATH))
        await cm.init()
        try:
            return await cm.reset_shadow_log(rule_id=rule_id)
        finally:
            await cm.close()

    deleted = asyncio.run(run())
    console.print(f"[bright_green]Deleted {deleted} shadow comparison(s) for {target}.[/bright_green]")


# ---------------------------------------------------------------------------
# prompt training
# ---------------------------------------------------------------------------


@main.command("run-prompt-training")
@click.option(
    "--scenario",
    "scenario_id",
    default="vibecoder_stats_dashboard",
    show_default=True,
    help="Built-in training scenario to run.",
)
@click.option(
    "--model",
    default="gpt-5.1-codex-mini",
    show_default=True,
    help="Hermes model to use for the training run.",
)
@click.option(
    "--scenario-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a reusable YAML/JSON scenario config (overrides --scenario).",
)
@click.option(
    "--max-prompts",
    type=int,
    default=None,
    help="Override the built-in scenario prompt budget.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("test-runs") / "ruleshield-training",
    show_default=True,
    help="Directory where isolated training runs and reports are written.",
)
@click.option(
    "--proxy-url",
    default="http://127.0.0.1:8337",
    show_default=True,
    help="RuleShield proxy base URL used for traffic observation and reporting.",
)
@click.option(
    "--max-iterations",
    type=int,
    default=8,
    show_default=True,
    help="Maximum Hermes iterations per prompt to keep runtime and cost low.",
)
def run_prompt_training_cmd(
    scenario_id: str,
    model: str,
    scenario_config: Path | None,
    max_prompts: int | None,
    output_dir: Path,
    proxy_url: str,
    max_iterations: int,
) -> None:
    """Run a short Hermes-driven RuleShield training scenario."""
    from ruleshield.prompt_training import run_prompt_training

    console.print()
    console.print(
        Panel(
            Text("RuleShield Prompt Training", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(1, 4),
        )
    )
    console.print(f"  Scenario: [cyan]{scenario_id}[/cyan]")
    if scenario_config is not None:
        console.print(f"  Scenario config: [cyan]{scenario_config}[/cyan]")
    console.print(f"  Model:    [yellow]{model}[/yellow]")
    console.print(f"  Proxy:    [cyan]{proxy_url}[/cyan]")
    console.print(f"  Output:   [cyan]{output_dir}[/cyan]")
    console.print()

    try:
        result = run_prompt_training(
            scenario_id=scenario_id,
            scenario_config=str(scenario_config) if scenario_config else None,
            model=model,
            max_prompts=max_prompts,
            output_dir=output_dir,
            proxy_url=proxy_url,
            max_iterations=max_iterations,
        )
    except Exception as exc:
        console.print(f"[red]Prompt training failed:[/red] {exc}")
        console.print()
        console.print(
            "[dim]If Hermes is installed in a different environment, set "
            "[cyan]RULESHIELD_HERMES_AGENT_IMPORT[/cyan] to the correct import path "
            "(example: [cyan]run_agent:AIAgent[/cyan] or [cyan]hermes:AIAgent[/cyan]).[/dim]"
        )
        console.print()
        raise SystemExit(1) from exc

    summary_table = Table(
        title="Training Run Summary",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    summary_table.add_column("Field", style="white", width=20)
    summary_table.add_column("Value", style="cyan")
    summary_table.add_row("Run ID", result.run_id)
    summary_table.add_row("Prompts sent", str(result.prompts_sent))
    summary_table.add_row("Duration", f"{result.duration_seconds:.2f}s")
    summary_table.add_row("Isolation OK", "yes" if result.isolation_ok else "no")
    summary_table.add_row("Project dir", result.project_dir)
    summary_table.add_row("Reports dir", result.reports_dir)
    summary_table.add_row("Summary (JSON)", result.summary_json_path)
    summary_table.add_row("Summary (MD)", result.summary_md_path)

    console.print(summary_table)
    console.print()


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------


@main.command()
def rules() -> None:
    """List active cost-saving rules."""
    rules_dir = RULES_DIR

    if not rules_dir.exists():
        console.print()
        console.print("[yellow]No rules directory found.[/yellow] Run [cyan]ruleshield init[/cyan] first.")
        console.print()
        return

    json_files = list(rules_dir.glob("*.json"))
    # Also include promoted rules from the promoted/ subdirectory.
    promoted_dir = rules_dir / "promoted"
    if promoted_dir.is_dir():
        json_files.extend(promoted_dir.glob("*.json"))
    if not json_files:
        console.print()
        console.print("[yellow]No rule files found.[/yellow]")
        console.print(f"[dim]Rules directory: {rules_dir}[/dim]")
        console.print()
        return

    all_rules: list[dict[str, Any]] = []
    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                all_rules.extend(data)
            elif isinstance(data, dict):
                all_rules.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    if not all_rules:
        console.print()
        console.print("[yellow]No valid rules found in rule files.[/yellow]")
        console.print()
        return

    # Sort by priority descending
    all_rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    console.print()

    tbl = Table(
        title="RuleShield Rules",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("#", style=_DIM, justify="right", width=4)
    tbl.add_column("Rule Name", style="white", min_width=20)
    tbl.add_column("Patterns", justify="center", width=10, style=_RULE_CLR)
    tbl.add_column("Hits", justify="right", width=8, style=_CACHE_CLR)
    tbl.add_column("Confidence", justify="right", width=12)
    tbl.add_column("Status", justify="center", width=10)

    for idx, rule in enumerate(all_rules, 1):
        name = rule.get("name", rule.get("id", "unnamed"))
        pattern_count = len(rule.get("patterns", []))
        hit_count = rule.get("hit_count", 0)
        confidence = rule.get("confidence", 1.0)
        enabled = rule.get("enabled", True)

        conf_pct = f"{confidence * 100:.0f}%"
        conf_style = _CACHE_CLR if confidence >= 0.9 else ("yellow" if confidence >= 0.7 else "red")
        status_text = Text("enabled", style="bold bright_green") if enabled else Text("disabled", style="red")

        tbl.add_row(
            str(idx),
            name,
            str(pattern_count),
            str(hit_count),
            Text(conf_pct, style=conf_style),
            status_text,
        )

    console.print(tbl)

    # Summary line
    total = len(all_rules)
    active = sum(1 for r in all_rules if r.get("enabled", True))
    total_hits = sum(r.get("hit_count", 0) for r in all_rules)
    console.print()
    console.print(
        f"  [dim]{active}/{total} rules active[/dim]  |  "
        f"[dim]{total_hits} total hits[/dim]  |  "
        f"[dim]Rules dir: [cyan]{rules_dir}[/cyan][/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------


@main.command()
def feedback() -> None:
    """Show per-rule feedback stats (accepts, rejects, confidence).

    \b
    Feedback is recorded automatically during proxy operation.
    Rules with low confidence are flagged for review or auto-deactivated.

    \b
    RL integration: Use ruleshield.feedback.HermesRLInterface for Hermes
    GRPO/Atropos training environments and DSPy/GEPA evolution configs.
    """
    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy and send some requests first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    import sqlite3 as _sqlite3

    try:
        conn = _sqlite3.connect(str(DB_PATH))
        conn.row_factory = _sqlite3.Row
        cur = conn.cursor()

        # Check if the feedback table exists
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rule_feedback'"
        )
        if cur.fetchone() is None:
            console.print()
            console.print("[yellow]No feedback data yet.[/yellow] The feedback table has not been created.")
            console.print("[dim]Feedback is recorded automatically when the proxy runs with rules enabled.[/dim]")
            console.print()
            conn.close()
            return

        cur.execute(
            """
            SELECT
                rule_id,
                SUM(CASE WHEN feedback = 'accept' THEN 1 ELSE 0 END) AS accepts,
                SUM(CASE WHEN feedback IN ('reject', 'correct') THEN 1 ELSE 0 END) AS rejects,
                COUNT(*) AS total
            FROM rule_feedback
            GROUP BY rule_id
            ORDER BY total DESC
            """
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as exc:
        console.print(f"[red]Failed to read feedback data: {exc}[/red]")
        return

    if not rows:
        console.print()
        console.print("[yellow]No feedback recorded yet.[/yellow]")
        console.print("[dim]Feedback accumulates as rules handle requests during proxy operation.[/dim]")
        console.print()
        return

    # Also load current rule confidences from JSON for cross-reference
    rule_confidences: dict[str, float] = {}
    if RULES_DIR.exists():
        for fp in RULES_DIR.glob("*.json"):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                rule_list = data if isinstance(data, list) else [data]
                for r in rule_list:
                    rid = r.get("id")
                    if rid:
                        rule_confidences[rid] = r.get("confidence", 1.0)
            except (json.JSONDecodeError, OSError):
                continue

    # Merge runtime state if available
    state_path = RULES_DIR / "_state.json"
    if state_path.is_file():
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                for entry in json.load(fh):
                    rid = entry.get("id")
                    if rid:
                        rule_confidences[rid] = entry.get("confidence", rule_confidences.get(rid, 1.0))
        except (json.JSONDecodeError, OSError):
            pass

    console.print()

    tbl = Table(
        title="Rule Feedback Stats",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("Rule ID", style="white", min_width=18)
    tbl.add_column("Accepts", justify="right", width=10, style=_CACHE_CLR)
    tbl.add_column("Rejects", justify="right", width=10, style="red")
    tbl.add_column("Total", justify="right", width=8, style=_DIM)
    tbl.add_column("Accept Rate", justify="right", width=13)
    tbl.add_column("Confidence", justify="right", width=12)

    for row in rows:
        rule_id = row["rule_id"]
        accepts = row["accepts"]
        rejects = row["rejects"]
        total = row["total"]
        rate = accepts / total if total > 0 else 0.0
        confidence = rule_confidences.get(rule_id)

        rate_pct = f"{rate * 100:.1f}%"
        rate_style = _CACHE_CLR if rate >= 0.9 else ("yellow" if rate >= 0.7 else "red")

        if confidence is not None:
            conf_pct = f"{confidence * 100:.1f}%"
            conf_style = _CACHE_CLR if confidence >= 0.9 else ("yellow" if confidence >= 0.5 else "red")
            conf_text = Text(conf_pct, style=conf_style)
        else:
            conf_text = Text("--", style=_DIM)

        tbl.add_row(
            rule_id,
            str(accepts),
            str(rejects),
            str(total),
            Text(rate_pct, style=rate_style),
            conf_text,
        )

    console.print(tbl)

    total_feedback = sum(row["total"] for row in rows)
    total_accepts = sum(row["accepts"] for row in rows)
    overall_rate = total_accepts / total_feedback if total_feedback > 0 else 0.0
    console.print()
    console.print(
        f"  [dim]{total_feedback} total feedback entries[/dim]  |  "
        f"[dim]Overall accept rate: {overall_rate * 100:.1f}%[/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# analyze-crons
# ---------------------------------------------------------------------------


@main.command("analyze-crons")
@click.option(
    "--min-occurrences",
    type=int,
    default=3,
    show_default=True,
    help="Minimum prompt occurrences to include in analysis.",
)
@click.option(
    "--structured",
    is_flag=True,
    help="Classify recurring prompts into static recurring prompts vs dynamic workflows.",
)
def analyze_crons(min_occurrences: int, structured: bool) -> None:
    """Identify recurring prompts that could be replaced by direct API calls.

    \b
    Scans the request log for prompts that appear repeatedly and evaluates
    whether they are already cached/rule-matched or should be optimized.
    Prompts with high cache rates are candidates for direct API replacement.
    """
    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy and send some requests first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    from ruleshield.cron_optimizer import analyze_recurring_workflows

    result = analyze_recurring_workflows(
        DB_PATH,
        min_occurrences=min_occurrences,
        structured=structured,
    )
    rows = result.get("candidates", [])
    if result.get("error"):
        console.print(f"[red]Failed to query request log: {result['error']}[/red]")
        return

    if not rows:
        console.print()
        console.print(f"[yellow]{result.get('message', 'No recurring prompts found.')}[/yellow]")
        console.print()
        return

    if structured:
        console.print()
        tbl = Table(
            title="Structured Cron Analysis",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        tbl.add_column("Prompt", style="white", min_width=20, max_width=40)
        tbl.add_column("Occur", justify="right", width=7, style=_RULE_CLR)
        tbl.add_column("Cache", justify="right", width=8)
        tbl.add_column("Class", width=18)
        tbl.add_column("Stages", justify="right", width=8)
        tbl.add_column("Recommendation", style="white", min_width=18, max_width=34)

        for row in rows:
            cls = row["classification"]
            cls_style = _CACHE_CLR if cls == "static_recurring" else ("yellow" if cls == "dynamic_workflow" else _DIM)
            tbl.add_row(
                row["prompt_preview"][:40],
                str(row["occurrences"]),
                f"{row['cache_rate_pct']:.0f}%",
                Text(cls, style=cls_style),
                str(row["stage_count"]),
                row["recommendation"],
            )

        console.print(tbl)
        console.print()
        summary = result.get("summary", {})
        console.print(
            f"  [bold]Summary:[/bold] "
            f"{summary.get('dynamic_workflow', 0)} dynamic workflow, "
            f"{summary.get('static_recurring', 0)} static recurring, "
            f"{summary.get('monitor', 0)} monitor"
        )
        console.print()
        return

    console.print()

    tbl = Table(
        title="Recurring Prompt Analysis",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("Prompt", style="white", min_width=20, max_width=45)
    tbl.add_column("Occurrences", justify="right", width=12, style=_RULE_CLR)
    tbl.add_column("Cache Rate", justify="right", width=12)
    tbl.add_column("Total Cost", justify="right", width=12, style=_LLM_CLR)
    tbl.add_column("Recommendation", justify="center", width=14)

    replace_count = 0

    for row in rows:
        prompt_text = (row["prompt_text"] or "")[:45]
        if len(row["prompt_text"] or "") > 45:
            prompt_text += "..."

        cache_rate = row["cache_rate_pct"]
        recommendation_label = row["recommendation_label"]

        if recommendation_label == "REPLACE":
            rec_text = Text("REPLACE", style="bold bright_green")
            replace_count += 1
        elif recommendation_label == "OPTIMIZE":
            rec_text = Text("OPTIMIZE", style="bold yellow")
        else:
            rec_text = Text("MONITOR", style="dim")

        rate_str = f"{cache_rate:.0f}%"
        rate_style = _CACHE_CLR if cache_rate > 80 else ("yellow" if cache_rate > 50 else _DIM)

        tbl.add_row(
            prompt_text,
            str(row["occurrences"]),
            Text(rate_str, style=rate_style),
            f"${row['total_cost_usd']:.4f}",
            rec_text,
        )

    console.print(tbl)

    console.print()
    console.print(
        f"  [{_CACHE_CLR}]{replace_count} prompt(s) could be replaced by direct API calls[/{_CACHE_CLR}]"
    )
    console.print()


# ---------------------------------------------------------------------------
# cron-profiles
# ---------------------------------------------------------------------------


@main.command("suggest-cron-profile")
@click.argument("prompt_hash_or_text")
@click.option(
    "--min-occurrences",
    type=int,
    default=3,
    show_default=True,
    help="Minimum number of occurrences required for the source prompt.",
)
def suggest_cron_profile_cmd(prompt_hash_or_text: str, min_occurrences: int) -> None:
    """Create a draft cron optimization profile from a recurring prompt."""
    from ruleshield.cron_optimizer import suggest_cron_profile

    result = suggest_cron_profile(
        DB_PATH,
        prompt_hash_or_text,
        min_occurrences=min_occurrences,
    )
    if result.get("error"):
        console.print(f"[red]Failed to suggest cron profile: {result['error']}[/red]")
        return

    matches = result.get("matches", [])
    if matches:
        console.print()
        tbl = Table(
            title="Multiple Cron Profile Matches",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        tbl.add_column("Prompt", style="white", min_width=20, max_width=42)
        tbl.add_column("Occur", justify="right", width=7, style=_RULE_CLR)
        tbl.add_column("Class", width=18)
        tbl.add_column("Hash", style=_DIM, min_width=12, max_width=16)
        for match in matches:
            tbl.add_row(
                match["prompt_preview"][:42],
                str(match["occurrences"]),
                match["classification"],
                f"{match['prompt_hash'][:12]}...",
            )
        console.print(tbl)
        console.print()
        console.print("[dim]Use a longer hash prefix or a more specific text fragment.[/dim]")
        console.print()
        return

    profile = result.get("profile")
    if not profile:
        console.print()
        console.print(f"[yellow]{result.get('message', 'No recurring prompt match found.')}[/yellow]")
        console.print()
        return

    estimates = profile["estimates"]
    detection = profile["detection"]
    console.print()
    console.print(
        Panel(
            Text("Draft Cron Profile Created", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(0, 4),
        )
    )
    console.print()
    console.print(f"  [bold]Profile ID:[/bold]    [{_RULE_CLR}]{profile['id']}[/{_RULE_CLR}]")
    console.print(f"  [bold]Name:[/bold]          {profile['name']}")
    console.print(f"  [bold]Class:[/bold]         {detection['classification']}")
    console.print(f"  [bold]Occurrences:[/bold]   [{_CACHE_CLR}]{detection['occurrences']}[/{_CACHE_CLR}]")
    console.print(f"  [bold]Saved:[/bold]         [cyan]{result['saved_path']}[/cyan]")
    console.print(f"  [bold]Compact Prompt:[/bold] [dim]{profile['optimized_execution']['prompt_template']}[/dim]")
    console.print()
    console.print(
        f"  [bold]Estimated Savings:[/bold] "
        f"[{_CACHE_CLR}]{estimates['token_reduction_pct']:.1f}% tokens[/{_CACHE_CLR}], "
        f"[{_LLM_CLR}]{estimates['cost_reduction_pct']:.1f}% cost[/{_LLM_CLR}], "
        f"[yellow]{estimates['tool_reduction_pct']:.1f}% tools[/yellow]"
    )
    console.print()


@main.command("list-cron-profiles")
def list_cron_profiles_cmd() -> None:
    """List stored cron optimization profiles."""
    from ruleshield.cron_optimizer import list_cron_profiles

    result = list_cron_profiles()
    profiles = result.get("profiles", [])
    if not profiles:
        console.print()
        console.print("[yellow]No cron profiles found.[/yellow]")
        console.print()
        return

    console.print()
    tbl = Table(
        title="Cron Optimization Profiles",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("ID", style=_RULE_CLR, min_width=18, max_width=26)
    tbl.add_column("Status", width=10)
    tbl.add_column("Runtime", width=10)
    tbl.add_column("Class", width=18)
    tbl.add_column("Occur", justify="right", width=7, style=_CACHE_CLR)
    tbl.add_column("Token Save", justify="right", width=11, style=_LLM_CLR)
    tbl.add_column("Confidence", justify="right", width=11, style="yellow")
    for profile in profiles:
        tbl.add_row(
            profile["id"],
            profile["status"],
            profile["runtime_status"],
            profile["classification"],
            str(profile["occurrences"]),
            f"{profile['token_reduction_pct']:.1f}%",
            f"{profile['optimization_confidence'] * 100:.1f}%",
        )
    console.print(tbl)
    console.print()


@main.command("show-cron-profile")
@click.argument("profile_id")
def show_cron_profile_cmd(profile_id: str) -> None:
    """Show a stored cron optimization profile."""
    from ruleshield.cron_optimizer import load_cron_profile

    result = load_cron_profile(profile_id)
    profile = result.get("profile")
    if not profile:
        console.print()
        console.print(f"[yellow]{result.get('message', 'Cron profile not found.')}[/yellow]")
        console.print()
        return

    console.print()
    console.print(
        Panel(
            Text(profile["name"], justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(0, 4),
        )
    )
    console.print()
    console.print(f"  [bold]ID:[/bold]            [{_RULE_CLR}]{profile['id']}[/{_RULE_CLR}]")
    console.print(f"  [bold]Status:[/bold]        {profile['status']}")
    console.print(f"  [bold]Runtime:[/bold]       {profile.get('runtime_status', 'draft')}")
    console.print(f"  [bold]File:[/bold]          [cyan]{result['path']}[/cyan]")
    console.print(f"  [bold]Source:[/bold]        [dim]{profile['source']['prompt_text']}[/dim]")
    console.print(f"  [bold]Compact Prompt:[/bold] [dim]{profile['optimized_execution']['prompt_template']}[/dim]")
    console.print()
    console.print(json.dumps(profile, indent=2, ensure_ascii=False))
    console.print()


@main.command("run-cron-shadow")
@click.argument("profile_id")
@click.option(
    "--optimized-response",
    type=str,
    help="Optimized output text to validate against recent original runs.",
)
@click.option(
    "--optimized-response-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read optimized output text from a file.",
)
@click.option(
    "--sample-limit",
    type=int,
    default=3,
    show_default=True,
    help="Number of recent original runs to compare against.",
)
@click.option(
    "--payload",
    type=str,
    help="Dynamic payload text for automatic compact execution.",
)
@click.option(
    "--payload-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read dynamic payload text from a file for automatic compact execution.",
)
@click.option(
    "--model",
    type=str,
    help="Override the compact execution model.",
)
def run_cron_shadow_cmd(
    profile_id: str,
    optimized_response: str | None,
    optimized_response_file: Path | None,
    sample_limit: int,
    payload: str | None,
    payload_file: Path | None,
    model: str | None,
) -> None:
    """Run shadow validation for a cron optimization profile."""
    from ruleshield.cron_validation import run_cron_shadow

    response_text = optimized_response or ""
    if optimized_response_file is not None:
        response_text = optimized_response_file.read_text(encoding="utf-8")

    payload_text = payload or ""
    if payload_file is not None:
        payload_text = payload_file.read_text(encoding="utf-8")

    if not response_text.strip() and not payload_text.strip():
        console.print()
        console.print("[yellow]Provide optimized output or payload for auto-run.[/yellow]")
        console.print()
        return

    result = run_cron_shadow(
        DB_PATH,
        profile_id,
        response_text,
        sample_limit=sample_limit,
        payload_text=payload_text,
        model=model,
    )
    if result.get("count", 0) == 0:
        console.print()
        console.print(f"[yellow]{result.get('message', 'No validation runs stored.')}[/yellow]")
        console.print()
        return

    summary = result["summary"]
    console.print()
    tbl = Table(
        title="Cron Shadow Validation",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("Runs", justify="right", width=7, style=_RULE_CLR)
    tbl.add_column("Similarity", justify="right", width=11, style=_CACHE_CLR)
    tbl.add_column("Structure", justify="right", width=10, style="yellow")
    tbl.add_column("Confidence", justify="right", width=11, style=_LLM_CLR)
    tbl.add_column("Accept", justify="right", width=8)
    tbl.add_row(
        str(summary["total_runs"]),
        f"{summary['avg_similarity'] * 100:.1f}%",
        f"{summary['avg_structure_score'] * 100:.1f}%",
        f"{summary['avg_optimization_confidence'] * 100:.1f}%",
        f"{summary['acceptance_rate'] * 100:.1f}%",
    )
    console.print(tbl)
    console.print()
    if result.get("execution"):
        console.print(f"  [bold]Auto-run model:[/bold] [dim]{result['execution'].get('model', '')}[/dim]")
        console.print()


@main.command("activate-cron-profile")
@click.argument("profile_id")
@click.option("--yes", "-y", is_flag=True, help="Force activation even if guardrails are not met.")
def activate_cron_profile_cmd(profile_id: str, yes: bool) -> None:
    """Activate a validated cron optimization profile."""
    from ruleshield.cron_optimizer import activate_cron_profile

    result = activate_cron_profile(
        profile_id,
        db_path=DB_PATH,
        force=yes,
    )
    profile = result.get("profile")
    if not profile:
        console.print()
        console.print(f"[yellow]{result.get('message', 'Activation failed.')}[/yellow]")
        if result.get("summary"):
            summary = result["summary"]
            console.print(
                f"[dim]Runs: {summary.get('total_runs', 0)}, "
                f"Confidence: {summary.get('avg_optimization_confidence', 0.0) * 100:.1f}%[/dim]"
            )
        console.print()
        return

    console.print()
    console.print(
        Panel(
            Text("Cron Profile Activated", justify="center", style="bold bright_green"),
            border_style="bright_green",
            padding=(0, 4),
        )
    )
    console.print()
    console.print(f"  [bold]Profile ID:[/bold]    [{_RULE_CLR}]{profile['id']}[/{_RULE_CLR}]")
    console.print(f"  [bold]Status:[/bold]        {profile['status']}")
    console.print(f"  [bold]Runtime:[/bold]       {profile.get('runtime_status', 'ready')}")
    console.print(f"  [bold]Saved:[/bold]         [cyan]{result['path']}[/cyan]")
    console.print()


@main.command("run-active-cron-profile")
@click.argument("profile_id")
@click.option("--payload", type=str, help="Dynamic payload text for the active profile.")
@click.option(
    "--payload-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read dynamic payload text from a file.",
)
@click.option("--model", type=str, help="Override the execution model.")
def run_active_cron_profile_cmd(
    profile_id: str,
    payload: str | None,
    payload_file: Path | None,
    model: str | None,
) -> None:
    """Execute an active cron profile with a payload."""
    from ruleshield.cron_optimizer import execute_active_cron_profile

    payload_text = payload or ""
    if payload_file is not None:
        payload_text = payload_file.read_text(encoding="utf-8")

    if not payload_text.strip():
        console.print()
        console.print("[yellow]Provide --payload or --payload-file.[/yellow]")
        console.print()
        return

    result = execute_active_cron_profile(
        profile_id,
        payload_text,
        model=model,
    )
    execution = result.get("execution")
    if not execution:
        console.print()
        console.print(f"[yellow]{result.get('message', 'Execution failed.')}[/yellow]")
        console.print()
        return

    console.print()
    console.print(
        Panel(
            Text("Cron Profile Executed", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(0, 4),
        )
    )
    console.print()
    console.print(f"  [bold]Profile ID:[/bold]    [{_RULE_CLR}]{profile_id}[/{_RULE_CLR}]")
    console.print(f"  [bold]Model:[/bold]         {execution.get('model', '')}")
    console.print(f"  [bold]Response:[/bold]      [dim]{(execution.get('response_text', '') or '')[:400]}[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# promote-rule
# ---------------------------------------------------------------------------


@main.command("promote-rule")
@click.argument("prompt_hash_or_text")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def promote_rule(prompt_hash_or_text: str, yes: bool) -> None:
    """Promote a recurring prompt to a permanent rule with a direct API endpoint.

    \b
    PROMPT_HASH_OR_TEXT can be:
      - A prompt hash prefix (at least 6 characters)
      - A substring of the original prompt text

    \b
    Searches the request log, displays the candidate, and (with confirmation)
    creates a JSON rule in ~/.ruleshield/rules/promoted/.  The promoted rule
    gets priority 15 and confidence 0.99, and is immediately available via
    GET /api/rules/{rule_id}/response for direct API access.
    """
    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy and send some requests first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    # --- Search for matching prompt(s) in request_log ---
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        search_term = prompt_hash_or_text.strip()

        # Try hash prefix match first, then text substring
        cur.execute(
            """
            SELECT prompt_hash, prompt_text, COUNT(*) as cnt,
                   SUM(CASE WHEN resolution_type IN ('cache','rule') THEN 1 ELSE 0 END) as cached,
                   SUM(cost_usd) as total_cost
            FROM request_log
            WHERE prompt_text != '' AND prompt_text IS NOT NULL
              AND (prompt_hash LIKE ? OR prompt_text LIKE ?)
            GROUP BY prompt_hash
            ORDER BY cnt DESC
            LIMIT 10
            """,
            (f"{search_term}%", f"%{search_term}%"),
        )
        candidates = cur.fetchall()

        if not candidates:
            console.print()
            console.print(f"[yellow]No matching prompts found for:[/yellow] {search_term}")
            console.print("[dim]Try a different hash prefix or text substring.[/dim]")
            console.print()
            conn.close()
            return

        if len(candidates) > 1:
            # Show all matches so the user can narrow down
            console.print()
            console.print(
                Panel(
                    Text("Multiple Matches Found", justify="center", style=f"bold {_BRAND}"),
                    border_style=_BRAND,
                    padding=(0, 4),
                )
            )
            console.print()

            tbl = Table(border_style="grey37", padding=(0, 2))
            tbl.add_column("#", style=_DIM, justify="right", width=4)
            tbl.add_column("Hash Prefix", style=_RULE_CLR, width=12)
            tbl.add_column("Prompt", style="white", min_width=20, max_width=45)
            tbl.add_column("Count", justify="right", width=8, style=_CACHE_CLR)
            tbl.add_column("Cache Rate", justify="right", width=12)

            for idx, c in enumerate(candidates, 1):
                prompt_preview = (c["prompt_text"] or "")[:45]
                if len(c["prompt_text"] or "") > 45:
                    prompt_preview += "..."
                cnt = c["cnt"]
                cached = c["cached"] or 0
                cache_rate = (cached / cnt * 100) if cnt > 0 else 0.0
                rate_str = f"{cache_rate:.0f}%"
                rate_style = _CACHE_CLR if cache_rate > 80 else ("yellow" if cache_rate > 50 else _DIM)

                tbl.add_row(
                    str(idx),
                    c["prompt_hash"][:12],
                    prompt_preview,
                    str(cnt),
                    Text(rate_str, style=rate_style),
                )

            console.print(tbl)
            console.print()
            console.print("[dim]Narrow your search or use a longer hash prefix.[/dim]")
            console.print()
            conn.close()
            return

        # --- Single match: show details ---
        match = candidates[0]
        prompt_hash = match["prompt_hash"]
        prompt_text = match["prompt_text"] or ""
        occurrence_count = match["cnt"]
        cached_count = match["cached"] or 0
        total_cost = match["total_cost"] or 0.0
        cache_rate = (cached_count / occurrence_count * 100) if occurrence_count > 0 else 0.0

        # Fetch the most recent response for this prompt
        cur.execute(
            """
            SELECT response FROM request_log
            WHERE prompt_hash = ? AND response IS NOT NULL AND response != ''
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (prompt_hash,),
        )
        response_row = cur.fetchone()
        conn.close()

        last_response = (response_row["response"] if response_row else "") or ""

        # Display candidate summary
        console.print()
        console.print(
            Panel(
                Text("Promote to Permanent Rule", justify="center", style=f"bold {_BRAND}"),
                border_style=_BRAND,
                padding=(0, 4),
            )
        )
        console.print()

        console.print(f"  [bold]Prompt:[/bold]       {prompt_text[:80]}{'...' if len(prompt_text) > 80 else ''}")
        console.print(f"  [bold]Hash:[/bold]         [{_RULE_CLR}]{prompt_hash[:16]}...[/{_RULE_CLR}]")
        console.print(f"  [bold]Occurrences:[/bold]  [{_CACHE_CLR}]{occurrence_count}[/{_CACHE_CLR}]")

        rate_style = _CACHE_CLR if cache_rate > 80 else ("yellow" if cache_rate > 50 else "red")
        console.print(f"  [bold]Cache Rate:[/bold]   [{rate_style}]{cache_rate:.1f}%[/{rate_style}]")
        console.print(f"  [bold]Total Cost:[/bold]   [{_LLM_CLR}]${total_cost:.4f}[/{_LLM_CLR}]")

        if last_response:
            response_preview = last_response[:120]
            if len(last_response) > 120:
                response_preview += "..."
            console.print(f"  [bold]Response:[/bold]     [dim]{response_preview}[/dim]")

        console.print()

        # --- Confirm ---
        if not yes:
            confirmed = click.confirm("  Create a permanent rule for this prompt?", default=False)
            if not confirmed:
                console.print()
                console.print("  [dim]Aborted.[/dim]")
                console.print()
                return

        # --- Create the promoted rule ---
        promoted_dir = RULES_DIR / "promoted"
        promoted_dir.mkdir(parents=True, exist_ok=True)

        # Generate a short rule ID from the hash
        rule_id = f"promoted_{prompt_hash[:12]}"

        rule = {
            "id": rule_id,
            "name": f"Promoted: {prompt_text[:50]}{'...' if len(prompt_text) > 50 else ''}",
            "description": (
                f"Auto-promoted from recurring prompt analysis. "
                f"{occurrence_count} occurrences, {cache_rate:.0f}% cache rate."
            ),
            "patterns": [
                {"type": "exact", "value": prompt_text, "field": "last_user_message"}
            ],
            "conditions": [],
            "response": {
                "content": last_response,
                "model": "ruleshield-promoted",
            },
            "confidence": 0.99,
            "priority": 15,
            "enabled": True,
            "hit_count": 0,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "source_hash": prompt_hash,
        }

        rule_path = promoted_dir / f"{rule_id}.json"
        with open(rule_path, "w", encoding="utf-8") as fh:
            json.dump(rule, fh, indent=2, ensure_ascii=False)

        # --- Success output ---
        console.print()
        console.print(
            Panel(
                Text("Rule Created", justify="center", style="bold bright_green"),
                border_style="bright_green",
                padding=(0, 4),
            )
        )
        console.print()
        console.print(f"  [bold]Rule ID:[/bold]      [{_RULE_CLR}]{rule_id}[/{_RULE_CLR}]")
        console.print(f"  [bold]File:[/bold]         [cyan]{rule_path}[/cyan]")
        console.print(f"  [bold]Priority:[/bold]     15 (higher than default rules)")
        console.print(f"  [bold]Confidence:[/bold]   99%")
        console.print()
        console.print(f"  [bold]Direct API:[/bold]   [cyan]GET /api/rules/{rule_id}/response[/cyan]")
        console.print()
        console.print(
            f"  [dim]This rule will be loaded automatically on next proxy start.[/dim]"
        )
        console.print()

    except Exception as exc:
        console.print(f"[red]Failed to promote rule: {exc}[/red]")
        return


# ---------------------------------------------------------------------------
# discover-templates
# ---------------------------------------------------------------------------


@main.command("discover-templates")
@click.option(
    "--min-cluster",
    type=int,
    default=3,
    show_default=True,
    help="Minimum prompts in a cluster to form a template.",
)
@click.option(
    "--similarity",
    type=float,
    default=0.6,
    show_default=True,
    help="Similarity threshold for clustering (0.0-1.0).",
)
def discover_templates(min_cluster: int, similarity: float) -> None:
    """Discover prompt templates from recurring similar prompts.

    \b
    Scans the request log for groups of structurally similar prompts
    (e.g. "Translate 'X' to German") and extracts parameterized templates.
    Known variable->response pairs are cached for instant responses.
    """
    from ruleshield.template_optimizer import TemplateOptimizer

    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy and send some requests first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    optimizer = TemplateOptimizer(
        db_path=str(DB_PATH),
        templates_path=str(RULESHIELD_DIR / "templates.json"),
    )
    optimizer.load_templates()

    console.print()
    console.print(
        Panel(
            Text("Template Discovery", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(0, 4),
        )
    )
    console.print()
    console.print(f"  Scanning request log (min cluster: {min_cluster}, similarity: {similarity:.0%})...")
    console.print()

    new_templates = optimizer.discover_templates(
        min_cluster_size=min_cluster,
        similarity_threshold=similarity,
    )

    if new_templates:
        tbl = Table(
            title="Newly Discovered Templates",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        tbl.add_column("#", style=_DIM, justify="right", width=4)
        tbl.add_column("Template", style="white", min_width=30, max_width=55)
        tbl.add_column("Variables", justify="center", width=12, style=_RULE_CLR)
        tbl.add_column("Examples", justify="right", width=10, style=_CACHE_CLR)
        tbl.add_column("ID", style=_DIM, width=18)

        for idx, tpl in enumerate(new_templates, 1):
            tbl.add_row(
                str(idx),
                tpl.template[:55] + ("..." if len(tpl.template) > 55 else ""),
                ", ".join(tpl.variables),
                str(tpl.hit_count),
                tpl.id,
            )

        console.print(tbl)
        console.print()
        console.print(
            f"  [{_CACHE_CLR}]{len(new_templates)} new template(s) discovered and saved.[/{_CACHE_CLR}]"
        )
    else:
        console.print(f"  [dim]No new templates discovered.[/dim]")

    # Show all existing templates
    if optimizer.templates:
        console.print()
        tbl2 = Table(
            title="All Templates",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        tbl2.add_column("#", style=_DIM, justify="right", width=4)
        tbl2.add_column("Template", style="white", min_width=30, max_width=55)
        tbl2.add_column("Variables", justify="center", width=12, style=_RULE_CLR)
        tbl2.add_column("Cached", justify="right", width=10, style=_CACHE_CLR)
        tbl2.add_column("ID", style=_DIM, width=18)

        for idx, tpl in enumerate(optimizer.templates, 1):
            tbl2.add_row(
                str(idx),
                tpl.template[:55] + ("..." if len(tpl.template) > 55 else ""),
                ", ".join(tpl.variables),
                str(tpl.hit_count),
                tpl.id,
            )

        console.print(tbl2)

        stats = optimizer.get_stats()
        console.print()
        console.print(
            f"  [dim]{stats['total_templates']} template(s)[/dim]  |  "
            f"[dim]{stats['total_cached_examples']} cached example(s)[/dim]  |  "
            f"[dim]Saved to: [cyan]{RULESHIELD_DIR / 'templates.json'}[/cyan][/dim]"
        )

    console.print()


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------


@main.command("templates")
def templates() -> None:
    """List current prompt templates and their cached variable mappings.

    \b
    Templates are extracted by 'discover-templates' from recurring similar
    prompts. When a new prompt matches a template and its variables are
    already cached, the response is returned instantly without an LLM call.
    """
    from ruleshield.template_optimizer import TemplateOptimizer

    templates_path = RULESHIELD_DIR / "templates.json"

    if not templates_path.exists():
        console.print()
        console.print("[yellow]No templates found.[/yellow]")
        console.print("  Run [cyan]ruleshield discover-templates[/cyan] to analyze your request log.")
        console.print()
        return

    optimizer = TemplateOptimizer(
        db_path=str(DB_PATH),
        templates_path=str(templates_path),
    )
    optimizer.load_templates()

    if not optimizer.templates:
        console.print()
        console.print("[yellow]No templates found.[/yellow]")
        console.print("  Run [cyan]ruleshield discover-templates[/cyan] to analyze your request log.")
        console.print()
        return

    console.print()
    console.print(
        Panel(
            Text("Prompt Templates", justify="center", style=f"bold {_BRAND}"),
            border_style=_BRAND,
            padding=(0, 4),
        )
    )
    console.print()

    tbl = Table(
        title="Templates",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("#", style=_DIM, justify="right", width=4)
    tbl.add_column("Template", style="white", min_width=30, max_width=55)
    tbl.add_column("Variables", justify="center", width=14, style=_RULE_CLR)
    tbl.add_column("Cached", justify="right", width=10, style=_CACHE_CLR)
    tbl.add_column("ID", style=_DIM, width=18)

    for idx, tpl in enumerate(optimizer.templates, 1):
        tbl.add_row(
            str(idx),
            tpl.template[:55] + ("..." if len(tpl.template) > 55 else ""),
            ", ".join(tpl.variables),
            str(tpl.hit_count),
            tpl.id,
        )

    console.print(tbl)

    stats = optimizer.get_stats()
    console.print()
    console.print(
        f"  [dim]{stats['total_templates']} template(s)[/dim]  |  "
        f"[dim]{stats['total_cached_examples']} cached example(s)[/dim]  |  "
        f"[dim]File: [cyan]{templates_path}[/cyan][/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# test-slack
# ---------------------------------------------------------------------------


@main.command("test-slack")
def test_slack() -> None:
    """Send a test notification to verify Slack webhook configuration."""
    import asyncio

    from ruleshield.config import load_settings
    from ruleshield.integrations.slack import SlackNotifier

    settings = load_settings()

    if not settings.slack_webhook:
        console.print()
        console.print("[yellow]No Slack webhook configured.[/yellow]")
        console.print()
        console.print("  Set via environment variable:")
        console.print("    [cyan]export RULESHIELD_SLACK_WEBHOOK=https://hooks.slack.com/services/...[/cyan]")
        console.print()
        console.print("  Or in [cyan]~/.ruleshield/config.yaml[/cyan]:")
        console.print("    [cyan]slack_webhook: https://hooks.slack.com/services/...[/cyan]")
        console.print()
        return

    notifier = SlackNotifier(webhook_url=settings.slack_webhook)

    console.print()
    console.print("  Sending test notification...", end=" ")

    success = asyncio.run(notifier.send_test())

    if success:
        console.print("[bright_green]sent![/bright_green]")
        console.print()
        console.print("  [dim]Check your Slack channel for the test message.[/dim]")
    else:
        console.print("[red]failed![/red]")
        console.print()
        console.print("  [dim]Check that your webhook URL is correct and the channel exists.[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# wrapped
# ---------------------------------------------------------------------------


def _query_wrapped_stats(days: int) -> dict[str, Any]:
    """Query aggregated stats from request_log for the given period."""
    stats: dict[str, Any] = {
        "days": days,
        "period_start": "",
        "period_end": "",
        "total_requests": 0,
        "breakdown": {
            "cache": 0,
            "rule": 0,
            "routed": 0,
            "template": 0,
            "passthrough": 0,
            "llm": 0,
        },
        "cost_without": 0.0,
        "cost_with": 0.0,
        "saved_usd": 0.0,
        "saved_pct": 0.0,
        "top_rules": [],
        "expensive_prompts": [],
    }

    if not DB_PATH.exists():
        return stats

    try:
        from datetime import timedelta

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        stats["period_start"] = cutoff.strftime("%Y-%m-%d")
        stats["period_end"] = now.strftime("%Y-%m-%d")

        # Total requests in period
        cur.execute(
            "SELECT COUNT(*) FROM request_log WHERE created_at >= ?", (cutoff_str,)
        )
        stats["total_requests"] = cur.fetchone()[0]

        # Breakdown by resolution type
        cur.execute(
            """
            SELECT resolution_type, COUNT(*) as cnt
            FROM request_log WHERE created_at >= ?
            GROUP BY resolution_type
            """,
            (cutoff_str,),
        )
        for row in cur.fetchall():
            rtype = (row["resolution_type"] or "llm").lower()
            if rtype in stats["breakdown"]:
                stats["breakdown"][rtype] = row["cnt"]

        # Cost calculations
        cur.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM request_log WHERE created_at >= ?",
            (cutoff_str,),
        )
        stats["cost_without"] = round(float(cur.fetchone()[0]), 4)

        cur.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM request_log "
            "WHERE created_at >= ? AND resolution_type = 'llm'",
            (cutoff_str,),
        )
        stats["cost_with"] = round(float(cur.fetchone()[0]), 4)

        stats["saved_usd"] = round(stats["cost_without"] - stats["cost_with"], 4)
        if stats["cost_without"] > 0:
            stats["saved_pct"] = round(
                (stats["saved_usd"] / stats["cost_without"]) * 100, 1
            )

        # Top 5 rules by hit count (from request_log, not rule files)
        cur.execute(
            """
            SELECT prompt_hash, prompt_text, COUNT(*) as hits
            FROM request_log
            WHERE created_at >= ? AND resolution_type = 'rule'
            GROUP BY prompt_hash
            ORDER BY hits DESC
            LIMIT 5
            """,
            (cutoff_str,),
        )
        stats["top_rules"] = [
            {
                "hash": row["prompt_hash"][:12],
                "prompt": (row["prompt_text"] or "")[:60],
                "hits": row["hits"],
            }
            for row in cur.fetchall()
        ]

        # Top 3 most expensive prompts
        cur.execute(
            """
            SELECT prompt_text, cost_usd, model, resolution_type
            FROM request_log
            WHERE created_at >= ? AND cost_usd > 0
            ORDER BY cost_usd DESC
            LIMIT 3
            """,
            (cutoff_str,),
        )
        stats["expensive_prompts"] = [
            {
                "prompt": (row["prompt_text"] or "")[:60],
                "cost": round(float(row["cost_usd"]), 4),
                "model": row["model"] or "unknown",
                "type": row["resolution_type"] or "llm",
            }
            for row in cur.fetchall()
        ]

        conn.close()
    except Exception:
        pass

    return stats


def _generate_html_report(stats: dict, days: int) -> str:
    """Generate a self-contained HTML report with dark theme."""
    period = f"{stats['period_start']} to {stats['period_end']}"
    total = stats["total_requests"]
    bd = stats["breakdown"]
    cost_without = stats["cost_without"]
    cost_with = stats["cost_with"]
    saved_usd = stats["saved_usd"]
    saved_pct = stats["saved_pct"]
    coffees = round(saved_usd / 5.0, 1) if saved_usd > 0 else 0

    # Build breakdown rows
    breakdown_html = ""
    type_colors = {
        "cache": "#00D4AA",
        "rule": "#6C5CE7",
        "routed": "#4A9EFF",
        "template": "#FFB84D",
        "passthrough": "#3B82F6",
        "llm": "#FF6B6B",
    }
    for rtype, count in bd.items():
        pct = (count / total * 100) if total > 0 else 0
        color = type_colors.get(rtype, "#6B6B82")
        breakdown_html += f"""
            <tr>
                <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:8px;"></span>{rtype.upper()}</td>
                <td style="text-align:right;font-family:'JetBrains Mono',monospace;">{count}</td>
                <td style="text-align:right;font-family:'JetBrains Mono',monospace;">{pct:.1f}%</td>
                <td style="width:40%;">
                    <div style="height:8px;border-radius:4px;background:#1A1A26;overflow:hidden;">
                        <div style="height:100%;width:{pct}%;border-radius:4px;background:{color};"></div>
                    </div>
                </td>
            </tr>"""

    # Build top rules rows
    rules_html = ""
    for i, rule in enumerate(stats["top_rules"], 1):
        rules_html += f"""
            <tr>
                <td style="color:#6B6B82;">{i}</td>
                <td style="font-family:'JetBrains Mono',monospace;font-size:12px;">{rule['prompt'][:50]}{'...' if len(rule['prompt']) > 50 else ''}</td>
                <td style="text-align:right;font-family:'JetBrains Mono',monospace;color:#6C5CE7;font-weight:700;">{rule['hits']}</td>
            </tr>"""
    if not rules_html:
        rules_html = '<tr><td colspan="3" style="text-align:center;color:#6B6B82;padding:24px;">No rule hits in this period</td></tr>'

    # Build expensive prompts rows
    expensive_html = ""
    for i, ep in enumerate(stats["expensive_prompts"], 1):
        expensive_html += f"""
            <tr>
                <td style="color:#6B6B82;">{i}</td>
                <td style="font-family:'JetBrains Mono',monospace;font-size:12px;">{ep['prompt'][:50]}{'...' if len(ep['prompt']) > 50 else ''}</td>
                <td style="text-align:right;font-family:'JetBrains Mono',monospace;color:#FFB84D;">${ep['cost']:.4f}</td>
                <td style="text-align:right;font-size:12px;color:#6B6B82;">{ep['model']}</td>
            </tr>"""
    if not expensive_html:
        expensive_html = '<tr><td colspan="4" style="text-align:center;color:#6B6B82;padding:24px;">No cost data in this period</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RuleShield Wrapped - {days} Day Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0A0A0F; color: #F0F0F5; font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 24px; }}
        h1 {{ font-size: 48px; font-weight: 800; background: linear-gradient(135deg, #6C5CE7, #00D4AA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 4px; }}
        h2 {{ font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; color: #6B6B82; margin-bottom: 20px; }}
        .subtitle {{ color: #6B6B82; font-size: 14px; margin-bottom: 32px; }}
        .card {{ background: #12121A; border: 1px solid #2A2A3C; border-radius: 16px; padding: 28px; margin: 20px 0; }}
        .metric {{ font-size: 56px; font-weight: 800; font-family: 'JetBrains Mono', 'Fira Code', monospace; line-height: 1; }}
        .metric-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #6B6B82; margin-bottom: 8px; }}
        .accent {{ color: #00D4AA; }}
        .primary {{ color: #6C5CE7; }}
        .muted {{ color: #6B6B82; }}
        .warning {{ color: #FFB84D; }}
        .glow {{ text-shadow: 0 0 40px rgba(0, 212, 170, 0.4); }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td, th {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #2A2A3C; font-size: 14px; }}
        th {{ color: #6B6B82; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
        .hero {{ text-align: center; padding: 48px 0 32px; }}
        .hero .metric {{ font-size: 72px; }}
        .divider {{ height: 1px; background: linear-gradient(90deg, transparent, #2A2A3C, transparent); margin: 32px 0; }}
        .coffee {{ display: inline-flex; align-items: center; gap: 8px; background: #1A1A26; border: 1px solid #2A2A3C; border-radius: 100px; padding: 12px 24px; font-size: 16px; margin-top: 16px; }}
        .footer {{ text-align: center; padding: 32px 0; color: #6B6B82; font-size: 12px; }}
        .share-box {{ background: #1A1A26; border: 1px solid #2A2A3C; border-radius: 12px; padding: 16px 20px; font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #A0A0B8; line-height: 1.6; }}
    </style>
</head>
<body>

    <!-- Header -->
    <div class="hero">
        <p class="metric-label">RuleShield Wrapped</p>
        <h1>{days}-Day Report</h1>
        <p class="subtitle">{period}</p>

        <p class="metric-label">Total Saved</p>
        <p class="metric accent glow">${saved_usd:.2f}</p>
        <p style="color:#A0A0B8;font-size:18px;margin-top:8px;">{saved_pct:.1f}% savings rate</p>

        <div class="coffee">
            <span style="font-size:24px;">&#9749;</span>
            <span>That's <strong style="color:#00D4AA;">{coffees}</strong> cups of coffee</span>
        </div>
    </div>

    <div class="divider"></div>

    <!-- Overview Cards -->
    <div class="grid-3" style="margin-bottom:20px;">
        <div class="card" style="text-align:center;">
            <p class="metric-label">Total Requests</p>
            <p class="metric" style="font-size:36px;color:#F0F0F5;">{total}</p>
        </div>
        <div class="card" style="text-align:center;">
            <p class="metric-label">Cost Without</p>
            <p class="metric" style="font-size:36px;color:#A0A0B8;">${cost_without:.2f}</p>
        </div>
        <div class="card" style="text-align:center;">
            <p class="metric-label">Cost With</p>
            <p class="metric" style="font-size:36px;color:#F0F0F5;">${cost_with:.2f}</p>
        </div>
    </div>

    <!-- Breakdown -->
    <div class="card">
        <h2>Resolution Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th style="text-align:right;">Count</th>
                    <th style="text-align:right;">Percent</th>
                    <th>Distribution</th>
                </tr>
            </thead>
            <tbody>{breakdown_html}
            </tbody>
        </table>
    </div>

    <!-- Top Rules -->
    <div class="card">
        <h2>Top 5 Rules by Hit Count</h2>
        <table>
            <thead>
                <tr>
                    <th style="width:30px;">#</th>
                    <th>Prompt Pattern</th>
                    <th style="text-align:right;">Hits</th>
                </tr>
            </thead>
            <tbody>{rules_html}
            </tbody>
        </table>
    </div>

    <!-- Expensive Prompts -->
    <div class="card">
        <h2>Top 3 Most Expensive Prompts</h2>
        <table>
            <thead>
                <tr>
                    <th style="width:30px;">#</th>
                    <th>Prompt</th>
                    <th style="text-align:right;">Cost</th>
                    <th style="text-align:right;">Model</th>
                </tr>
            </thead>
            <tbody>{expensive_html}
            </tbody>
        </table>
    </div>

    <div class="divider"></div>

    <!-- Footer -->
    <div class="footer">
        <p style="margin-bottom:8px;">Generated by <strong style="color:#6C5CE7;">RuleShield Hermes</strong></p>
        <p>LLM Cost Optimizer &middot; {stats['period_end']}</p>
    </div>

</body>
</html>"""


@main.command()
@click.option("--days", type=int, default=30, show_default=True, help="Number of days to include.")
@click.option("--export", "export_path", type=click.Path(), default=None, help="Export report as HTML file.")
def wrapped(days: int, export_path: str | None) -> None:
    """Generate a \"Wrapped\" monthly savings report.

    \b
    Shows a beautifully formatted summary of your RuleShield savings
    over the last N days, including resolution breakdown, top rules,
    most expensive prompts, and fun metrics.
    """
    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy and send some requests first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    stats_data = _query_wrapped_stats(days)

    # --- HTML export ---
    if export_path:
        html = _generate_html_report(stats_data, days)
        out_path = Path(export_path)
        out_path.write_text(html, encoding="utf-8")
        console.print()
        console.print(f"  [bright_green]Report exported to:[/bright_green] [cyan]{out_path.resolve()}[/cyan]")
        console.print()
        return

    # --- CLI output ---
    total = stats_data["total_requests"]
    bd = stats_data["breakdown"]
    saved_usd = stats_data["saved_usd"]
    saved_pct = stats_data["saved_pct"]
    coffees = round(saved_usd / 5.0, 1) if saved_usd > 0 else 0

    console.print()
    console.print(
        Panel(
            Text("RuleShield Wrapped", justify="center", style=f"bold {_BRAND}"),
            subtitle=f"{days}-Day Savings Report",
            subtitle_align="center",
            border_style=_BRAND,
            padding=(1, 4),
        )
    )

    # Period
    console.print()
    console.print(
        f"  [bold]Period:[/bold]  [{_DIM}]{stats_data['period_start']} to {stats_data['period_end']}[/{_DIM}]"
    )
    console.print(f"  [bold]Total Requests:[/bold]  [{_RULE_CLR}]{total}[/{_RULE_CLR}]")
    console.print()

    # --- Breakdown table ---
    bd_table = Table(
        title="Resolution Breakdown",
        title_style=f"bold {_BRAND}",
        border_style="grey37",
        padding=(0, 2),
    )
    bd_table.add_column("Type", style="white", width=14)
    bd_table.add_column("Count", justify="right", width=8, style=_RULE_CLR)
    bd_table.add_column("Percent", justify="right", width=10)
    bd_table.add_column("Bar", width=30)

    type_styles = {
        "cache": _CACHE_CLR,
        "rule": _RULE_CLR,
        "routed": "blue",
        "template": _LLM_CLR,
        "passthrough": "bright_blue",
        "llm": "red",
    }

    for rtype, count in bd.items():
        pct = (count / total * 100) if total > 0 else 0
        bar_len = int(pct / 100 * 25)
        bar = "=" * bar_len
        style = type_styles.get(rtype, _DIM)
        bd_table.add_row(
            rtype.upper(),
            str(count),
            Text(f"{pct:.1f}%", style=style),
            Text(bar, style=style),
        )

    console.print(bd_table)
    console.print()

    # --- Savings panel ---
    savings_panel_text = Text()
    savings_panel_text.append("Cost Without RuleShield:  ", style="bold")
    savings_panel_text.append(f"${stats_data['cost_without']:.2f}\n", style=_DIM)
    savings_panel_text.append("Cost With RuleShield:     ", style="bold")
    savings_panel_text.append(f"${stats_data['cost_with']:.2f}\n\n", style="white")
    savings_panel_text.append("Total Saved:              ", style="bold")
    savings_panel_text.append(f"${saved_usd:.2f}", style=f"bold {_CACHE_CLR}")
    savings_panel_text.append(f"  ({saved_pct:.1f}%)\n", style=_CACHE_CLR)

    console.print(
        Panel(
            savings_panel_text,
            title="Cost Savings",
            title_align="left",
            border_style=_CACHE_CLR,
            padding=(1, 4),
        )
    )
    console.print()

    # --- Top rules ---
    if stats_data["top_rules"]:
        rules_table = Table(
            title="Top 5 Rules by Hit Count",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        rules_table.add_column("#", style=_DIM, justify="right", width=4)
        rules_table.add_column("Prompt Pattern", style="white", min_width=30, max_width=50)
        rules_table.add_column("Hits", justify="right", width=8, style=_CACHE_CLR)

        for i, rule in enumerate(stats_data["top_rules"], 1):
            prompt_preview = rule["prompt"][:50]
            if len(rule["prompt"]) > 50:
                prompt_preview += "..."
            rules_table.add_row(str(i), prompt_preview, str(rule["hits"]))

        console.print(rules_table)
        console.print()

    # --- Expensive prompts ---
    if stats_data["expensive_prompts"]:
        exp_table = Table(
            title="Top 3 Most Expensive Prompts",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        exp_table.add_column("#", style=_DIM, justify="right", width=4)
        exp_table.add_column("Prompt", style="white", min_width=30, max_width=45)
        exp_table.add_column("Cost", justify="right", width=10, style=_LLM_CLR)
        exp_table.add_column("Model", style=_DIM, width=16)

        for i, ep in enumerate(stats_data["expensive_prompts"], 1):
            prompt_preview = ep["prompt"][:45]
            if len(ep["prompt"]) > 45:
                prompt_preview += "..."
            exp_table.add_row(str(i), prompt_preview, f"${ep['cost']:.4f}", ep["model"])

        console.print(exp_table)
        console.print()

    # --- Fun metric ---
    console.print(
        Panel(
            Text(
                f"Your savings are equivalent to {coffees} cups of coffee!",
                justify="center",
                style=f"bold {_CACHE_CLR}",
            ),
            border_style=_CACHE_CLR,
            padding=(0, 4),
        )
    )
    console.print()
    console.print(
        f"  [dim]Export as HTML: [cyan]ruleshield wrapped --export report.html[/cyan][/dim]"
    )
    console.print()


# ---------------------------------------------------------------------------
# auto-promote
# ---------------------------------------------------------------------------


@main.command("auto-promote")
@click.option("--yes", "-y", is_flag=True, help="Actually promote eligible rules (dry-run by default).")
def auto_promote(yes: bool) -> None:
    """Check and promote candidate rules based on shadow accuracy and feedback.

    \b
    Rules must meet ALL of these criteria to be promoted:
      - Currently disabled (shadow / candidate mode)
      - At least 10 shadow comparisons
      - Shadow accuracy > 80%
      - Feedback acceptance rate > 85% (or no feedback yet)

    By default this command performs a DRY RUN -- it shows candidates and
    their status without actually promoting anything.  Pass --yes to apply.
    """
    import asyncio as _asyncio

    if not DB_PATH.exists():
        console.print()
        console.print("[yellow]No data yet.[/yellow] Start the proxy first.")
        console.print(f"[dim]Expected database at: {DB_PATH}[/dim]")
        console.print()
        return

    async def _run() -> None:
        from ruleshield.feedback import RuleFeedback
        from ruleshield.rules import RuleEngine

        engine = RuleEngine(rules_dir=str(RULES_DIR))
        await engine.init()

        fb = RuleFeedback(engine, db_path=str(DB_PATH))
        await fb.init()

        candidates = await fb.get_promotion_candidates()

        if not candidates:
            console.print()
            console.print("[yellow]No disabled rules found.[/yellow]")
            console.print("[dim]Rules must be disabled (enabled: false) to be promotion candidates.[/dim]")
            console.print()
            await fb.close()
            return

        # --- Display candidates table ---
        console.print()
        console.print(
            Panel(
                Text("Auto-Promotion Candidates", justify="center", style=f"bold {_BRAND}"),
                border_style=_BRAND,
                padding=(0, 4),
            )
        )
        console.print()

        tbl = Table(
            title="Disabled Rules",
            title_style=f"bold {_BRAND}",
            border_style="grey37",
            padding=(0, 2),
        )
        tbl.add_column("Rule ID", style="white", min_width=18)
        tbl.add_column("Name", style="white", min_width=20)
        tbl.add_column("Confidence", justify="right", width=12)
        tbl.add_column("Shadow Comps", justify="right", width=14, style=_RULE_CLR)
        tbl.add_column("Shadow Acc", justify="right", width=12)
        tbl.add_column("Feedback", justify="right", width=10)
        tbl.add_column("Accept Rate", justify="right", width=12)
        tbl.add_column("Promotable", justify="center", width=12)

        promotable_ids: list[str] = []

        for c in candidates:
            shadow_style = _CACHE_CLR if c["shadow_avg_sim"] >= 0.80 else "yellow"
            acc_style = _CACHE_CLR if c["acceptance_rate"] >= 0.85 else "yellow"
            promo_text = (
                f"[{_CACHE_CLR}]YES[/{_CACHE_CLR}]"
                if c["promotable"]
                else "[red]NO[/red]"
            )
            if c["promotable"]:
                promotable_ids.append(c["rule_id"])

            tbl.add_row(
                c["rule_id"],
                c["rule_name"],
                f"{c['confidence']:.4f}",
                str(c["shadow_total"]),
                f"[{shadow_style}]{c['shadow_avg_sim'] * 100:.1f}%[/{shadow_style}]",
                str(c["feedback_total"]),
                f"[{acc_style}]{c['acceptance_rate'] * 100:.1f}%[/{acc_style}]",
                promo_text,
            )

        console.print(tbl)
        console.print()

        if not promotable_ids:
            console.print(
                "  [yellow]No rules meet promotion criteria yet.[/yellow]"
            )
            console.print(
                "  [dim]Rules need >= 10 shadow comparisons with >= 80% accuracy"
                " and >= 85% feedback acceptance rate.[/dim]"
            )
            console.print()
            await fb.close()
            return

        console.print(
            f"  [bold]{len(promotable_ids)}[/bold] rule(s) eligible for promotion."
        )

        if not yes:
            console.print()
            console.print(
                "  [dim]This is a dry run. Pass --yes to actually promote rules.[/dim]"
            )
            console.print()
            await fb.close()
            return

        # Actually promote
        console.print()
        promoted_count = 0
        for rule_id in promotable_ids:
            if engine.activate_rule(rule_id):
                console.print(f"  [{_CACHE_CLR}]Promoted:[/{_CACHE_CLR}] {rule_id}")
                promoted_count += 1
            else:
                console.print(f"  [red]Failed to promote:[/red] {rule_id}")

        console.print()
        console.print(
            f"  [bold {_CACHE_CLR}]{promoted_count} rule(s) promoted successfully.[/bold {_CACHE_CLR}]"
        )
        console.print()

        await fb.close()

    _asyncio.run(_run())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
