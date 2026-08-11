#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
# shellcheck source=cli/_common.sh
source "$script_dir/_common.sh"
listenkit_prepare_posix_environment
runtime_dir="${LISTENKIT_FASTER_WHISPER_VENV_DIR:-${HOME}/Library/Caches/ListenKit/venvs/cpython-314}"
python_executable="${LISTENKIT_FASTER_WHISPER_VENV_PYTHON:-${runtime_dir}/bin/python}"
import_timeout_seconds="${LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS:-60}"

usage() {
  cat <<'EOF'
Usage:
  cli/check-runtime.sh [--python <path>]

Validate ListenKit's Python 3.14 faster-whisper runtime without modifying it.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      [[ $# -ge 2 ]] || { echo "Missing value for --python" >&2; exit 1; }
      python_executable="$2"
      shift 2
      ;;
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

if [[ ! "$import_timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS must be a positive integer." >&2
  exit 1
fi

if [[ ! -x "$python_executable" ]]; then
  echo "ListenKit runtime is missing: $python_executable" >&2
  echo "Repair: $repo_root/cli/init-faster-whisper.sh" >&2
  exit 1
fi

runtime_metadata="$("$python_executable" - <<'PY'
import importlib.metadata
import sys

if sys.version_info[:2] != (3, 14):
    raise SystemExit(
        f"ListenKit requires Python 3.14, got {sys.version.split()[0]} at {sys.executable}"
    )
print(f"python_executable={sys.executable}")
print(f"python_version={sys.version.split()[0]}")
print(f"abi_tag={sys.implementation.cache_tag}")
print(f"runtime_prefix={sys.prefix}")
try:
    print(f"faster_whisper_version={importlib.metadata.version('faster-whisper')}")
except importlib.metadata.PackageNotFoundError as exc:
    raise SystemExit("faster-whisper is not installed in the selected runtime") from exc
PY
)" || {
  echo "ListenKit runtime metadata check failed: $python_executable" >&2
  echo "Repair: $repo_root/cli/init-faster-whisper.sh" >&2
  exit 1
}

installed_version="$(printf '%s\n' "$runtime_metadata" | awk -F= '$1 == "faster_whisper_version" {print $2}')"
runtime_prefix="$(printf '%s\n' "$runtime_metadata" | awk -F= '$1 == "runtime_prefix" {sub(/^[^=]*=/, ""); print}')"
if [[ "$runtime_prefix" == *"/Library/Mobile Documents/"* ]]; then
  echo "ListenKit native runtime cannot use an iCloud-backed path: $runtime_prefix" >&2
  echo "Repair: $repo_root/cli/init-faster-whisper.sh" >&2
  exit 1
fi
if [[ "$installed_version" != "1.2.1" ]]; then
  echo "ListenKit requires faster-whisper 1.2.1, got ${installed_version:-unknown}: $python_executable" >&2
  echo "Repair: $repo_root/cli/init-faster-whisper.sh" >&2
  exit 1
fi

"$python_executable" -c 'import faster_whisper' >/dev/null 2>&1 &
import_pid=$!
elapsed=0
while kill -0 "$import_pid" 2>/dev/null; do
  if (( elapsed >= import_timeout_seconds )); then
    kill "$import_pid" 2>/dev/null || true
    wait "$import_pid" 2>/dev/null || true
    echo "faster-whisper import timed out after ${import_timeout_seconds} seconds: $python_executable" >&2
    exit 1
  fi
  sleep 1
  ((elapsed += 1))
done
if ! wait "$import_pid"; then
  echo "faster-whisper cannot be imported from: $python_executable" >&2
  echo "Repair: $repo_root/cli/init-faster-whisper.sh" >&2
  exit 1
fi

printf '%s\n' "$runtime_metadata"
printf 'import_health=ok\n'
