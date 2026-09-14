#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
ROOT_DIR="${SCRIPT_DIR:h}"
APP_NAME="ListenKitAppleSpeechHelper"
SOURCE_FILE="${ROOT_DIR}/SpeechPermissionApp/main.swift"
PLIST_FILE="${ROOT_DIR}/SpeechPermissionApp/Info.plist"
BUILD_DIR="${ROOT_DIR}/.build/helper-app"
APP_DIR="${BUILD_DIR}/${APP_NAME}.app"
CONTENTS_DIR="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
EXECUTABLE_PATH="${MACOS_DIR}/${APP_NAME}"
MODULE_CACHE_DIR="${LISTENKIT_SWIFT_MODULE_CACHE_DIR:-${ROOT_DIR}/.build/module-cache}"

if [[ "${1:-}" == "--clean" ]]; then
  rm -rf "${ROOT_DIR}/.build"
  exit 0
fi

needs_rebuild() {
  if [[ ! -x "${EXECUTABLE_PATH}" ]]; then
    return 0
  fi

  if [[ "${SOURCE_FILE}" -nt "${EXECUTABLE_PATH}" ]]; then
    return 0
  fi

  if [[ "${PLIST_FILE}" -nt "${EXECUTABLE_PATH}" ]]; then
    return 0
  fi

  if [[ "${0}" -nt "${EXECUTABLE_PATH}" ]]; then
    return 0
  fi

  return 1
}

if [[ -d "/Applications/Xcode.app/Contents/Developer" ]]; then
  export DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
fi

mkdir -p "${MACOS_DIR}"
mkdir -p "${MODULE_CACHE_DIR}"
if needs_rebuild; then
  SDK_PATH="$(xcrun --sdk macosx --show-sdk-path)"

  swiftc \
    -sdk "${SDK_PATH}" \
    -target "$(uname -m)-apple-macos26.0" \
    -module-cache-path "${MODULE_CACHE_DIR}" \
    -framework AppKit \
    -framework AVFoundation \
    -framework Speech \
    -o "${EXECUTABLE_PATH}" \
    "${SOURCE_FILE}"

  cp "${PLIST_FILE}" "${CONTENTS_DIR}/Info.plist"
  codesign --force --sign - "${APP_DIR}" >/dev/null 2>&1 || true
fi

echo "${APP_DIR}"
