#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/tests/.local"
OUT_FILE="$OUT_DIR/imported_keys.env"

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

read_secret() {
	local prompt="$1"
	local value=""
	read -r -s -p "$prompt" value
	echo ""
	printf '%s' "$value"
}

OPENROUTER_KEY="$(read_secret 'OpenRouter API key (required, hidden): ')"
if [[ -z "$OPENROUTER_KEY" ]]; then
	echo "ERROR: OpenRouter API key is required." >&2
	exit 1
fi

OPENAI_KEY="${OPENAI_API_KEY:-}"
if [[ -z "$OPENAI_KEY" ]]; then
	OPENAI_KEY="$(read_secret 'OpenAI API key (optional, hidden): ')"
fi

{
	echo "# Imported test keys for local story tests"
	echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
	# nosec
	echo "OPENROUTER_API_KEY=$OPENROUTER_KEY"
	if [[ -n "$OPENAI_KEY" ]]; then
		# nosec
		echo "OPENAI_API_KEY=$OPENAI_KEY"
	fi
} >"$OUT_FILE"

chmod 600 "$OUT_FILE"
echo "Saved imported keys: $OUT_FILE"
