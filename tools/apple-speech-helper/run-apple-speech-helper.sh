#!/bin/zsh
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The Apple Speech helper is available only on macOS." >&2
  exit 1
fi

SCRIPT_DIR="${0:A:h}"

APP_DIR="$(zsh "${SCRIPT_DIR}/scripts/build-helper-app.sh")"
if [[ ! -d "${APP_DIR}" ]]; then
  echo "Failed to build ListenKitAppleSpeechHelper.app" >&2
  exit 1
fi

APP_EXECUTABLE="${APP_DIR}/Contents/MacOS/ListenKitAppleSpeechHelper"
if [[ ! -x "${APP_EXECUTABLE}" ]]; then
  echo "ListenKitAppleSpeechHelper executable is missing: ${APP_EXECUTABLE}" >&2
  exit 1
fi

ARGS=()
while (( $# > 0 )); do
  case "$1" in
    --audio-path|--locale)
      option="$1"
      shift
      if (( $# == 0 )); then
        echo "Missing value for ${option}." >&2
        exit 1
      fi
      ARGS+=("${option}" "$1")
      ;;
    --json)
      ;;
    --*)
      echo "Unsupported argument for Apple Speech helper: $1" >&2
      exit 1
      ;;
    *)
      if [[ " ${ARGS[*]} " != *" --audio-path "* ]]; then
        ARGS+=("--audio-path" "$1")
      else
        echo "Unexpected positional argument: $1" >&2
        exit 1
      fi
      ;;
  esac
  shift
done

if [[ " ${ARGS[*]} " != *" --audio-path "* ]]; then
  echo "--audio-path is required." >&2
  exit 1
fi

if [[ " ${ARGS[*]} " != *" --locale "* ]]; then
  ARGS+=("--locale" "ja-JP")
fi

NORMALIZED_ARGS=()
index=1
while (( index <= ${#ARGS[@]} )); do
  argument="${ARGS[index]}"
  if [[ "${argument}" == "--audio-path" ]]; then
    (( index += 1 ))
    audio_path="${ARGS[index]}"
    if [[ "${audio_path}" != /* ]]; then
      audio_path="${PWD:A}/${audio_path}"
    fi
    NORMALIZED_ARGS+=("--audio-path" "${audio_path}")
  else
    NORMALIZED_ARGS+=("${argument}")
  fi
  (( index += 1 ))
done

TEMP_ROOT="${TMPDIR:-/tmp}"
OUTPUT_JSON="$(mktemp "${TEMP_ROOT%/}/listenkit-apple-speech-output.XXXXXX")"
OPEN_STDOUT_LOG="$(mktemp "${TEMP_ROOT%/}/listenkit-apple-speech-open-stdout.XXXXXX")"
OPEN_STDERR_LOG="$(mktemp "${TEMP_ROOT%/}/listenkit-apple-speech-open-stderr.XXXXXX")"
cleanup() {
  rm -f "${OUTPUT_JSON}"
  rm -f "${OPEN_STDOUT_LOG}"
  rm -f "${OPEN_STDERR_LOG}"
}
trap cleanup EXIT

open_exit=0
if /usr/bin/open -W -n "${APP_DIR}" --args "${NORMALIZED_ARGS[@]}" --output-path "${OUTPUT_JSON}" >"${OPEN_STDOUT_LOG}" 2>"${OPEN_STDERR_LOG}"; then
  open_exit=0
else
  open_exit=$?
fi

if [[ ! -s "${OUTPUT_JSON}" ]]; then
  echo "Apple Speech helper finished without producing JSON output." >&2
  if (( open_exit != 0 )); then
    echo "App launch via open failed with exit ${open_exit}: $(<"${OPEN_STDERR_LOG}")" >&2
  fi
  echo "If this is a new session, allow launching the local Apple Speech helper app when prompted." >&2
  exit 1
fi

if (( open_exit != 0 )); then
  cat "${OUTPUT_JSON}" >&2
  exit "${open_exit}"
fi

cat "${OUTPUT_JSON}"
