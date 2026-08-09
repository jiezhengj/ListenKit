#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/init-faster-whisper.sh

Create or reuse ListenKit's local Cache runtime, install faster-whisper,
prepare supported CUDA or MLX acceleration, verify runtime health, and print
the Python executable path.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
venv_dir="${LISTENKIT_FASTER_WHISPER_VENV_DIR:-${HOME}/Library/Caches/ListenKit/venvs/cpython-314}"
python_executable="$venv_dir/bin/python"
requirements_file="$repo_root/requirements-faster-whisper.txt"
import_timeout_seconds="${LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS:-60}"

prepare_acceleration() {
  local candidate="$1"
  PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}" \
    "$candidate" -c \
    'import pathlib; from listenkit_cli.runtime import prepare_runtime_acceleration; prepare_runtime_acceleration(pathlib.Path(__import__("sys").executable))'
}

if [[ ! "$import_timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS must be a positive integer." >&2
  exit 1
fi

if [[ "$venv_dir" == *"/Library/Mobile Documents/"* ]]; then
  echo "Refusing to create ListenKit's native runtime in an iCloud-backed path: $venv_dir" >&2
  echo "Use the default local Cache path or set LISTENKIT_FASTER_WHISPER_VENV_DIR outside iCloud." >&2
  exit 1
fi

python_version_is_supported() {
  local candidate="$1"
  "$candidate" - <<'PY' >/dev/null 2>&1
import sys
major, minor = sys.version_info[:2]
raise SystemExit(0 if (major, minor) == (3, 14) else 1)
PY
}

python_can_import_faster_whisper() {
  local candidate="$1"
  local pid elapsed=0
  [[ -x "$candidate" ]] || return 1
  "$candidate" -c 'import faster_whisper' >/dev/null 2>&1 &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    if (( elapsed >= import_timeout_seconds )); then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 1
    ((elapsed += 1))
  done
  wait "$pid"
}

python_has_expected_faster_whisper_version() {
  local candidate="$1"
  "$candidate" -c 'import importlib.metadata; raise SystemExit(0 if importlib.metadata.version("faster-whisper") == "1.2.1" else 1)' >/dev/null 2>&1
}

select_bootstrap_python() {
  local candidate resolved
  local candidates=()

  if [[ -n "${LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON:-}" ]]; then
    candidates=("$LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON")
  else
    candidates+=(
      "/opt/homebrew/bin/python3.14"
      "/opt/homebrew/opt/python@3.14/bin/python3.14"
      "/usr/local/bin/python3.14"
      "python3.14"
      "python3"
    )
  fi

  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [[ -n "$resolved" ]] || continue
    fi

    if python_version_is_supported "$resolved"; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done

  return 1
}

if [[ -x "$python_executable" ]] && ! python_version_is_supported "$python_executable"; then
  "$python_executable" - <<'PY' >&2
import sys
print(
    "Existing ListenKit runtime uses unsupported Python "
    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}. "
    "Rebuild it with Homebrew Python 3.14."
)
PY
  exit 1
fi

if [[ -x "$python_executable" ]]; then
  if python_can_import_faster_whisper "$python_executable" && python_has_expected_faster_whisper_version "$python_executable"; then
    prepare_acceleration "$python_executable"
    printf '%s\n' "$python_executable"
    exit 0
  else
    import_status=$?
    if [[ "$import_status" -eq 124 ]]; then
      echo "faster-whisper import timed out after ${import_timeout_seconds} seconds: $python_executable" >&2
      exit 1
    fi
  fi
fi

if [[ ! -x "$python_executable" ]]; then
  bootstrap_python="$(select_bootstrap_python || true)"
  if [[ -z "$bootstrap_python" ]]; then
    echo "Python 3.14 is required to create ListenKit's faster-whisper environment. Set LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON=/opt/homebrew/bin/python3.14." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$venv_dir")"
  "$bootstrap_python" -m venv "$venv_dir"
fi

"$python_executable" -m pip install --upgrade pip >&2
"$python_executable" -m pip install -r "$requirements_file" >&2

if python_can_import_faster_whisper "$python_executable" && python_has_expected_faster_whisper_version "$python_executable"; then
  prepare_acceleration "$python_executable"
else
  import_status=$?
  if [[ "$import_status" -eq 124 ]]; then
    echo "Installed faster-whisper, but import timed out after ${import_timeout_seconds} seconds: $python_executable" >&2
  else
    echo "Installed faster-whisper, but it cannot be imported from: $python_executable" >&2
  fi
  exit 1
fi

printf '%s\n' "$python_executable"
