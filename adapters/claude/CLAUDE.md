# ListenKit

Use the repository CLI. Do not reimplement the pipeline in prompt text. Prefer
`python -m listenkit_cli generate-markdown` from the repository root. When the
host Python environment is uncertain, use `cli/listenkit.sh generate-markdown`
on macOS/Linux/WSL or `.\cli\listenkit.ps1 generate-markdown` on native Windows.

Normal workflow:

```bash
cli/listenkit.sh generate-markdown \
  --url <url> \
  --language <label> \
  --output <md> \
  --report-json <execution-json> \
  --auto-init
```

The high-level command also accepts `--input <path>` as the single input source. It derives the ASR locale from `--language`. URL titles default to the video's platform title when available; local titles default to the source filename unless optional overrides are provided.

Leave ASR engine and device selection on their automatic defaults. Do not force CPU unless the user explicitly requests reproducible CPU execution.

For `--output path/name.md`, consume `path/name.md` as the readable transcript and `path/name.json` as the structured transcript artifact.
Read the optional execution report for status and backend diagnostics when
stdout capture is unreliable. Do not modify ListenKit to work around Claude
host PATH or shell limitations.

For URL input, the high-level command tries platform subtitles first and still attempts to import local audio. If subtitles are unavailable, it falls back to imported audio plus ASR.

Do not call lower-level import, subtitle extraction, ASR, rendering, raw downloader, or `tools/*` workflows in normal integrations. They are ListenKit debugging and maintenance interfaces only.

Keep the output to transcript JSON or plain transcript Markdown. Do not add learning-note templates, Obsidian-only syntax, Anki cards, or review scheduling unless a downstream project explicitly requests that transformation.

The Windows command accepts the same flags and produces the same output pair. Native Windows must not be routed through WSL because its runtime and paths are separate.
Git Bash/MSYS2/Cygwin are native Windows and the `.sh` entrypoints exit 64 there;
use the Python or PowerShell dispatcher. Prefer `--report-json` over modifying
ListenKit for host PATH, shell, or stdout-capture limitations.
