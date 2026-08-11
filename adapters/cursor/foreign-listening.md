# Cursor Rule: ListenKit

When working in this repository, use the CLI scripts as the source of truth:

- `python -m listenkit_cli generate-markdown` as the cross-platform programmatic entrypoint
- `cli/listenkit.sh generate-markdown` when the macOS/Linux/WSL host Python environment is uncertain
- `.\cli\listenkit.ps1 generate-markdown` for the same dispatcher workflow on native Windows
- `generate-markdown --output path/name.md` also writes `path/name.json` for structured transcript consumption
- URL workflows try platform subtitles first while still importing local listening audio
- lower-level import, subtitle extraction, ASR, rendering, raw downloader, and `tools/*` workflows are debugging and maintenance interfaces only

Do not duplicate business logic inside editor rules.

Use `--report-json` when the calling host needs file-based execution status.
Select `.sh` for macOS/Linux/WSL and `.ps1` for native Windows; Git Bash is not
WSL, and WSL must not be used as a transparent wrapper for Windows paths. The
`.sh` entrypoints exit 64 in Git Bash/MSYS2/Cygwin; use Python or PowerShell.

Leave ASR engine and device selection on their automatic defaults. Do not force CPU unless the user explicitly requests reproducible CPU execution.

Expected Markdown output contains:

- `Source`
- `Transcript`

Keep this adapter focused on transcript generation. Do not add learning-note templates, Obsidian, Anki, or review-system structures unless a downstream project asks for that transformation.
