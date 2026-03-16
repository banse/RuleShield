#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$TESTS_DIR/.." && pwd)"
source "$TESTS_DIR/_stories_helpers.sh"

PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
TMP_HOME="$(mktemp -d)"

cleanup() {
	rm -rf "$TMP_HOME"
}
trap cleanup EXIT

mkdir -p "$TMP_HOME/.hermes"
cat >"$TMP_HOME/.hermes/config.yaml" <<'YAML'
model:
  provider: openrouter
  model: arcee-ai/trinity-large-preview:free
  base_url: http://127.0.0.1:9001/v1
YAML

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m ruleshield.cli init --hermes >/dev/null

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import yaml

home = Path.home()
hermes_cfg = home / ".hermes" / "config.yaml"
backup_file = home / ".ruleshield" / "hermes_original_url.txt"

data = yaml.safe_load(hermes_cfg.read_text(encoding="utf-8")) or {}
base_url = ((data.get("model") or {}).get("base_url") or "").strip()
if base_url != "http://127.0.0.1:8347/v1":
    raise SystemExit(f"init --hermes did not patch expected base_url, got: {base_url}")
if not backup_file.is_file():
    raise SystemExit("expected Hermes base_url backup file is missing")
PY

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m ruleshield.cli restore-hermes >/dev/null

HOME="$TMP_HOME" PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import yaml

home = Path.home()
hermes_cfg = home / ".hermes" / "config.yaml"
data = yaml.safe_load(hermes_cfg.read_text(encoding="utf-8")) or {}
base_url = ((data.get("model") or {}).get("base_url") or "").strip()
if base_url != "http://127.0.0.1:9001/v1":
    raise SystemExit(f"restore-hermes did not restore old base_url, got: {base_url}")
PY

echo "story_install_init_restore: ok"
