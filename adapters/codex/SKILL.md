---
name: generate-markdown
description: Generate transcript Markdown and same-stem transcript JSON from a URL or local audio/video file.
---

# Generate Markdown

Use this skill when the user wants ListenKit to produce transcript artifacts from one input: a network audio/video URL or a local audio/video file.

## Workflow

1. Confirm exactly one input source: URL or local media path.
2. Choose the output Markdown path and user-facing language label.
3. Run the shared programmatic entrypoint once: `python -m listenkit_cli generate-markdown` from the repository root. If the host Python environment is uncertain, use `cli/listenkit.sh generate-markdown` on macOS/Linux/WSL or `.\cli\listenkit.ps1 generate-markdown` on native Windows.

Git Bash, MSYS2, and Cygwin are native Windows rather than WSL. The `.sh`
entrypoints exit 64 there; use the Python or PowerShell dispatcher and consume
`--report-json` when stdout capture is unreliable.

The wrapper derives the ASR locale from `--language`. For URL input, it defaults the Markdown title to the video's platform title when available; for local input, it derives the title from the source filename. Use optional `--locale` or `--title` only when the user needs an override.

For `--output work/name.md`, the wrapper writes both `work/name.md` and `work/name.json`. Use the Markdown for readable transcript output and the JSON for downstream structured transformations.

For URL input, the wrapper tries platform subtitles first. If subtitles are usable, it renders the transcript from subtitles and skips ASR, while still trying to import local audio for listening. If subtitles are unavailable, it falls back to imported audio plus ASR.

When a downstream workflow has already selected explicit time ranges, use `cli/export-audio-slices.py --input <audio> --manifest <json> --output-dir <dir>` to export clips. ListenKit validates and exports ranges; the downstream workflow remains responsible for semantic grouping. Add `--allow-overlap` only when overlapping padded clips are intentional.

## Rules

- Keep ListenKit output to transcript Markdown and the same-stem transcript JSON artifact.
- Use `cli/export-audio-slices.py` instead of raw `ffmpeg` when a downstream workflow requests clips for explicit time ranges.
- Leave ASR engine and device selection on their automatic defaults; do not force CPU unless the user explicitly requests reproducible CPU execution.
- Do not expose existing-audio, existing-transcript-JSON, subtitle extraction, ASR, import, rendering, raw downloader, or `tools/*` workflows through this high-level skill; those belong to ListenKit debugging and maintenance only.
- Do not add learning-note templates, Obsidian frontmatter, wikilinks, Anki cards, or review scheduling unless a downstream project explicitly asks.
- Keep language-learning analysis outside this generic transcription skill.
- Respect copyright. Do not help redistribute copyrighted transcripts or audio.

## CLI Examples

URL input:

```bash
cli/listenkit.sh generate-markdown \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --report-json work/sample-execution.json \
  --auto-init
```

Local media input:

```bash
cli/listenkit.sh generate-markdown \
  --input ~/Desktop/recording.wav \
  --language English \
  --output work/recording-transcript.md \
  --report-json work/recording-execution.json \
  --auto-init
```

Native Windows uses the same options with PowerShell syntax:

```powershell
.\cli\listenkit.ps1 generate-markdown `
  --input "C:\Media\recording.wav" `
  --language English `
  --output work\recording-transcript.md `
  --report-json work\recording-execution.json `
  --auto-init
```
