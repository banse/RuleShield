#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/demo/_helpers.sh"
PYTHON_BIN="${PYTHON_BIN:-$(ruleshield_python_bin)}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-$(ruleshield_config_port 2>/dev/null || printf '8347')}"
LOG_FILE="${LOG_FILE:-/tmp/ruleshield-gateway.log}"
PID_FILE="${PID_FILE:-/tmp/ruleshield-gateway.pid}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <start|stop|restart|status|logs|kill-all>

Environment overrides:
  HOST, PORT, PYTHON_BIN, LOG_FILE, PID_FILE
EOF
}

kill_by_port() {
  local pids
  pids="$(lsof -ti "tcp:${PORT}" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 0.5
    pids="$(lsof -ti "tcp:${PORT}" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}

kill_matching_processes() {
  local pattern="$1"
  local pids
  pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return
  fi
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  sleep 0.5
  pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2086
    kill -9 $pids 2>/dev/null || true
  fi
}

kill_stale_ruleshield_local() {
  kill_matching_processes "uvicorn ruleshield.proxy:app --host ${HOST} --port ${PORT}"
  kill_matching_processes "ruleshield start --port ${PORT}"
}

kill_all_ruleshield_gateways() {
  kill_matching_processes "uvicorn ruleshield.proxy:app"
  kill_matching_processes "ruleshield start"
  kill_matching_processes "python -m uvicorn ruleshield.proxy:app"
  # Also clear common default/listening ports if lingering.
  for p in 8337 8338 8339 8347 8348 8349; do
    PORT="$p" kill_by_port
  done
}

start_gateway() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "ERROR: python binary not found: $PYTHON_BIN" >&2
    exit 1
  fi
  kill_all_ruleshield_gateways
  kill_by_port
  nohup env PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" -m uvicorn ruleshield.proxy:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    --app-dir "$ROOT_DIR" >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"

  local tries=0
  until curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [[ $tries -gt 25 ]]; then
      echo "ERROR: gateway did not become healthy. Check $LOG_FILE" >&2
      if [[ -f "$PID_FILE" ]]; then
        local pid
        pid="$(cat "$PID_FILE" 2>/dev/null || true)"
        if [[ -n "$pid" ]] && ! ps -p "$pid" >/dev/null 2>&1; then
          echo "ERROR: gateway process exited early (PID $pid)." >&2
        fi
      fi
      exit 1
    fi
    sleep 0.2
  done
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  echo "Gateway running on http://${HOST}:${PORT}"
  echo "Gateway startup complete. pid=${pid:-unknown} log=${LOG_FILE}"
}

stop_gateway() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]]; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  kill_stale_ruleshield_local
  kill_by_port
  echo "Gateway stopped."
}

status_gateway() {
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    echo "status=running url=http://${HOST}:${PORT}"
    lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN || true
  else
    echo "status=stopped url=http://${HOST}:${PORT}"
  fi
}

show_logs() {
  tail -n 120 "$LOG_FILE"
}

cmd="${1:-}"
case "$cmd" in
  start) start_gateway ;;
  stop) stop_gateway ;;
  restart) stop_gateway; start_gateway ;;
  status) status_gateway ;;
  logs) show_logs ;;
  kill-all) kill_all_ruleshield_gateways; echo "All RuleShield gateway processes terminated." ;;
  *) usage; exit 1 ;;
esac
