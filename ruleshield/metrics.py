"""RuleShield Hermes -- Real-time terminal metrics dashboard.

Beautiful Rich-powered dashboard that visualises request routing, cache hits,
rule matches, LLM calls, and cumulative cost savings in real time.  Designed
to be the star of the hackathon demo video.

Also contains the original ``MetricsCollector`` async interface so that
``proxy.py`` keeps working without changes.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from typing import Any

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BRAND = "magenta"
_CACHE_CLR = "bright_green"
_RULE_CLR = "bright_cyan"
_ROUTED_CLR = "bright_blue"
_LLM_CLR = "yellow"
_HEADER_CLR = "bold bright_white"
_DIM = "dim"
_MAX_RECENT = 15
_MAX_TOP_RULES = 8
_PROMPT_TRUNC = 35
_REFRESH_HZ = 4  # dashboard refreshes per second
_BAR_WIDTH = 30

# Unicode bar characters for the savings visualisation.
_BLOCK_FULL = "\u2588"
_BLOCK_MED = "\u2592"
_BLOCK_LIGHT = "\u2591"

# ASCII art banner lines -- kept compact so it works in 80-col terminals.
_BANNER_ART = r"""
    ____        __     _____ __    _      __    __
   / __ \__  __/ /__  / ___// /_  (_)__  / /___/ /
  / /_/ / / / / / _ \ \__ \/ __ \/ / _ \/ / __  /
 / _, _/ /_/ / /  __/___/ / / / / /  __/ / /_/ /
/_/ |_|\__,_/_/\___//____/_/ /_/_/\___/_/\__,_/
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pct(part: int, total: int) -> str:
    """Return a percentage string like '42%', or '0%' when total is zero."""
    if total == 0:
        return "0%"
    return f"{round(part / total * 100)}%"


def _pct_val(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return part / total * 100


def _savings_colour(pct: float) -> str:
    if pct >= 50:
        return _CACHE_CLR
    if pct >= 20:
        return "yellow"
    return "red"


def _resolution_style(res: str) -> str:
    res = res.upper()
    if res == "CACHE":
        return _CACHE_CLR
    if res == "RULE":
        return _RULE_CLR
    if res == "ROUTED":
        return _ROUTED_CLR
    if res == "PASSTHROUGH":
        return _ROUTED_CLR
    if res == "LLM":
        return _LLM_CLR
    return "white"


def _truncate(text: str, length: int = _PROMPT_TRUNC) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[:length] + "..."


def _visual_bar(pct: float, width: int = _BAR_WIDTH) -> Text:
    """Build a coloured bar: filled portion + empty portion."""
    filled = int(round(pct / 100 * width))
    empty = width - filled
    colour = _savings_colour(pct)
    bar = Text()
    bar.append(_BLOCK_FULL * filled, style=colour)
    bar.append(_BLOCK_LIGHT * empty, style=_DIM)
    bar.append(f"  {pct:.0f}%", style=f"bold {colour}")
    return bar


# ---------------------------------------------------------------------------
# MetricsDashboard -- the live terminal dashboard
# ---------------------------------------------------------------------------


class MetricsDashboard:
    """Real-time Rich terminal dashboard for RuleShield Hermes.

    All public methods are thread-safe.  The dashboard renders in a
    background thread so it never blocks the proxy event loop.
    """

    def __init__(self) -> None:
        self.console = Console()

        # Counters
        self.total_requests: int = 0
        self.cache_hits: int = 0
        self.rule_hits: int = 0
        self.routed_calls: int = 0
        self.passthrough_calls: int = 0
        self.llm_calls: int = 0
        self.total_cost_without: float = 0.0
        self.total_cost_with: float = 0.0

        # Recent request log (bounded deque)
        self.recent_requests: deque[dict[str, Any]] = deque(maxlen=_MAX_RECENT)

        # Rule hit tracking: rule_id -> {name, hits, confidence_sum}
        self.top_rules: dict[str, dict[str, Any]] = {}

        # Timing
        self._start_time: float = time.monotonic()

        # Live display state
        self._live: Live | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # -- Public API ---------------------------------------------------------

    def log_request(
        self,
        prompt_text: str,
        resolution_type: str,
        cost: float,
        estimated_full_cost: float,
        rule_id: str | None = None,
        rule_name: str | None = None,
        confidence: float | None = None,
    ) -> None:
        """Log a request and update all metrics.  Thread-safe."""
        with self._lock:
            self.total_requests += 1
            self.total_cost_with += cost
            self.total_cost_without += estimated_full_cost

            res = resolution_type.upper()
            if res == "CACHE":
                self.cache_hits += 1
            elif res == "RULE":
                self.rule_hits += 1
            elif res == "ROUTED":
                self.routed_calls += 1
            elif res == "PASSTHROUGH":
                self.passthrough_calls += 1
            else:
                self.llm_calls += 1

            saved = estimated_full_cost - cost

            self.recent_requests.appendleft(
                {
                    "num": self.total_requests,
                    "prompt": prompt_text,
                    "type": res,
                    "cost": cost,
                    "saved": saved,
                    "ts": datetime.now(),
                }
            )

            if rule_id:
                entry = self.top_rules.setdefault(
                    rule_id,
                    {"name": rule_name or rule_id, "hits": 0, "confidence_sum": 0.0},
                )
                entry["hits"] += 1
                if confidence is not None:
                    entry["confidence_sum"] += confidence

    def start_live(self) -> None:
        """Start the live-updating dashboard in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._start_time = time.monotonic()
        self._thread = threading.Thread(
            target=self._run_live, daemon=True, name="ruleshield-dashboard"
        )
        self._thread.start()

    def stop_live(self) -> None:
        """Stop the live dashboard gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def print_summary(self) -> None:
        """Print a final summary when dashboard stops."""
        self.console.print()
        self.console.rule(
            Text(" RuleShield Session Summary ", style=f"bold {_BRAND}"),
            style=_BRAND,
        )
        self.console.print()

        with self._lock:
            total = self.total_requests
            cache = self.cache_hits
            rule = self.rule_hits
            llm = self.llm_calls
            cost_without = self.total_cost_without
            cost_with = self.total_cost_with

        saved_pct = _pct_val(1, 1) * 0  # initialise
        if cost_without > 0:
            saved_pct = (cost_without - cost_with) / cost_without * 100

        tbl = Table(show_header=False, box=None, padding=(0, 2))
        tbl.add_column(style=_DIM, justify="right")
        tbl.add_column(style="bold")

        tbl.add_row("Total Requests", str(total))
        tbl.add_row("Cache Hits", f"{cache}  ({_pct(cache, total)})")
        tbl.add_row("Rule Hits", f"{rule}  ({_pct(rule, total)})")
        tbl.add_row("LLM Calls", f"{llm}  ({_pct(llm, total)})")
        tbl.add_row("", "")
        tbl.add_row("Cost Without RuleShield", f"${cost_without:.2f}")
        tbl.add_row("Cost With RuleShield", f"${cost_with:.2f}")

        colour = _savings_colour(saved_pct)
        tbl.add_row(
            "Total Saved",
            Text(f"${cost_without - cost_with:.2f}  ({saved_pct:.0f}%)", style=colour),
        )

        elapsed = time.monotonic() - self._start_time
        mins, secs = divmod(int(elapsed), 60)
        tbl.add_row("Session Duration", f"{mins}m {secs}s")

        self.console.print(
            Panel(tbl, title="[bold]Final Results[/bold]", border_style=_BRAND, padding=(1, 2))
        )
        self.console.print()

    def print_request_line(
        self,
        prompt_text: str,
        resolution_type: str,
        cost: float,
        saved: float,
    ) -> None:
        """Print a single coloured request line (non-dashboard mode)."""
        res = resolution_type.upper()
        style = _resolution_style(res)
        tag = Text(f" {res:5s} ", style=f"bold {style} on grey15")
        prompt_short = _truncate(prompt_text, 50)

        line = Text()
        line.append_text(tag)
        line.append("  ")
        line.append(prompt_short, style="white")
        line.append("  ")
        if cost > 0:
            line.append(f"${cost:.4f}", style=_LLM_CLR)
        else:
            line.append("$0.00", style=_CACHE_CLR)
        if saved > 0:
            line.append(f"  (saved ${saved:.4f})", style=f"{_DIM} {_CACHE_CLR}")

        self.console.print(line)

    # -- Internal -----------------------------------------------------------

    def _run_live(self) -> None:
        """Background thread: run the Rich Live display."""
        with Live(
            self._build_dashboard(),
            console=self.console,
            refresh_per_second=_REFRESH_HZ,
            screen=False,
        ) as live:
            self._live = live
            while not self._stop_event.is_set():
                live.update(self._build_dashboard())
                self._stop_event.wait(1.0 / _REFRESH_HZ)
            self._live = None

    def _build_dashboard(self) -> Panel:
        """Build the full dashboard as a Rich renderable."""
        with self._lock:
            total = self.total_requests
            cache = self.cache_hits
            rule = self.rule_hits
            llm = self.llm_calls
            cost_without = self.total_cost_without
            cost_with = self.total_cost_with
            recent = list(self.recent_requests)
            rules_snapshot = {
                k: dict(v) for k, v in self.top_rules.items()
            }

        savings_pct = 0.0
        if cost_without > 0:
            savings_pct = (cost_without - cost_with) / cost_without * 100

        elapsed = time.monotonic() - self._start_time
        mins, secs = divmod(int(elapsed), 60)

        # -- Header row -----------------------------------------------------
        header_left = Text("  RuleShield for Hermes Agent", style=f"bold {_BRAND}")
        dot_style = _CACHE_CLR if total > 0 else _DIM
        header_right = Text()
        header_right.append(" LIVE ", style=f"bold white on {dot_style}")
        header_right.append(f"  {mins:02d}:{secs:02d}", style=_DIM)

        header_table = Table.grid(expand=True)
        header_table.add_column(ratio=1)
        header_table.add_column(justify="right")
        header_table.add_row(header_left, header_right)

        # -- Metric cards ---------------------------------------------------
        cards = self._build_metric_cards(total, cache, rule, llm, savings_pct)

        # -- Cost savings panel ---------------------------------------------
        cost_panel = self._build_cost_panel(cost_without, cost_with, savings_pct)

        # -- Recent requests table ------------------------------------------
        recent_table = self._build_recent_table(recent)

        # -- Top rules table ------------------------------------------------
        rules_table = self._build_rules_table(rules_snapshot)

        # -- Compose --------------------------------------------------------
        parts: list[Any] = [
            header_table,
            Text(),
            cards,
            Text(),
            cost_panel,
            Text(),
            recent_table,
        ]
        if rules_snapshot:
            parts.append(Text())
            parts.append(rules_table)

        group = Group(*parts)

        return Panel(
            group,
            border_style=_BRAND,
            padding=(1, 2),
            subtitle=Text(
                " press Ctrl+C to stop ",
                style=_DIM,
            ),
        )

    def _build_metric_cards(
        self, total: int, cache: int, rule: int, llm: int, savings_pct: float
    ) -> Table:
        """Build the row of metric summary cards."""
        cards = Table.grid(expand=True, padding=(0, 1))
        for _ in range(5):
            cards.add_column(justify="center", ratio=1)

        def _card(label: str, value: str, detail: str = "", style: str = "bold") -> Panel:
            inner = Text(justify="center")
            inner.append(value, style=style)
            if detail:
                inner.append(f"\n{detail}", style=_DIM)
            return Panel(
                inner,
                title=f"[{_HEADER_CLR}]{label}[/]",
                border_style="grey37",
                padding=(0, 1),
                width=16,
            )

        cards.add_row(
            _card("Requests", str(total)),
            _card(
                "Cache",
                str(cache),
                _pct(cache, total),
                style=_CACHE_CLR,
            ),
            _card(
                "Rules",
                str(rule),
                _pct(rule, total),
                style=_RULE_CLR,
            ),
            _card(
                "LLM",
                str(llm),
                _pct(llm, total),
                style=_LLM_CLR,
            ),
            _card(
                "Savings",
                f"{savings_pct:.0f}%",
                style=f"bold {_savings_colour(savings_pct)}",
            ),
        )
        return cards

    def _build_cost_panel(
        self, cost_without: float, cost_with: float, savings_pct: float
    ) -> Panel:
        """Build the cost savings panel with a visual bar."""
        saved = cost_without - cost_with
        colour = _savings_colour(savings_pct)

        tbl = Table.grid(expand=True, padding=(0, 1))
        tbl.add_column(justify="right", style=_DIM, min_width=24)
        tbl.add_column(justify="left")

        tbl.add_row("Without RuleShield:", Text(f"  ${cost_without:.2f}", style="bold"))
        tbl.add_row(
            "With RuleShield:",
            Text(f"  ${cost_with:.2f}", style=f"bold {_CACHE_CLR}"),
        )

        bar_line = Text("  ")
        bar_line.append(f"${saved:.2f}  ", style=f"bold {colour}")
        bar_line.append_text(_visual_bar(savings_pct))

        tbl.add_row("Saved:", bar_line)

        return Panel(
            tbl,
            title=f"[{_HEADER_CLR}]Cost Savings[/]",
            border_style="grey37",
            padding=(0, 2),
        )

    def _build_recent_table(self, recent: list[dict[str, Any]]) -> Panel:
        """Build the recent requests table."""
        tbl = Table(
            expand=True,
            show_edge=False,
            pad_edge=False,
            box=None,
            padding=(0, 1),
        )
        tbl.add_column("#", style=_DIM, justify="right", width=5)
        tbl.add_column("Prompt", ratio=1, no_wrap=True)
        tbl.add_column("Type", justify="center", width=8)
        tbl.add_column("Cost", justify="right", width=8)
        tbl.add_column("Saved", justify="right", width=8)

        if not recent:
            tbl.add_row("", Text("Waiting for requests...", style=_DIM), "", "", "")
        else:
            for req in recent[:10]:
                res = req["type"]
                style = _resolution_style(res)
                tag = Text(f" {res} ", style=f"bold {style}")

                cost_text = (
                    Text("$0.00", style=_CACHE_CLR)
                    if req["cost"] == 0
                    else Text(f"${req['cost']:.4f}", style=_LLM_CLR)
                )
                saved_text = (
                    Text(f"${req['saved']:.4f}", style=_DIM)
                    if req["saved"] > 0
                    else Text("-", style=_DIM)
                )

                tbl.add_row(
                    str(req["num"]),
                    Text(f'"{_truncate(req["prompt"])}"', style="white"),
                    tag,
                    cost_text,
                    saved_text,
                )

        return Panel(
            tbl,
            title=f"[{_HEADER_CLR}]Recent Requests[/]",
            border_style="grey37",
            padding=(0, 2),
        )

    def _build_rules_table(self, rules: dict[str, dict[str, Any]]) -> Panel:
        """Build the top rules table sorted by hit count."""
        tbl = Table(
            expand=True,
            show_edge=False,
            pad_edge=False,
            box=None,
            padding=(0, 1),
        )
        tbl.add_column("Rule", ratio=1, no_wrap=True, style="white")
        tbl.add_column("Hits", justify="right", width=6, style=_RULE_CLR)
        tbl.add_column("Avg Conf.", justify="right", width=10)

        sorted_rules = sorted(
            rules.values(), key=lambda r: r["hits"], reverse=True
        )[:_MAX_TOP_RULES]

        for r in sorted_rules:
            avg_conf = (
                r["confidence_sum"] / r["hits"] * 100
                if r["hits"] > 0 and r["confidence_sum"] > 0
                else 0
            )
            conf_text = Text(f"{avg_conf:.0f}%", style=_CACHE_CLR) if avg_conf else Text("-", style=_DIM)
            tbl.add_row(r["name"], str(r["hits"]), conf_text)

        return Panel(
            tbl,
            title=f"[{_HEADER_CLR}]Top Rules[/]",
            border_style="grey37",
            padding=(0, 2),
        )


# ---------------------------------------------------------------------------
# MetricsCollector -- async interface expected by proxy.py
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Collects request metrics and cost-savings data.

    Wraps ``MetricsDashboard`` so the proxy can call the original async
    interface while the dashboard renders live in the terminal.
    """

    def __init__(self) -> None:
        self.dashboard = MetricsDashboard()
        self._data: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    async def init(self) -> None:
        """Initialize the metrics backend."""
        pass  # No external deps to set up.

    async def record(
        self,
        model: str = "",
        resolution: str = "",
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        latency_ms: float = 0.0,
        cost_saved: float = 0.0,
        prompt_text: str = "",
        rule_id: str | None = None,
        rule_name: str | None = None,
        confidence: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Record a single request event and update the dashboard."""
        # Estimate full cost from tokens (simplified pricing).
        est_full = (tokens_prompt * 0.000003) + (tokens_completion * 0.000015)
        if est_full == 0 and cost_saved > 0:
            est_full = cost_saved

        actual_cost = max(0.0, est_full - cost_saved)

        with self._lock:
            self._data.append(
                {
                    "model": model,
                    "resolution": resolution,
                    "tokens_prompt": tokens_prompt,
                    "tokens_completion": tokens_completion,
                    "latency_ms": latency_ms,
                    "cost_saved": cost_saved,
                    "ts": datetime.now(),
                }
            )

        self.dashboard.log_request(
            prompt_text=prompt_text or f"[{model}]",
            resolution_type=resolution or "LLM",
            cost=actual_cost,
            estimated_full_cost=est_full,
            rule_id=rule_id,
            rule_name=rule_name,
            confidence=confidence,
        )

    async def get_summary(self) -> dict[str, Any]:
        """Return an aggregate metrics summary."""
        with self._lock:
            d = self.dashboard
            return {
                "total_requests": d.total_requests,
                "cache_hits": d.cache_hits,
                "rule_hits": d.rule_hits,
                "passthrough_calls": d.passthrough_calls,
                "llm_calls": d.llm_calls,
                "tokens_saved": sum(
                    r.get("tokens_prompt", 0) + r.get("tokens_completion", 0)
                    for r in self._data
                    if r.get("resolution", "").upper() in ("CACHE", "RULE")
                ),
                "estimated_cost_saved": d.total_cost_without - d.total_cost_with,
                "cost_without": d.total_cost_without,
                "cost_with": d.total_cost_with,
            }

    async def get_timeline(self, hours: int = 24) -> list[dict[str, Any]]:
        """Return per-hour metrics for the last *hours* hours."""
        # Simplified: return raw data points for now.
        with self._lock:
            return list(self._data[-hours * 60 :])


# ---------------------------------------------------------------------------
# Standalone helpers -- startup banner & CLI summary
# ---------------------------------------------------------------------------


def print_startup_banner() -> None:
    """Print a styled startup banner when RuleShield starts."""
    console = Console()
    console.print()

    art_text = Text(_BANNER_ART, style=f"bold {_BRAND}")

    subtitle_parts = Text(justify="center")
    subtitle_parts.append("LLM Cost Optimizer", style="bold white")
    subtitle_parts.append("  |  ", style=_DIM)
    subtitle_parts.append("Hermes Agent Integration", style=_DIM)
    subtitle_parts.append("  |  ", style=_DIM)
    subtitle_parts.append("v0.1.0", style=_BRAND)

    banner_group = Group(
        Align.center(art_text),
        Text(),
        Align.center(subtitle_parts),
    )

    console.print(
        Panel(
            banner_group,
            border_style=_BRAND,
            padding=(0, 4),
        )
    )

    # Feature tags
    tags = Text(justify="center")
    tags.append(" CACHE ", style=f"bold white on {_CACHE_CLR}")
    tags.append("  ")
    tags.append(" RULES ", style=f"bold white on {_RULE_CLR}")
    tags.append("  ")
    tags.append(" LLM PASSTHROUGH ", style=f"bold white on {_LLM_CLR}")
    tags.append("  ")
    tags.append(" REAL-TIME METRICS ", style=f"bold white on {_BRAND}")

    console.print(Align.center(tags))
    console.print()


def print_stats_summary(stats: dict[str, Any]) -> None:
    """Print a summary table from a stats dict (for CLI ``ruleshield stats``)."""
    console = Console()
    console.print()

    total = stats.get("total_requests", 0)
    cache = stats.get("cache_hits", 0)
    rule = stats.get("rule_hits", 0)
    passthrough = stats.get("passthrough", 0)
    llm = stats.get("llm_calls", total - cache - rule - passthrough)
    cost_without = stats.get("cost_without", 0.0)
    cost_with = stats.get("cost_with", 0.0)
    saved = stats.get("estimated_cost_saved", cost_without - cost_with)

    savings_pct = 0.0
    if cost_without > 0:
        savings_pct = saved / cost_without * 100

    # -- Summary table ------------------------------------------------------
    tbl = Table(
        title="RuleShield Session Statistics",
        title_style=f"bold {_BRAND}",
        show_lines=True,
        border_style="grey37",
        padding=(0, 2),
    )
    tbl.add_column("Metric", style=_DIM, justify="right")
    tbl.add_column("Value", style="bold")

    tbl.add_row("Total Requests", str(total))
    tbl.add_row("Cache Hits", Text(f"{cache}  ({_pct(cache, total)})", style=_CACHE_CLR))
    tbl.add_row("Rule Hits", Text(f"{rule}  ({_pct(rule, total)})", style=_RULE_CLR))
    tbl.add_row("Passthrough", Text(f"{passthrough}  ({_pct(passthrough, total)})", style=_ROUTED_CLR))
    tbl.add_row("LLM Calls", Text(f"{llm}  ({_pct(llm, total)})", style=_LLM_CLR))
    tbl.add_row("Cost Without", f"${cost_without:.2f}")
    tbl.add_row("Cost With", f"${cost_with:.2f}")

    colour = _savings_colour(savings_pct)
    saved_line = Text()
    saved_line.append(f"${saved:.2f}", style=f"bold {colour}")
    saved_line.append(f"  ({savings_pct:.0f}%)", style=colour)
    tbl.add_row("Saved", saved_line)

    console.print(tbl)

    # -- Visual bar ---------------------------------------------------------
    console.print()
    bar = _visual_bar(savings_pct, width=40)
    console.print(Align.center(bar))
    console.print()
