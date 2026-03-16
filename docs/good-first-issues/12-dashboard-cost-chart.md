# Dashboard: Add cost trend chart (last 7 days)

**Labels:** `good first issue`, `help wanted`, `dashboard`, `enhancement`, `UI`

## Description

Add a new section to the RuleShield dashboard that displays a cost trend chart showing daily costs over the last 7 days. The chart should compare "cost without RuleShield" vs. "cost with RuleShield" on a day-by-day basis, making the savings impact immediately visible over time.

## Why this is useful

The current dashboard shows aggregate cost savings as a single number, but it does not show trends over time. A daily cost chart helps users understand whether their savings are improving, spot anomalies (sudden cost spikes), and demonstrate ROI to stakeholders. Visual cost trends are one of the most-requested features in cost optimization tools.

## Where to look in the codebase

### Dashboard page

**File:** `dashboard/src/routes/+page.svelte`

The main dashboard page has four rows of content:
1. Metric cards (line ~132)
2. Cost savings panel (line ~186)
3. Two-column layout: Recent Requests table + Top Rules table (line ~236)
4. Shadow Mode panel (line ~350)

The cost trend chart should be inserted as a new section between the savings panel (Row 2) and the two-column layout (Row 3), or at the bottom before the footer.

### Data loading

**File:** `dashboard/src/routes/+page.server.ts`

This file fetches data from the RuleShield proxy API. You will need to add a new API call to fetch daily cost data. The proxy API base is `http://localhost:8347`.

### Proxy API

**File:** `ruleshield/proxy.py`

You will need to add a new API endpoint to the proxy that returns daily cost aggregates. The `request_log` table (see schema in `ruleshield/cache.py`, line ~60) has `cost_usd`, `resolution_type`, and `created_at` columns that can be grouped by day.

Suggested new endpoint:

```python
@app.get("/api/costs/daily")
async def get_daily_costs(days: int = Query(default=7)):
    """Return daily cost breakdown for the last N days."""
    # Query request_log grouped by date
    # For each day, return:
    #   - date
    #   - total_cost (cost_with_ruleshield)
    #   - estimated_cost_without (total cost if all requests went to LLM)
    #   - savings
```

### Database schema reference

**File:** `ruleshield/cache.py` (line ~60)

```sql
CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_hash TEXT NOT NULL,
    prompt_text TEXT,
    response TEXT,
    model TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    resolution_type TEXT,    -- 'cache', 'rule', 'llm', 'passthrough'
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

SQL query for daily costs:

```sql
SELECT
    DATE(created_at) AS day,
    SUM(cost_usd) AS total_cost,
    SUM(CASE WHEN resolution_type = 'llm' THEN cost_usd ELSE 0 END) AS llm_cost,
    SUM(CASE WHEN resolution_type IN ('cache', 'rule') THEN cost_usd ELSE 0 END) AS saved_cost,
    COUNT(*) AS request_count
FROM request_log
WHERE created_at >= DATE('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY day ASC
```

## Implementation approach

### Chart library options

Pick one of these lightweight options:

1. **Chart.js** (recommended) -- Add via npm, use a Svelte wrapper or the canvas API directly. Well-documented, widely used.
   ```bash
   cd dashboard && npm install chart.js
   ```

2. **Lightweight SVG** -- Build a simple bar chart using SVG elements directly in Svelte. No dependencies, full control, but more work.

3. **Inline CSS bars** -- The simplest option: use styled `<div>` elements as bar chart segments. No external dependencies.

### Chart design

- **Type:** Line chart or bar chart
- **X-axis:** Days (last 7 days, labeled with day name or date)
- **Y-axis:** Cost in USD
- **Two series:**
  - "Estimated cost without RuleShield" (all requests at LLM pricing) -- shown in the warning/yellow color (`#FFB84D`)
  - "Actual cost with RuleShield" (only LLM calls charged) -- shown in the accent/green color (`#00D4AA`)
- **Shaded area between the lines** = savings

### Styling

Use the existing dashboard color palette from `dashboard/src/app.css`:
- Background: `var(--color-surface)` (`#12121A`)
- Borders: `var(--color-border)` (`#2A2A3C`)
- Savings line: `var(--color-accent)` (`#00D4AA`)
- Cost line: `var(--color-warning)` (`#FFB84D`)
- Text: `var(--color-text-muted)` for labels, `var(--color-text-primary)` for values

## Acceptance criteria

- [ ] A new API endpoint exists at `/api/costs/daily` in `ruleshield/proxy.py` that returns daily cost data
- [ ] The endpoint accepts a `days` query parameter (default 7)
- [ ] The endpoint returns JSON with per-day cost breakdowns
- [ ] `dashboard/src/routes/+page.server.ts` fetches data from the new endpoint
- [ ] A chart or visual cost breakdown appears on the dashboard page
- [ ] The chart shows at least two data series: cost with and without RuleShield
- [ ] The chart is styled consistently with the existing dashboard theme (dark background, correct brand colors)
- [ ] The chart handles the case where there is no data (shows a helpful empty state message)
- [ ] The chart updates on the 2-second auto-refresh cycle (same as the rest of the dashboard)
- [ ] The chart is responsive and looks correct at different viewport widths

## Estimated difficulty

**Medium** -- Requires changes across three layers: backend API endpoint (Python), data fetching (TypeScript), and frontend chart rendering (Svelte). Each individual change is small, but coordinating them takes some full-stack awareness.

## Helpful links and references

- [Dashboard page](../../dashboard/src/routes/+page.svelte) -- Where to add the chart section
- [Data loading](../../dashboard/src/routes/+page.server.ts) -- Where to fetch chart data
- [Proxy source](../../ruleshield/proxy.py) -- Where to add the API endpoint
- [Cache schema](../../ruleshield/cache.py) -- `request_log` table definition
- [Dashboard CSS](../../dashboard/src/app.css) -- Theme colors to use
- Chart.js docs: https://www.chartjs.org/docs/latest/
- SvelteKit `$effect` for Chart.js: https://svelte.dev/docs/svelte/$effect
