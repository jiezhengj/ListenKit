# ListenKit Agent Instructions

Use ListenKit only through the public high-level transcript command during normal integrations.

Choose the entrypoint from the current operating environment:

- macOS/Linux/WSL: `cli/generate-markdown.sh`
- native Windows: `.\cli\generate-markdown.ps1`

Do not send native Windows through WSL; it has a different filesystem and ASR runtime.

## Normal Workflow

For a URL:

```bash
cli/generate-markdown.sh \
  --url "<url>" \
  --language <label> \
  --output <md> \
  --auto-init
```

For a local audio or video file:

```bash
cli/generate-markdown.sh \
  --input <path> \
  --language <label> \
  --output <md> \
  --auto-init
```

Rules:

- Provide exactly one input source: `--url` or `--input`.
- Always provide `--language` and `--output`.
- Use `--auto-init` unless the user explicitly chooses a different backend setup.
- Leave `--engine` and `--device` on their automatic defaults; do not force CPU
  unless the user requests reproducible CPU execution.
- For `--output path/name.md`, expect both `path/name.md` and `path/name.json`.
- If the user does not specify an output path, prefer `work/<safe-source-stem>-transcript.md`; if no stable source stem is available, use `work/transcript.md`.

Do not call these directly as an integration shortcut:

- `yt-dlp`
- `ffmpeg`
- `cli/import-audio.sh`
- `cli/extract-subtitles.sh`
- `cli/transcribe-audio.sh`
- `cli/render-listening-note.py`
- `tools/*`

Those are dependency, maintenance, or debugging interfaces. If `yt-dlp`, `ffmpeg`, Python, or backend initialization is missing, ask the user to install or authorize the missing dependency instead of bypassing `cli/generate-markdown.sh`.

On Windows, the same rule applies to `.\cli\generate-markdown.ps1`; do not bypass it with lower-level `.ps1` commands during normal integrations.

ListenKit stops at plain transcript Markdown and same-stem transcript JSON. Downstream summaries, learning notes, vocabulary lists, cards, or app-specific records are separate transformations after ListenKit output exists.
