# ListenKit LLM Integration Contract

This document is the source of truth for external LLM agents and automation integrations. Keep `adapters/agent/listenkit-agent-instructions.md` in sync with the key invariants here.

## Agent Install And Use

If a user asks you to read this GitHub repository and install ListenKit:

1. Clone the repository and enter it.
2. Check whether `yt-dlp` and `ffmpeg` are available. If either is missing, ask the user to install or authorize installing the dependency; do not bypass ListenKit with lower-level pipeline commands.
3. Install the agent instruction summary if you know the user's agent rules/context target:

   ```bash
   cli/install-agent-instructions.sh --target <agent-rules-file-or-dir>
   ```

   On Windows, use `.\cli\install-agent-instructions.ps1 --target <agent-rules-file-or-dir>`.

4. If you do not know the persistent rules/context target, do not guess. Use this exact prompt:

   ```text
   I can install ListenKit instructions, but I need the path to your agent rules/context file or directory. If you only want to use it once, I can skip installation and run ListenKit directly.
   ```

5. If the user needs a pasteable fallback, print the instructions:

   ```bash
   cli/install-agent-instructions.sh --print
   ```

`cli/install-agent-instructions.sh` installs agent instructions only. It does not install Homebrew packages, Python, faster-whisper, Apple Speech assets, or ASR model files.

The corresponding native Windows installer is `.\cli\install-agent-instructions.ps1`; it has the same limited scope.

If a user asks you to read this GitHub repository and use ListenKit once, you may skip persistent installation and run the public entrypoint directly. If the user did not specify `--output`, prefer `work/<safe-source-stem>-transcript.md`; if no stable source stem is available, use `work/transcript.md`. Tell the user when you used ListenKit only for the current task and did not complete persistent agent installation.

## Public Entrypoint

The shared Python CLI is the programmatic source of truth. From the repository
root, an Agent with Python 3.10+ may use the same command on every platform:

```bash
python -m listenkit_cli generate-markdown \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --report-json work/sample-execution.json \
  --auto-init
```

When the host Python environment or `PYTHONPATH` is uncertain, use the platform
dispatcher. It sanitizes inherited Python environment variables and selects a
compatible CLI interpreter:

```bash
cli/listenkit.sh generate-markdown \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --report-json work/sample-execution.json \
  --auto-init
```

On native Windows, use the matching PowerShell dispatcher:

```powershell
.\cli\listenkit.ps1 generate-markdown `
  --url "https://example.com/video" `
  --language Japanese `
  --output work\sample-transcript.md `
  --report-json work\sample-execution.json `
  --auto-init
```

`cli/generate-markdown.sh` and `.\cli\generate-markdown.ps1` remain supported
high-level convenience wrappers. Use `.sh` only on macOS/Linux/WSL and `.ps1`
on native Windows. Git Bash, MSYS2, and Cygwin are native Windows environments,
not WSL; the `.sh` entrypoints fail fast there with exit 64. Use the Python CLI
or PowerShell dispatcher instead. Do not route native Windows through WSL
because WSL has a separate filesystem, runtime path, and dependency environment.
If script execution is restricted, invoke the dispatcher with
`powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\listenkit.ps1 ...`.

The Windows dispatcher removes inherited `PYTHONHOME` and `PYTHONPATH`, uses
UTF-8 I/O, and probes each interpreter by running it. Its automatic order is an
explicit `LISTENKIT_CLI_PYTHON`, the managed runtime, the standard per-user and
Program Files Python 3.14 locations, then `py -3.14`, `python3.14`, and `python`.
The CLI host needs Python 3.10+; creating or repairing the managed ASR runtime
still requires a genuine Python 3.14 interpreter. Direct `python -m listenkit_cli`
also configures its public stdout and stderr streams as UTF-8 on Windows.

For local media, replace `--url <url>` with `--input <path>`.

ListenKit owns source acquisition, subtitle selection, ASR fallback, transcript normalization, and plain transcript rendering behind this entrypoint. External agents should not reimplement or bypass those stages.

Automatic ASR is acceleration-first: Apple Silicon uses a prepared MLX/Metal
runtime, while Windows/Linux NVIDIA systems use managed CUDA. Agents should
leave the engine and device on `auto` and should not force CPU unless the user
requests reproducible CPU execution. `--auto-init` authorizes creation or repair
of a missing core runtime. Initialization and managed-runtime transcription may
download platform acceleration dependencies and the selected local model.
All automation entrypoints are non-interactive by default. A missing runtime
returns an error unless `--auto-init` or `LISTENKIT_AUTO_INIT=1` explicitly
authorizes initialization.

For URL input, the Markdown title defaults to the video's platform title when available. For local input, the title defaults to the source filename. Use `--title` only when the caller needs an explicit override.

## Output Contract

For an output path like:

```text
work/sample-transcript.md
```

The platform public entrypoint produces:

- `work/sample-transcript.md`: human-readable transcript Markdown
- `work/sample-transcript.json`: structured transcript JSON with normalized text, segments, source engine and actual device metadata, fallback diagnostics, locale, and timing status

Downstream agents may consume either artifact:

- Use Markdown when the next step needs a readable transcript.
- Use JSON when the next step needs structured text, segments, timing, or engine metadata.

When `--report-json <path>` is supplied, ListenKit also atomically writes a
separate execution report. It records `status`, elapsed time, artifact paths,
actual engine/device metadata and fallback diagnostics, or a structured error.
The execution report does not contain the full transcript and must not use the
same path as the Markdown or transcript JSON.

For version negotiation, `doctor` reports `listenkit_version`,
`doctor_schema_version`, `transcript_schema_version`, and
`execution_report_schema_version` before platform-specific diagnostics.

## Optional Audio Slice Export

When a downstream workflow has already selected audio time ranges, export the clips through ListenKit:

```bash
cli/export-audio-slices.py \
  --input work/audio/source.m4a \
  --manifest work/source.slices.json \
  --output-dir work/slices \
  --padding-seconds 0.15 \
  --overwrite
```

The manifest is intentionally generic:

```json
{
  "version": 1,
  "slices": [
    {"id": "S01", "start": 4.0, "end": 19.0}
  ]
}
```

ListenKit validates the ranges, applies bounded padding, exports non-empty same-stem `SNN.m4a` files, and prints a JSON report. Use `--allow-overlap` only when the downstream workflow intentionally wants fully padded overlapping clips and can handle the reported overlap. The downstream workflow still owns semantic grouping, labels, learning-note rendering, and application-specific records.

## Downstream Transformations

ListenKit stops at transcript normalization and plain transcript rendering. After the Markdown or JSON exists, downstream agents may transform it into their own products, such as summaries, learning notes, vocabulary lists, review cards, or app-specific records.

Those transformations are outside the ListenKit contract and should not be implemented by bypassing ListenKit internals.

## Do Not Bypass The Entrypoint

In normal integrations, do not call these directly as a shortcut:

- `yt-dlp`
- `ffmpeg`
- `tools/*`
- `cli/extract-subtitles.sh`
- `cli/transcribe-audio.sh`
- `cli/import-audio.sh`
- `cli/render-listening-note.py`

On Windows, the corresponding lower-level `.ps1` commands are subject to the same restriction.

These are dependency, maintenance, or debugging interfaces. Calling them directly can skip ListenKit's subtitle priority, cleanup, ASR fallback, output naming, provenance, or transcript JSON normalization behavior.

Use direct low-level calls only when debugging ListenKit itself or maintaining the pipeline. See `docs/debugging.md`.

`cli/export-audio-slices.py` is the supported exception: downstream workflows may call it after they have selected explicit time ranges.
