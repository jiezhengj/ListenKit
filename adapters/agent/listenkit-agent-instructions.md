# ListenKit Agent Instructions

Use ListenKit only through the public high-level transcript command during normal integrations.

Choose the entrypoint from the current operating environment:

- any platform with a compatible repository-root Python: `python -m listenkit_cli generate-markdown`
- macOS/Linux/WSL dispatcher: `cli/listenkit.sh generate-markdown`
- native Windows dispatcher: `.\cli\listenkit.ps1 generate-markdown`

The existing `cli/generate-markdown.sh` and `.\cli\generate-markdown.ps1`
convenience wrappers remain supported. Do not send native Windows through WSL;
Git Bash is not WSL, and WSL has a different filesystem and ASR runtime. The
`.sh` entrypoints intentionally exit 64 in Git Bash/MSYS2/Cygwin; use the Python
or PowerShell dispatcher there.

## Normal Workflow

For a URL:

```bash
cli/listenkit.sh generate-markdown \
  --url "<url>" \
  --language <label> \
  --output <md> \
  --auto-init
```

For a local audio or video file:

```bash
cli/listenkit.sh generate-markdown \
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
- For automation, add `--report-json path/name.execution.json` and read that
  file for status, artifact paths, actual backend metadata, and errors.
- Do not patch this repository to compensate for a host Agent's PATH, shell, or
  stdout-capture limitation. Use the Python/platform dispatcher and report file.
- On Windows, set `LISTENKIT_CLI_PYTHON` only when automatic discovery cannot
  use the managed runtime or standard Python 3.14 install locations. The CLI
  host accepts Python 3.10+; ASR runtime creation remains pinned to Python 3.14.
- Entry points are non-interactive by default. Use `--auto-init` to authorize
  runtime preparation; never wait on an implicit terminal prompt.
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

If a downstream workflow has already selected explicit time ranges, export clips through the supported supplemental interface instead of calling `ffmpeg` directly:

```bash
cli/export-audio-slices.py \
  --input <audio> \
  --manifest <json> \
  --output-dir <dir> \
  --padding-seconds 0.15
```

Use `--allow-overlap` only when overlapping padded clips are intentional. The downstream workflow remains responsible for deciding what each time range means.
