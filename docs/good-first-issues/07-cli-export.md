# CLI: Add `ruleshield export` command

**Labels:** `good first issue`, `help wanted`, `CLI`, `enhancement`

## Description

Add a new `ruleshield export` CLI command that exports the `request_log` table from the SQLite database as CSV or JSON. This allows users to analyze their RuleShield usage data in spreadsheets, BI tools, or custom scripts.

## Why this is useful

Right now, the only way to see request data is through `ruleshield stats` (aggregate numbers) or the live dashboard. Developers and teams often need to export raw data for reporting, cost analysis, or integration with their own monitoring tools. A simple `export` command makes RuleShield data portable and auditable.

## Where to look in the codebase

### CLI structure

**File:** `ruleshield/cli.py`

The CLI uses Click and Rich for formatting. All commands are registered under the `@main.group()` group. Look at the `stats` command (line ~282) for the pattern -- it queries the same SQLite database you will be reading from.

Key patterns to follow:
- Database path: `DB_PATH = RULESHIELD_DIR / "proxy.pid"` is defined at the top, but the actual DB is `DB_PATH = RULESHIELD_DIR / "cache.db"` (line ~38)
- Database queries use `sqlite3` directly (not async -- the CLI is synchronous)
- Rich console is used for all output formatting
- The `_query_stats_from_db()` helper (line ~227) shows how to open and query the database

### Database schema

**File:** `ruleshield/cache.py`

The `request_log` table schema (line ~60):

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
    resolution_type TEXT,
    latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## What to build

Add a new Click command to `ruleshield/cli.py`:

```python
@main.command()
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv", help="Output format.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path (defaults to stdout).")
@click.option("--last", "days", type=int, default=None, help="Only export the last N days of data.")
def export(fmt: str, output: str | None, days: int | None) -> None:
    """Export request log data as CSV or JSON."""
    ...
```

### Expected behavior

```bash
# Export all data as CSV to stdout
ruleshield export

# Export last 7 days as JSON to a file
ruleshield export --format json --output report.json --last 7

# Export as CSV to a file
ruleshield export --format csv -o requests.csv
```

### CSV output format

```csv
id,prompt_hash,prompt_text,model,tokens_in,tokens_out,cost_usd,resolution_type,latency_ms,created_at
1,abc123...,hello,gpt-4o-mini,5,12,0.000085,rule,2,2025-06-15T10:30:00
```

### JSON output format

```json
[
  {
    "id": 1,
    "prompt_hash": "abc123...",
    "prompt_text": "hello",
    "model": "gpt-4o-mini",
    "tokens_in": 5,
    "tokens_out": 12,
    "cost_usd": 0.000085,
    "resolution_type": "rule",
    "latency_ms": 2,
    "created_at": "2025-06-15T10:30:00"
  }
]
```

## Acceptance criteria

- [ ] `ruleshield export` command is registered and shows up in `ruleshield --help`
- [ ] `--format csv` outputs valid CSV with a header row (default format)
- [ ] `--format json` outputs a valid JSON array of objects
- [ ] `--output filename` writes to a file instead of stdout
- [ ] `--last N` filters to only the last N days of data (using `created_at` column)
- [ ] When no data exists, prints a helpful message (similar to how `stats` handles this case)
- [ ] The `response` column is excluded from the export (it can be very large and is not useful for analysis)
- [ ] Output to stdout uses `click.echo()` or `sys.stdout` (not Rich console, so it can be piped)
- [ ] Existing CLI commands still work correctly

## Estimated difficulty

**Easy** -- Follows the same SQLite query pattern as the existing `stats` command. Uses Python's built-in `csv` and `json` modules. The Click option pattern is well-established in the same file.

## Helpful links and references

- [CLI source](../../ruleshield/cli.py) -- Existing commands and database query patterns
- [Cache/DB schema](../../ruleshield/cache.py) -- `request_log` table definition
- Click documentation: https://click.palletsprojects.com/en/stable/
- Python csv module: https://docs.python.org/3/library/csv.html
