#!/usr/bin/env bash
set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${ROOT_DIR:-$(cd "$FRAMEWORK_DIR/../.." && pwd)}"
STATUS_STORE="$ROOT_DIR/tests/framework/status_store.py"
STATUS_LOGS_DIR="$ROOT_DIR/tests/status/data/logs"

SUITE_ID=""
RUN_ID=""
SUITE_STARTED_AT=""

suite_now_iso() {
	python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).replace(microsecond=0).isoformat())
PY
}

suite_now_ms() {
	python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

suite_detect_gateway() {
	if [[ -n "${PROXY_URL:-}" ]]; then
		printf '%s\n' "$PROXY_URL"
		return
	fi
	if [[ -n "${TEST_PORT:-}" ]]; then
		printf 'http://127.0.0.1:%s\n' "$TEST_PORT"
		return
	fi
	if [[ -n "${RULESHIELD_PORT:-}" ]]; then
		printf 'http://127.0.0.1:%s\n' "$RULESHIELD_PORT"
		return
	fi
	printf '%s\n' "-"
}

suite_detect_gateway_from_log() {
	local log_abs="$1"
	local url=""

	url="$(python3 - "$log_abs" <<'PY'
import re
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
if not log_path.is_file():
    print("-")
    raise SystemExit(0)

text = log_path.read_text(encoding="utf-8", errors="ignore")
patterns = [
    r"^Proxy:\s*(https?://[^\s]+)",
    r"\b(https?://127\.0\.0\.1:\d+)\b",
    r"\b(https?://localhost:\d+)\b",
]
for pattern in patterns:
    m = re.search(pattern, text, flags=re.MULTILINE)
    if m:
        print(m.group(1).rstrip("/"))
        raise SystemExit(0)

print("-")
PY
)"

	printf '%s\n' "$url"
}

suite_patch_log_gateway() {
	local log_abs="$1"
	local gateway="$2"
	python3 - "$log_abs" "$gateway" <<'PY'
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
gateway = sys.argv[2]
if not log_path.is_file() or not gateway or gateway == "-":
    raise SystemExit(0)

text = log_path.read_text(encoding="utf-8", errors="ignore")
patched = text.replace("env.gateway=-", f"env.gateway={gateway}", 1)
if patched != text:
    log_path.write_text(patched, encoding="utf-8")
PY
}

suite_extract_error_line() {
	local log_abs="$1"
	python3 - "$log_abs" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    print("unknown")
    raise SystemExit(0)

lines = [ln.rstrip("\r") for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
if not lines:
    print("unknown")
    raise SystemExit(0)

priority_patterns = [
    r"^ERROR:",
    r"monitor run failed",
    r"monitor run timeout",
    r"preflight_",
    r"status=failed",
    r"Traceback",
    r"Exception",
    r"TimeoutError",
    r"provider_config_error",
]
noise_patterns = [
    r'^INFO:\s+\d+\.\d+\.\d+\.\d+:\d+\s+-\s+"(GET|POST|PUT|DELETE)\s+',
    r"^INFO:\s+",
    r'^202\d-\d\d-\d\d .* \[INFO\] ',
    r"^Batches:\s",
]

for line in reversed(lines):
    for pat in priority_patterns:
        if re.search(pat, line, flags=re.IGNORECASE):
            print(line)
            raise SystemExit(0)

for line in reversed(lines):
    if any(re.search(p, line) for p in noise_patterns):
        continue
    print(line)
    raise SystemExit(0)

print(lines[-1])
PY
}

suite_detect_model() {
	if [[ -n "${MODEL:-}" ]]; then
		printf '%s\n' "$MODEL"
		return
	fi
	if [[ -n "${RULESHIELD_TEST_MODEL:-}" ]]; then
		printf '%s\n' "$RULESHIELD_TEST_MODEL"
		return
	fi
	printf '%s\n' "-"
}

suite_detect_provider() {
	if [[ -n "${RULESHIELD_TEST_PROVIDER:-}" ]]; then
		printf '%s\n' "$RULESHIELD_TEST_PROVIDER"
		return
	fi
	if [[ -n "${MODEL_PROFILE_ID:-}" ]]; then
		printf '%s\n' "$MODEL_PROFILE_ID"
		return
	fi
	if [[ -n "${RULESHIELD_TEST_PROFILE_ID:-}" ]]; then
		printf '%s\n' "$RULESHIELD_TEST_PROFILE_ID"
		return
	fi
	printf '%s\n' "-"
}

suite_detect_login_method() {
	if [[ -n "${RULESHIELD_API_KEY:-}" ]]; then
		printf '%s\n' "api_key"
		return
	fi
	if [[ -n "${RULESHIELD_OPENROUTER_API_KEY:-}" ]]; then
		printf '%s\n' "api_key"
		return
	fi
	if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
		printf '%s\n' "api_key"
		return
	fi
	if [[ -n "${OPENAI_API_KEY:-}" ]]; then
		printf '%s\n' "api_key"
		return
	fi
	if [[ -n "${RULESHIELD_TEST_OAUTH:-}" ]]; then
		printf '%s\n' "oauth"
		return
	fi
	printf '%s\n' "unknown"
}

suite_init() {
	SUITE_ID="$1"
	SUITE_STARTED_AT="$(suite_now_iso)"
	RUN_ID="$(python3 - <<'PY'
from datetime import datetime, timezone
dt = datetime.now(timezone.utc)
print(dt.strftime("%Y%m%dT%H%M%S") + f"{dt.microsecond // 1000:03d}Z")
PY
)"

	mkdir -p "$STATUS_LOGS_DIR"
	python3 "$STATUS_STORE" init-run \
		--root "$ROOT_DIR" \
		--run-id "$RUN_ID" \
		--suite-id "$SUITE_ID" \
		--started-at "$SUITE_STARTED_AT"
}

suite_finish() {
	local exit_code="$1"
	python3 "$STATUS_STORE" finalize-run \
		--root "$ROOT_DIR" \
		--run-id "$RUN_ID" \
		--exit-code "$exit_code" \
		--ended-at "$(suite_now_iso)" >/dev/null 2>&1 || true
}

suite_case() {
	local case_id="$1"
	local case_name="$2"
	local script_path="$3"
	shift 3

	local case_started_ms case_ended_ms duration_ms case_started_iso case_ended_iso
	local log_rel log_abs status error_line exit_code
	local env_gateway env_gateway_detected env_model env_provider env_login
	case_started_ms="$(suite_now_ms)"
	case_started_iso="$(suite_now_iso)"
	log_rel="tests/status/data/logs/${RUN_ID}-${case_id}.log"
	log_abs="$ROOT_DIR/$log_rel"
	env_gateway="$(suite_detect_gateway)"
	env_model="$(suite_detect_model)"
	env_provider="$(suite_detect_provider)"
	env_login="$(suite_detect_login_method)"

	set +e
	{
		echo "== ${case_name} =="
		echo "case_id=${case_id}"
		echo "script_path=${script_path}"
		echo "started_at=${case_started_iso}"
		echo "env.gateway=${env_gateway}"
		echo "env.model=${env_model}"
		echo "env.provider=${env_provider}"
		echo "env.login_method=${env_login}"
		echo ""
		"$@"
	} >"$log_abs" 2>&1
	exit_code=$?
	set -e

	if [[ "$env_gateway" == "-" ]]; then
		env_gateway_detected="$(suite_detect_gateway_from_log "$log_abs")"
		if [[ "$env_gateway_detected" != "-" ]]; then
			env_gateway="$env_gateway_detected"
			suite_patch_log_gateway "$log_abs" "$env_gateway"
		fi
	fi

	local fallback_detected=0
	if rg -n "\\[fallback\\]|fallback_" "$log_abs" >/dev/null 2>&1; then
		fallback_detected=1
		# Optional strict mode for CI/debug sessions.
		if [[ "${STRICT_FALLBACK_TRANSPARENCY:-0}" == "1" ]]; then
			exit_code=199
		fi
	fi

	case_ended_ms="$(suite_now_ms)"
	case_ended_iso="$(suite_now_iso)"
	duration_ms=$((case_ended_ms - case_started_ms))

	if [[ "$exit_code" -eq 0 ]]; then
		status="success"
		error_line=""
	else
		status="failed"
		error_line="$(suite_extract_error_line "$log_abs")"
		if [[ "$exit_code" -eq 199 ]]; then
			error_line="fallback_detected_in_test_output"
		fi
	fi

	if [[ "$fallback_detected" -eq 1 && "$exit_code" -eq 0 ]]; then
		echo "[WARN] fallback markers detected in $case_name log"
		echo "  log: $log_rel"
	fi

	python3 "$STATUS_STORE" record-case \
		--root "$ROOT_DIR" \
		--run-id "$RUN_ID" \
		--case-id "$case_id" \
		--name "$case_name" \
		--script-path "$script_path" \
		--status "$status" \
		--exit-code "$exit_code" \
		--started-at "$case_started_iso" \
		--ended-at "$case_ended_iso" \
		--duration-ms "$duration_ms" \
		--log-path "$log_rel" \
		--error "$error_line"

	if [[ "$exit_code" -eq 0 ]]; then
		echo "[OK] $case_name"
	else
		echo "[FAIL] $case_name"
		echo "  last error: ${error_line:-unknown}"
		echo "  log: $log_rel"
		tail -n 30 "$log_abs" || true
	fi

	return "$exit_code"
}
