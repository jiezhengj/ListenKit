# Debugging And Maintenance Interfaces

This document is for ListenKit maintainers and integration debugging. It is not
the public contract for external LLM agents.

Normal integrations should call:

```bash
cli/generate-markdown.sh (--url <url>|--input <path>) --language <label> --output <md>
```

On native Windows:

```powershell
.\cli\generate-markdown.ps1 (--url <url>|--input <path>) --language <label> --output <md>
```

The command also writes a same-stem transcript JSON file next to the Markdown
output. External agents should consume that JSON instead of calling the lower
levels directly.

## Lower-Level CLI

The following commands remain available for tests, maintenance, caching, and
pipeline debugging:

- `cli/import-audio.sh`: URL or local media -> local audio file
- `cli/extract-subtitles.sh`: URL subtitles -> transcript JSON
- `cli/transcribe-audio.sh`: local audio file -> transcript JSON
- `cli/render-listening-note.py`: transcript JSON -> transcript Markdown

Native Windows provides matching `.ps1` commands for import, subtitle extraction, transcription, and the public workflow. The platform `doctor` command reports resolved dependencies and runtime health without changing the system. Windows/Linux diagnostics include NVIDIA driver, managed CUDA libraries, devices and selected compute type; macOS diagnostics include architecture, MLX/Metal availability, versions, model cache and automatic engine. CUDA or MLX preparation is performed by initialization or before managed-runtime transcription, never by `doctor`.

Use them only when investigating a specific stage or maintaining ListenKit.

## Backend Helpers

Backend helpers under `tools/` are implementation details:

- `tools/subtitles/vtt_to_transcript_json.py`
- `tools/faster-whisper/transcribe.py`
- `tools/mlx-whisper/transcribe.py`
- `tools/apple-speech-helper/`

Do not call these from external agent workflows. They are wrapped by the CLI
commands above so the public transcript shape stays consistent.

## Raw Downloader Calls

Do not use raw `yt-dlp` subtitle or audio commands as an integration shortcut.
ListenKit's wrappers handle subtitle priority, single-item URL behavior, audio
conversion, output placement, and transcript normalization.

Raw downloader calls are appropriate only while debugging downloader behavior or
writing focused tests for ListenKit internals.
