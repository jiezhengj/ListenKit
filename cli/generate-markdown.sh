#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  cli/generate-markdown.sh (--url <url>|--input <path>) --language <label> --output <md> [options]

Core:
  --url <url>                    yt-dlp-supported video or audio URL
  --input <path>                 Existing local audio or video file
  --language <label>             Human-readable language label, for example Japanese or English
  --output <md>                  Output Markdown path

Optional overrides:
  --title <title>                Optional Markdown title override. URL defaults to platform title when available; local input defaults to source filename
  --locale <bcp47>               Optional ASR locale override. Defaults from --language

ASR options:
  --engine <name>                auto, faster-whisper, mlx, or apple. Defaults to auto
  --auto-init                    Allow managed ASR runtime initialization when needed

Import options:
  --format <mp3|m4a|wav|flac>    Imported audio format. Defaults to m4a

URL-only advanced options:
  --quality <value>              URL-only yt-dlp audio quality. Defaults to 0
  --filename-template <template> URL-only yt-dlp output template
  --write-info-json              URL-only: save yt-dlp info JSON next to URL audio
  --write-thumbnail              URL-only: save yt-dlp thumbnail next to URL audio

Other:
  --help                         Show this help

This is the recommended high-level entrypoint. Existing audio and existing
transcript JSON workflows are available through the lower-level CLI commands.
EOF
}

url=""
input_path=""
title=""
language=""
output_path=""
locale=""
engine="auto"
auto_init="false"
audio_format="m4a"
audio_quality="0"
quality_was_set="false"
filename_template=""
write_info_json="false"
write_thumbnail="false"

locale_from_language() {
  case "$1" in
    Japanese|japanese|日本語|日语|日語|ja|ja-JP) printf '%s\n' "ja-JP" ;;
    English|english|英語|英语|en|en-US) printf '%s\n' "en-US" ;;
    Chinese|chinese|中文|汉语|漢語|zh|zh-CN) printf '%s\n' "zh-CN" ;;
    Korean|korean|한국어|韓語|韩语|ko|ko-KR) printf '%s\n' "ko-KR" ;;
    *) return 1 ;;
  esac
}

supported_languages_message() {
  cat <<'EOF'
Supported language values include:
  Japanese, 日本語, 日语, ja, ja-JP
  English, 英語, 英语, en, en-US
  Chinese, 中文, 汉语, 漢語, zh, zh-CN
  Korean, 한국어, 韓語, 韩语, ko, ko-KR

Pass --locale <bcp47> to override the derived ASR locale.
EOF
}

stem_from_path() {
  local value="$1"
  local filename
  filename="$(basename "$value")"
  filename="${filename%%\?*}"
  filename="${filename%%#*}"
  local stem="${filename%.*}"
  if [[ -z "$stem" || "$stem" == "." || "$stem" == ".." ]]; then
    return 1
  fi
  printf '%s\n' "$stem"
}

title_from_url() {
  local value="$1"
  command -v yt-dlp >/dev/null 2>&1 || return 1

  local title_file
  title_file="$(mktemp)"
  if yt-dlp \
    --quiet \
    --no-warnings \
    --skip-download \
    --no-playlist \
    --print title \
    "$value" >"$title_file" 2>/dev/null; then
    local first_line
    IFS= read -r first_line <"$title_file" || first_line=""
    rm -f "$title_file"
    if [[ -n "$first_line" ]]; then
      printf '%s\n' "$first_line"
      return 0
    fi
  fi
  rm -f "$title_file"
  return 1
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
    --title)
      [[ $# -ge 2 ]] || { echo "Missing value for --title" >&2; exit 1; }
      title="$2"
      shift 2
      ;;
    --language)
      [[ $# -ge 2 ]] || { echo "Missing value for --language" >&2; exit 1; }
      language="$2"
      shift 2
      ;;
    --output)
      [[ $# -ge 2 ]] || { echo "Missing value for --output" >&2; exit 1; }
      output_path="$2"
      shift 2
      ;;
    --locale)
      [[ $# -ge 2 ]] || { echo "Missing value for --locale" >&2; exit 1; }
      locale="$2"
      shift 2
      ;;
    --engine)
      [[ $# -ge 2 ]] || { echo "Missing value for --engine" >&2; exit 1; }
      engine="$2"
      shift 2
      ;;
    --auto-init)
      auto_init="true"
      shift
      ;;
    --format)
      [[ $# -ge 2 ]] || { echo "Missing value for --format" >&2; exit 1; }
      audio_format="$2"
      shift 2
      ;;
    --quality)
      [[ $# -ge 2 ]] || { echo "Missing value for --quality" >&2; exit 1; }
      audio_quality="$2"
      quality_was_set="true"
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
    --audio-path|--transcript-json|--source-ref)
      echo "$1 is not supported by cli/generate-markdown.sh. Use lower-level CLI commands for existing audio or transcript JSON workflows." >&2
      exit 1
      ;;
    --base-name)
      echo "--base-name is not supported by cli/generate-markdown.sh. Use cli/import-audio.sh for advanced import naming workflows." >&2
      exit 1
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

input_count=0
for value in "$url" "$input_path"; do
  if [[ -n "$value" ]]; then
    input_count=$((input_count + 1))
  fi
done

if [[ "$input_count" -ne 1 ]]; then
  echo "Exactly one of --url or --input is required." >&2
  usage >&2
  exit 1
fi

if [[ -z "$language" || -z "$output_path" ]]; then
  echo "--language and --output are required." >&2
  usage >&2
  exit 1
fi

if [[ -z "$url" ]]; then
  if [[ "$quality_was_set" == "true" || -n "$filename_template" || "$write_info_json" == "true" || "$write_thumbnail" == "true" ]]; then
    echo "--quality, --filename-template, --write-info-json, and --write-thumbnail are only valid with --url." >&2
    exit 1
  fi
fi

if [[ -z "$locale" ]]; then
  if ! locale="$(locale_from_language "$language")"; then
    echo "Cannot derive ASR locale from --language: $language" >&2
    supported_languages_message >&2
    exit 1
  fi
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
import_script="$repo_root/cli/import-audio.sh"
subtitle_script="$repo_root/cli/extract-subtitles.sh"
transcribe_script="$repo_root/cli/transcribe-audio.sh"
render_script="$repo_root/cli/render-listening-note.py"

output_dir="$(dirname "$output_path")"
mkdir -p "$output_dir"

output_file="$(basename "$output_path")"
output_stem="${output_file%.*}"

transcript_json="${output_dir%/}/${output_stem}.json"
source_ref="${url:-$input_path}"
subtitle_available="false"
url_title=""

if [[ -n "$url" && -z "$title" ]]; then
  url_title="$(title_from_url "$url" || true)"
fi

if [[ -n "$url" ]]; then
  subtitle_error_log="$(mktemp)"
  if "$subtitle_script" --url "$url" --locale "$locale" --output "$transcript_json" >/dev/null 2>"$subtitle_error_log"; then
    subtitle_available="true"
  fi
  rm -f "$subtitle_error_log"
fi

import_command=(
  "$import_script"
  --output-dir "${output_dir%/}/audio"
  --base-name "$output_stem"
  --format "$audio_format"
)

if [[ -n "$url" ]]; then
  import_command+=(--url "$url" --quality "$audio_quality")
  if [[ -n "$filename_template" ]]; then
    import_command+=(--filename-template "$filename_template")
  fi
  if [[ "$write_info_json" == "true" ]]; then
    import_command+=(--write-info-json)
  fi
  if [[ "$write_thumbnail" == "true" ]]; then
    import_command+=(--write-thumbnail)
  fi
else
  import_command+=(--input "$input_path")
fi

if ! audio_path="$("${import_command[@]}")"; then
  if [[ -n "$url" ]]; then
    if [[ "$subtitle_available" == "true" ]]; then
      cat >&2 <<EOF

Audio import failed after subtitles were extracted.
Markdown was generated from subtitles, but no local listening audio was created.

To create listening audio, record the source with Audio Hijack or another local recorder, then rerun with:
  cli/generate-markdown.sh --input <recording> --language "$language" --output "$output_path"

See docs/audio-hijack.md.
EOF
      if [[ -z "$title" ]]; then
        title="${url_title:-$output_stem}"
      fi
      "$render_script" \
        --source-ref "$source_ref" \
        --transcript-json "$transcript_json" \
        --title "$title" \
        --language "$language" \
        --output "$output_path"
      exit 0
    fi

    cat >&2 <<EOF

Audio import failed. See the error above from cli/import-audio.sh.

If this URL cannot be downloaded by yt-dlp, record the source audio with Audio Hijack or another local recorder, then rerun:
  cli/generate-markdown.sh --input <recording> --language "$language" --output "$output_path"

See docs/audio-hijack.md.
EOF
  fi
  exit 1
fi
if [[ "$audio_path" == *$'\n'* ]]; then
  echo "Import produced multiple audio paths; generate-markdown expects a single input." >&2
  exit 1
fi

if [[ -z "$title" ]]; then
  if [[ -n "$url_title" ]]; then
    title="$url_title"
  elif [[ -n "$input_path" ]] && title="$(stem_from_path "$input_path")"; then
    :
  elif title="$(stem_from_path "$audio_path")"; then
    :
  else
    title="$output_stem"
  fi
fi

if [[ "$subtitle_available" != "true" ]]; then
  transcribe_command=(
    "$transcribe_script"
    --audio-path "$audio_path"
    --locale "$locale"
    --engine "$engine"
    --output "$transcript_json"
  )
  if [[ "$auto_init" == "true" ]]; then
    transcribe_command+=(--auto-init)
  fi
  "${transcribe_command[@]}" >/dev/null
fi

"$render_script" \
  --source-ref "$source_ref" \
  --transcript-json "$transcript_json" \
  --title "$title" \
  --language "$language" \
  --output "$output_path"
