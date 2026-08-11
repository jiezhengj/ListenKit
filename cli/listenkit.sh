#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
# shellcheck source=cli/_common.sh
source "$script_dir/_common.sh"
listenkit_prepare_posix_environment

python_executable="$(listenkit_find_cli_python)"
export PYTHONPATH="$repo_root"
exec "$python_executable" -m listenkit_cli "$@"
