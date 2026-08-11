#!/usr/bin/env bash

# Shared by ListenKit's POSIX entrypoints. Keep this file compatible with the
# Bash 3.2 shipped by macOS.

listenkit_prepare_posix_environment() {
  case "$(uname -s 2>/dev/null || true)" in
    MINGW*|MSYS*|CYGWIN*)
      echo "ListenKit .sh entrypoints are not supported in Git Bash, MSYS2, or Cygwin." >&2
      echo "Use the cross-platform Python CLI: python -m listenkit_cli <command>" >&2
      echo "Or use native PowerShell: powershell -NoProfile -ExecutionPolicy Bypass -File .\\cli\\listenkit.ps1 <command>" >&2
      return 64
      ;;
  esac

  unset PYTHONHOME
  unset PYTHONPATH
  export PYTHONUTF8=1
  export PYTHONIOENCODING=utf-8

  case "$(uname -s 2>/dev/null || true)" in
    Darwin)
      local prefix
      for prefix in /opt/homebrew/bin /usr/local/bin; do
        if [[ -d "$prefix" && ":${PATH:-}:" != *":${prefix}:"* ]]; then
          PATH="${prefix}${PATH:+:${PATH}}"
        fi
      done
      export PATH
      ;;
  esac
}

listenkit_find_cli_python() {
  local candidate
  local resolved

  if [[ -n "${LISTENKIT_CLI_PYTHON:-}" ]]; then
    resolved="$(command -v "$LISTENKIT_CLI_PYTHON" 2>/dev/null || true)"
    if [[ -n "$resolved" ]] && "$resolved" -c \
      'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)' \
      >/dev/null 2>&1; then
      printf '%s\n' "$resolved"
      return 0
    fi
    echo "LISTENKIT_CLI_PYTHON is not a usable Python 3.10+ executable: $LISTENKIT_CLI_PYTHON" >&2
    return 1
  fi

  for candidate in python3.14 python3 python; do
    resolved="$(command -v "$candidate" 2>/dev/null || true)"
    if [[ -z "$resolved" ]]; then
      continue
    fi
    if "$resolved" -c \
      'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)' \
      >/dev/null 2>&1; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done

  echo "Python 3.10 or newer is required to run the ListenKit CLI." >&2
  echo "Install Python or set LISTENKIT_CLI_PYTHON to a compatible executable." >&2
  return 1
}
