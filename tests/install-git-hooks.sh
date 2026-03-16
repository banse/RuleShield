#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

chmod +x .githooks/pre-commit .githooks/pre-push
git config core.hooksPath .githooks

echo "Git hooks installed."
echo "pre-commit -> tests/run-commit-suite.sh"
echo "pre-push   -> tests/run-core-suite.sh"
