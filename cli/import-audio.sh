#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cli/_common.sh
source "$script_dir/_common.sh"
listenkit_prepare_posix_environment

usage() {
  cat <<'EOF'
Usage:
  cli/import-audio.sh --url <url> --output-dir <dir> [options]
  cli/import-audio.sh --input <path> --output-dir <dir> [options]

Options:
  --url <url>                    yt-dlp-supported video or audio URL
  --input <path>                 Existing local audio file, including Audio Hijack output
  --output-dir <dir>             Destination directory
  --base-name <name>             Output base name without extension
  --format <mp3|m4a|wav|flac>    Output format (default: m4a)
  --quality <value>              yt-dlp audio quality for URL input (default: 0)
  --filename-template <template> yt-dlp output template for URL input
  --write-info-json              Save yt-dlp info JSON next to URL audio
  --write-thumbnail              Save yt-dlp thumbnail next to URL audio
  --playlist                     Download a full playlist instead of one item
  --help                         Show this help

The default URL behavior is single-item mode via yt-dlp --no-playlist.
EOF
}

url=""
input_path=""
output_dir=""
base_name=""
audio_format="m4a"
audio_quality="0"
filename_template=""
playlist_mode="false"
write_info_json="false"
write_thumbnail="false"

validate_base_name() {
  local value="$1"
  if [[ -z "$value" || "$value" == "." || "$value" == ".." || "$value" == *"/"* || "$value" == *"\\"* ]]; then
    echo "--base-name must be a filename stem, not a path: $value" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      [[ $# -ge 2 ]] || { echo "Missing value for --url" >&2; exit 1; }
      url="$2"
      shift 2
      ;;
    --input)
      [[ $# -ge 2 ]] || { echo "Missing value for --input" >&2; exit 1; }
      input_path="$2"
      shift 2
      ;;
    --output-dir)
      [[ $# -ge 2 ]] || { echo "Missing value for --output-dir" >&2; exit 1; }
      output_dir="$2"
      shift 2
      ;;
    --base-name)
      [[ $# -ge 2 ]] || { echo "Missing value for --base-name" >&2; exit 1; }
      base_name="$2"
      shift 2
      ;;
    --format)
      [[ $# -ge 2 ]] || { echo "Missing value for --format" >&2; exit 1; }
      audio_format="$2"
      shift 2
      ;;
    --quality)
      [[ $# -ge 2 ]] || { echo "Missing value for --quality" >&2; exit 1; }
      audio_quality="$2"
      shift 2
      ;;
    --filename-template)
      [[ $# -ge 2 ]] || { echo "Missing value for --filename-template" >&2; exit 1; }
      filename_template="$2"
      shift 2
      ;;
    --write-info-json)
      write_info_json="true"
      shift
      ;;
    --write-thumbnail)
      write_thumbnail="true"
      shift
      ;;
    --playlist)
      playlist_mode="true"
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

if [[ -n "$url" && -n "$input_path" ]]; then
  echo "Use either --url or --input, not both." >&2
  exit 1
fi

if [[ -z "$url" && -z "$input_path" ]]; then
  echo "One of --url or --input is required." >&2
  usage >&2
  exit 1
fi

if [[ -z "$output_dir" ]]; then
  echo "--output-dir is required." >&2
  exit 1
fi

case "$audio_format" in
  mp3|m4a|wav|flac) ;;
  *)
    echo "--format must be one of: mp3, m4a, wav, flac" >&2
    exit 1
    ;;
esac

if [[ -n "$base_name" ]]; then
  validate_base_name "$base_name"
fi

mkdir -p "$output_dir"

if [[ -n "$input_path" ]]; then
  if [[ ! -f "$input_path" ]]; then
    echo "Input audio file not found: $input_path" >&2
    exit 1
  fi

  if [[ -z "$base_name" ]]; then
    base_name="$(basename "$input_path")"
    base_name="${base_name%.*}"
  fi

  output_path="${output_dir%/}/${base_name}.${audio_format}"
  input_abs="$(cd "$(dirname "$input_path")" && pwd -P)/$(basename "$input_path")"
  output_abs="$(cd "$(dirname "$output_path")" && pwd -P)/$(basename "$output_path")"
  if [[ "$input_abs" == "$output_abs" ]]; then
    printf '%s\n' "$output_path"
    exit 0
  fi

  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Missing required command: ffmpeg" >&2
    echo "Install it first, for example: brew install ffmpeg" >&2
    exit 1
  fi

  ffmpeg_log="$(mktemp)"
  if ! ffmpeg -y -i "$input_path" -vn "$output_path" >/dev/null 2>"$ffmpeg_log"; then
    cat "$ffmpeg_log" >&2
    rm -f "$ffmpeg_log"
    exit 1
  fi
  rm -f "$ffmpeg_log"
  printf '%s\n' "$output_path"
  exit 0
fi

missing=()
for dependency in yt-dlp ffmpeg; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    missing+=("$dependency")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Missing required commands: ${missing[*]}" >&2
  echo "Install them first, for example: brew install yt-dlp ffmpeg" >&2
  exit 1
fi

template="${filename_template:-%(title)s.%(ext)s}"
if [[ -n "$base_name" && -z "$filename_template" ]]; then
  template="${base_name}.%(ext)s"
fi

command=(
  yt-dlp
  --quiet
  --no-warnings
  --extract-audio
  --audio-format "$audio_format"
  --audio-quality "$audio_quality"
  --add-metadata
  --embed-metadata
  --no-mtime
  --print
  "after_move:filepath"
  --paths "$output_dir"
  --output "$template"
)

if [[ "$playlist_mode" == "true" ]]; then
  command+=(--yes-playlist)
else
  command+=(--no-playlist)
fi

if [[ "$write_info_json" == "true" ]]; then
  command+=(--write-info-json)
fi

if [[ "$write_thumbnail" == "true" ]]; then
  command+=(--write-thumbnail)
fi

command+=("$url")
"${command[@]}"
