#!/usr/bin/env bash
set -euo pipefail

STATUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$STATUS_DIR/../.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
URL="http://${HOST}:${PORT}/tests/status/"

cd "$ROOT_DIR"

if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
	echo "Port ${PORT} is already in use."
	echo "Open manually: ${URL}"
	exit 0
fi

echo "Starting static server on ${HOST}:${PORT} ..."
python3 -m http.server "$PORT" --bind "$HOST" >/tmp/ruleshield-test-status-server.log 2>&1 &
SERVER_PID=$!

cleanup() {
	kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 0.4
echo "Opening ${URL}"
open "$URL" >/dev/null 2>&1 || true
echo "Press Ctrl+C to stop the server."

wait "$SERVER_PID"
