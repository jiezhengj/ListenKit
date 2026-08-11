#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cli/_common.sh
source "$script_dir/_common.sh"
listenkit_prepare_posix_environment

usage() {
  cat <<'EOF'
Usage:
  cli/install-agent-instructions.sh --target <file-or-directory> [--force]
  cli/install-agent-instructions.sh --target <file-or-directory> --dry-run
  cli/install-agent-instructions.sh --print

Install ListenKit agent instructions into an agent rules/context file.

Options:
  --target <path>  File path to write, or an existing directory where
                   listenkit-agent-instructions.md will be written
  --force          Overwrite an existing target file
  --dry-run        Print the source and resolved target without writing.
                   Only valid with --target
  --print          Print the instruction block to stdout. Mutually exclusive
                   with --target, --force, and --dry-run
  --help           Show this help
EOF
}

target=""
force="false"
dry_run="false"
print_only="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || { echo "Missing value for --target" >&2; exit 1; }
      target="$2"
      shift 2
      ;;
    --force)
      force="true"
      shift
      ;;
    --dry-run)
      dry_run="true"
      shift
      ;;
    --print)
      print_only="true"
      shift
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

repo_root="$(cd "$script_dir/.." && pwd)"
source_file="$repo_root/adapters/agent/listenkit-agent-instructions.md"

if [[ ! -f "$source_file" ]]; then
  echo "ListenKit agent instructions source is missing: $source_file" >&2
  exit 1
fi

if [[ "$print_only" == "true" ]]; then
  if [[ -n "$target" || "$force" == "true" || "$dry_run" == "true" ]]; then
    echo "--print is mutually exclusive with --target, --force, and --dry-run." >&2
    exit 1
  fi
  cat "$source_file"
  exit 0
fi

if [[ -z "$target" ]]; then
  echo "--target is required unless --print is used." >&2
  usage >&2
  exit 1
fi

if [[ "$dry_run" == "true" && -z "$target" ]]; then
  echo "--dry-run requires --target." >&2
  exit 1
fi

resolve_target() {
  local raw_target="$1"
  local parent
  local name

  if [[ -d "$raw_target" ]]; then
    parent="$(cd "$raw_target" && pwd -P)"
    printf '%s\n' "$parent/listenkit-agent-instructions.md"
    return 0
  fi

  parent="$(dirname "$raw_target")"
  name="$(basename "$raw_target")"
  if [[ ! -d "$parent" ]]; then
    echo "Target parent directory does not exist: $parent" >&2
    return 1
  fi
  parent="$(cd "$parent" && pwd -P)"
  printf '%s\n' "$parent/$name"
}

target_file="$(resolve_target "$target")"

if [[ "$dry_run" == "true" ]]; then
  printf 'Source: %s\n' "$source_file"
  printf 'Target: %s\n' "$target_file"
  exit 0
fi

if [[ -e "$target_file" && "$force" != "true" ]]; then
  echo "Target already exists: $target_file" >&2
  echo "Use --force to overwrite it." >&2
  exit 1
fi

target_parent="$(dirname "$target_file")"
target_name="$(basename "$target_file")"
temporary_file="$(mktemp "$target_parent/.${target_name}.XXXXXX")"
cleanup_temporary() {
  rm -f "$temporary_file"
}
trap cleanup_temporary EXIT
cp "$source_file" "$temporary_file"
mv -f "$temporary_file" "$target_file"
trap - EXIT
printf '%s\n' "$target_file"
