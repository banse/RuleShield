#!/usr/bin/env bash
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${ROOT_DIR:-$(cd "$TESTS_DIR/.." && pwd)}"
RULESHIELD_ROOT="${RULESHIELD_ROOT:-$ROOT_DIR}"

ruleshield_python_bin() {
	local candidate="${PYTHON_BIN:-$RULESHIELD_ROOT/.venv/bin/python}"
	if [[ -x "$candidate" ]]; then
		printf '%s\n' "$candidate"
		return
	fi
	command -v python3
}

import_test_keys_for_home() {
	local tmp_home="$1"
	local source_file="${RULESHIELD_TEST_KEYS_FILE:-$RULESHIELD_ROOT/tests/.local/imported_keys.env}"
	local ruleshield_env="$tmp_home/.ruleshield/.env"
	local python_bin
	local openrouter_key=""
	local openai_key=""
	local parsed_keys_file

	mkdir -p "$tmp_home/.ruleshield" "$tmp_home/.hermes"
	if [[ ! -f "$source_file" ]]; then
		echo "ERROR: missing imported test keys file: $source_file" >&2
		echo "Run: bash tests/import_test_keys.sh" >&2
		return 1
	fi

	python_bin="$(ruleshield_python_bin)"
	parsed_keys_file="$(mktemp)"
	RULESHIELD_TEST_KEYS_FILE="$source_file" "$python_bin" - <<'PY' >"$parsed_keys_file"
import os
from pathlib import Path

path = Path(os.environ["RULESHIELD_TEST_KEYS_FILE"])
vals = {}
for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    vals[k.strip()] = v.strip().strip('"').strip("'")
print(vals.get("OPENROUTER_API_KEY", ""))
print(vals.get("OPENAI_API_KEY", ""))
PY
	openrouter_key="$(sed -n '1p' "$parsed_keys_file")"
	openai_key="$(sed -n '2p' "$parsed_keys_file")"
	rm -f "$parsed_keys_file"

	: >"$ruleshield_env"

	if [[ -n "$openrouter_key" ]]; then
		printf 'OPENROUTER_API_KEY=%s\n' "$openrouter_key" >>"$ruleshield_env"
	fi
	if [[ -n "$openai_key" ]]; then
		printf 'OPENAI_API_KEY=%s\n' "$openai_key" >>"$ruleshield_env"
	fi
}

ensure_test_ruleshield_config() {
	local tmp_home="$1"
	local desired_port="${2:-}"
	local python_bin
	python_bin="$(ruleshield_python_bin)"
	HOME="$tmp_home" "$python_bin" - "$desired_port" <<'PY'
import sys
from pathlib import Path
import yaml

desired_port_raw = (sys.argv[1] or "").strip()
desired_port = int(desired_port_raw) if desired_port_raw else None

cfg_dir = Path.home() / ".ruleshield"
cfg_path = cfg_dir / "config.yaml"
cfg_dir.mkdir(parents=True, exist_ok=True)

data = {}
if cfg_path.is_file():
    try:
        loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data = loaded
    except Exception:
        data = {}

if desired_port is not None:
    data["port"] = int(desired_port)
else:
    data["port"] = int(data.get("port", 8347))

# Disable Smart Router for test stability (config-based, not script override).
data["router_enabled"] = False

cfg_path.write_text(
    yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
    encoding="utf-8",
)
PY
}

resolve_openrouter_key_for_home() {
	local tmp_home="$1"
	local python_bin
	python_bin="$(ruleshield_python_bin)"
	HOME="$tmp_home" "$python_bin" - <<'PY'
import os
from pathlib import Path

home = Path.home()

def parse_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

key = (os.getenv("RULESHIELD_OPENROUTER_API_KEY") or "").strip()
if not key:
    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
if not key:
    key = parse_dotenv(home / ".ruleshield" / ".env").get("OPENROUTER_API_KEY", "").strip()

print(key)
PY
}

wait_for_health() {
	local url="$1"
	local timeout_seconds="${2:-8}"
	local tries=0
	local max_tries=$((timeout_seconds * 10))

	until curl -fsS "$url" >/dev/null 2>&1; do
		tries=$((tries + 1))
		if [[ "$tries" -ge "$max_tries" ]]; then
			echo "ERROR: gateway health did not become ready: $url" >&2
			return 1
		fi
		sleep 0.1
	done
}

start_gateway_for_home() {
	local tmp_home="$1"
	local log_file="$2"
	local pid_file="$3"
	local python_bin
	local port
	local openrouter_key

	python_bin="$(ruleshield_python_bin)"
	import_test_keys_for_home "$tmp_home"
	ensure_test_ruleshield_config "$tmp_home"
	port="$(HOME="$tmp_home" PYTHONPATH="$RULESHIELD_ROOT" "$python_bin" - <<'PY'
from ruleshield.config import load_settings
print(load_settings().port)
PY
)"
	openrouter_key="$(resolve_openrouter_key_for_home "$tmp_home")"

	HOME="$tmp_home" PYTHONPATH="$RULESHIELD_ROOT" \
	OPENROUTER_API_KEY="$openrouter_key" RULESHIELD_OPENROUTER_API_KEY="$openrouter_key" \
	"$python_bin" -m uvicorn ruleshield.proxy:app \
		--host 127.0.0.1 \
		--port "$port" \
		--log-level info \
		--app-dir "$RULESHIELD_ROOT" >"$log_file" 2>&1 &
	echo $! >"$pid_file"
	wait_for_health "http://127.0.0.1:${port}/health"
	printf '%s\n' "$port"
}

stop_gateway_from_pid_file() {
	local pid_file="$1"
	if [[ -f "$pid_file" ]]; then
		local pid
		pid="$(cat "$pid_file" 2>/dev/null || true)"
		if [[ -n "$pid" ]]; then
			kill "$pid" 2>/dev/null || true
			wait "$pid" 2>/dev/null || true
		fi
		rm -f "$pid_file"
	fi
}
