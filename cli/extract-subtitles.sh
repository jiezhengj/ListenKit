#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
# shellcheck source=cli/_common.sh
source "$script_dir/_common.sh"
listenkit_prepare_posix_environment

usage() {
  cat <<'EOF'
Usage:
  cli/extract-subtitles.sh --url <url> --locale <bcp47> --output <json>

Options:
  --url <url>       yt-dlp-supported video URL
  --locale <bcp47>  Subtitle language/ASR locale, for example ja-JP or en-US
  --output <json>   Output ListenKit transcript JSON path
  --help            Show this help
EOF
}

url=""
locale=""
output_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      [[ $# -ge 2 ]] || { echo "Missing value for --url" >&2; exit 1; }
      url="$2"
      shift 2
      ;;
    --locale)
      [[ $# -ge 2 ]] || { echo "Missing value for --locale" >&2; exit 1; }
      locale="$2"
      shift 2
      ;;
    --output)
      [[ $# -ge 2 ]] || { echo "Missing value for --output" >&2; exit 1; }
      output_path="$2"
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

if [[ -z "$url" || -z "$locale" || -z "$output_path" ]]; then
  echo "--url, --locale, and --output are required." >&2
  usage >&2
  exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "Missing required command: yt-dlp" >&2
  echo "Install it first, for example: brew install yt-dlp" >&2
  exit 1
fi

converter="$repo_root/tools/subtitles/vtt_to_transcript_json.py"
cli_python="$(listenkit_find_cli_python)"
sub_lang="${locale%%-*}"
sub_lang="$(printf '%s' "$sub_lang" | tr '[:upper:]' '[:lower:]')"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

find_vtt() {
  find "$work_dir" -type f -name '*.vtt' | sort | head -n 1
}

download_subtitles() {
  local kind="$1"
  local flag="$2"
  rm -f "$work_dir"/*.vtt "$work_dir"/*/*.vtt 2>/dev/null || true
  if ! yt-dlp \
    --quiet \
    --no-warnings \
    --skip-download \
    "$flag" \
    --sub-langs "$sub_lang" \
    --sub-format vtt \
    --paths "$work_dir" \
    --output "subtitle.%(ext)s" \
    "$url" >/dev/null 2>/dev/null; then
    return 1
  fi

  local subtitle_path
  subtitle_path="$(find_vtt)"
  [[ -n "$subtitle_path" ]] || return 1

  "$cli_python" "$converter" \
    --vtt "$subtitle_path" \
    --locale "$locale" \
    --subtitle-kind "$kind" \
    --output "$output_path" >/dev/null
}

if download_subtitles "manual" "--write-subs"; then
  printf '%s\n' "$output_path"
  exit 0
fi

if download_subtitles "auto" "--write-auto-subs"; then
  printf '%s\n' "$output_path"
  exit 0
fi

echo "No usable subtitles found for URL and locale: $url ($locale)" >&2
exit 1
