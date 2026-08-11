# ListenKit

Local-first multilingual audio and video transcription toolchain. ListenKit turns URL or local media input into plain transcript Markdown plus same-stem transcript JSON.

[简体中文](README.zh-CN.md) | English

## Quick Try

macOS/Linux/WSL:

```bash
git clone https://github.com/feiyanqiqiao/ListenKit.git
cd ListenKit
# macOS/Homebrew path. Linux users should install yt-dlp and ffmpeg with their package manager.
brew install yt-dlp ffmpeg
cli/listenkit.sh generate-markdown --help
cli/listenkit.sh generate-markdown --url "https://example.com/video" --language Japanese --output work/sample.md --report-json work/sample.execution.json --auto-init
```

Windows 10/11 PowerShell:

```powershell
winget install Python.Python.3.14
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg
.\cli\listenkit.ps1 generate-markdown --help
.\cli\listenkit.ps1 generate-markdown --url "https://example.com/video" --language Japanese --output work\sample.md --report-json work\sample.execution.json --auto-init
```

The Windows workflow is native: it does not require Bash, WSL, Git Bash, or
MSYS2. POSIX `.sh` entrypoints intentionally exit 64 in Git Bash/MSYS2/Cygwin;
use the Python or PowerShell dispatcher. If script execution is restricted, run
`powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\listenkit.ps1 generate-markdown ...`.

ASR defaults to acceleration-first execution. On Apple Silicon macOS, ListenKit
prepares MLX Whisper and selects the Metal GPU. On Windows and Linux, it detects
an NVIDIA GPU, prepares CUDA 12 cuBLAS and cuDNN 9 inside ListenKit's isolated
runtime, and tries supported CUDA precisions before a visible CPU INT8 fallback.
Intel Macs use CTranslate2's Apple Accelerate CPU backend. Use `--device cpu`
for reproducible CPU-only execution, `--device cuda` to require CUDA without CPU
fallback, or `--engine mlx` to require MLX/Metal on Apple Silicon.

This writes:

```text
work/sample.md
work/sample.json
work/sample.execution.json
```

The execution report is optional. It records success or failure, elapsed time,
artifact paths, and actual ASR backend metadata without duplicating transcript
text. Agents may also call `python -m listenkit_cli generate-markdown` directly
from the repository root on every platform.

## Install For Your AI Agent

If you know your agent rules or context path:

```bash
cli/install-agent-instructions.sh --target <your-agent-rules-file-or-dir>
```

On Windows, use `.\cli\install-agent-instructions.ps1` with the same arguments.

If you do not know the target path yet, use the `--print` fallback described in `LLM_INTEGRATION.md`.

## Documentation

- `LLM_INTEGRATION.md`: AI/agent install and usage contract
- `docs/install.md`: dependencies, backend setup, and troubleshooting
- `docs/backends.md`: ASR engine and acceleration policy
- `docs/debugging.md`: lower-level maintenance and debugging interfaces
- `docs/output-format.md`: transcript Markdown and JSON output shape
- `cli/init-faster-whisper.sh`: managed ASR runtime initializer for macOS/Linux/WSL
- `cli/check-runtime.sh`: read-only Python 3.14 and faster-whisper health check for Bash environments
- `cli/listenkit.sh`: macOS/Linux/WSL unified dispatcher with Agent environment isolation
- `cli/doctor.sh`: read-only macOS/Linux/WSL platform and dependency diagnosis
- `cli/init-faster-whisper.ps1`: native Windows managed ASR runtime initializer
- `cli/check-runtime.ps1`: native Windows runtime health check
- `cli/generate-markdown.ps1`: native Windows public transcript entrypoint
- `cli/doctor.ps1`: read-only Windows platform and dependency diagnosis

## What It Does

```text
URL or local media
  -> python -m listenkit_cli generate-markdown (cross-platform)
     or cli/listenkit.sh generate-markdown (macOS/Linux/WSL)
     or cli\listenkit.ps1 generate-markdown (native Windows)
  -> transcript Markdown + same-stem transcript JSON
```

Inputs:

- yt-dlp-supported URLs
- Local audio, video, or media files
- Audio Hijack recordings saved as local files

Output:

- Plain Markdown with source metadata and transcript text
- Same-stem transcript JSON with normalized text, segments, engine metadata, locale, and timing status
- Optional audio clips exported from a downstream time-range manifest through `cli/export-audio-slices.py`

## What It Is Not

- Not tied to Codex. Codex is only one adapter.
- Not tied to Japanese. Japanese, English, Chinese, and Korean labels are supported by the public CLI.
- Not a note-taking, language-learning, Obsidian, Anki, or spaced-repetition system.
- Not a source of copyrighted audio or transcripts.

## Adapters

- Generic agent instructions: `adapters/agent/listenkit-agent-instructions.md`
- Codex: `adapters/codex/SKILL.md`
- Claude: `adapters/claude/CLAUDE.md`
- Cursor: `adapters/cursor/foreign-listening.md`

Adapters should call the shared `generate-markdown` command for normal use,
then consume either the generated Markdown or same-stem JSON. Use
`--report-json` when file-based status is more reliable than captured stdout.
When a downstream workflow has already selected time ranges, call
`cli/export-audio-slices.py` instead of invoking `ffmpeg` directly. Adapters
should not reimplement import, subtitle extraction, transcription, rendering,
or downstream note systems.

The Python CLI and platform dispatchers preserve the same parameters and output contract.

## Privacy and Copyright

The default transcription route is local: MLX Whisper on a ready Apple Silicon
Mac and faster-whisper elsewhere. The first run may download model files. Apple
Speech is available as an optional local macOS backend. Downstream tools that
consume transcript text may send it to the model provider you use. Only process
material you have the right to use.

See `PRIVACY_AND_COPYRIGHT.md`.
