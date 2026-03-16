#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WITH_HERMES=0
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10

for arg in "$@"; do
	case "$arg" in
		--hermes|--init-hermes)
			WITH_HERMES=1
			;;
		*)
			echo "Unknown option: $arg" >&2
			echo "Usage: bash scripts/install.sh [--hermes]" >&2
			exit 2
			;;
	esac
done

python_ok() {
	local bin="$1"
	"$bin" -c "import sys; raise SystemExit(0 if sys.version_info >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)" >/dev/null 2>&1
}

python_version() {
	local bin="$1"
	"$bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
}

find_python_bin() {
	local candidates=()
	if [[ -n "${PYTHON_BIN:-}" ]]; then
		candidates+=("$PYTHON_BIN")
	fi
	candidates+=("python3.12" "python3.11" "python3.10" "python3")

	local seen=""
	for candidate in "${candidates[@]}"; do
		if [[ "$seen" == *"|$candidate|"* ]]; then
			continue
		fi
		seen="$seen|$candidate|"
		if ! command -v "$candidate" >/dev/null 2>&1; then
			continue
		fi
		if python_ok "$candidate"; then
			echo "$candidate"
			return 0
		fi
	done

	return 1
}

maybe_install_python_macos() {
	if [[ "$(uname -s)" != "Darwin" ]]; then
		return 1
	fi
	if ! command -v brew >/dev/null 2>&1; then
		echo "ERROR: Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} required, but Homebrew is not installed." >&2
		return 1
	fi

	echo ""
	echo "Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} is required."
	echo "Install Python 3.12 with Homebrew now?"
	if [[ -t 0 ]]; then
		read -r -p "Run: brew install python@3.12 [Y/n] " reply
		if [[ "${reply:-Y}" =~ ^[Nn]$ ]]; then
			return 1
		fi
	else
		return 1
	fi

	brew install python@3.12
	return 0
}

if ! PYTHON_BIN="$(find_python_bin)"; then
	current_py=""
	if command -v python3 >/dev/null 2>&1; then
		current_py="$(python_version python3 2>/dev/null || true)"
	fi

	if [[ -n "$current_py" ]]; then
		echo "Detected python3=${current_py}, but RuleShield requires >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}." >&2
	fi

	if maybe_install_python_macos && PYTHON_BIN="$(find_python_bin)"; then
		echo "Using Python: $PYTHON_BIN ($(python_version "$PYTHON_BIN"))"
	else
		echo "ERROR: No compatible Python found (need >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR})." >&2
		echo "Install one and retry, for example:" >&2
		echo "  brew install python@3.12" >&2
		echo "  python3.12 --version" >&2
		echo "  npm run setup:hermes" >&2
		exit 1
	fi
fi

cd "$ROOT_DIR"

if [[ -d "$VENV_DIR" ]]; then
	if [[ ! -x "$VENV_DIR/bin/python" ]] || ! python_ok "$VENV_DIR/bin/python"; then
		echo "Existing virtualenv is incompatible (needs Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}). Recreating..."
		rm -rf "$VENV_DIR"
	fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
	echo "Creating virtualenv with $PYTHON_BIN ($(python_version "$PYTHON_BIN"))"
	"$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -e .

if [[ "$WITH_HERMES" -eq 1 ]]; then
	"$VENV_DIR/bin/ruleshield" init --hermes
fi

echo ""
echo "Install complete."
echo "RuleShield binary: $VENV_DIR/bin/ruleshield"
echo "Run gateway:       $VENV_DIR/bin/ruleshield start"
