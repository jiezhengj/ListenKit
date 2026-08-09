# Backends

This is a maintenance reference for ListenKit internals. External LLM agents
should follow `LLM_INTEGRATION.md` and call the platform public entrypoint instead
of calling backend commands directly.

## v1

Three local ASR backends and one URL subtitle backend are supported:

- `auto` is the default selector
- `mlx` uses MLX Whisper and the Metal GPU on Apple Silicon
- `faster-whisper` uses CTranslate2 on CUDA or optimized CPU
- `apple` is optional and uses the bundled Apple Speech helper by default
- `yt-dlp-subtitles` is used by the high-level URL workflow when platform subtitles are available

The default CLI boundary is:

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --auto-init
```

Native Windows uses `.\cli\transcribe-audio.ps1` with the same arguments.

The faster-whisper Python selection order in Bash is:

1. `FASTER_WHISPER_PYTHON`
2. `LISTENKIT_FASTER_WHISPER_VENV_PYTHON`, when explicitly set
3. `~/Library/Caches/ListenKit/venvs/cpython-314/bin/python`
4. authorized initialization through `--auto-init`, `LISTENKIT_AUTO_INIT=1`, or an interactive TTY prompt

On native Windows, `.\cli\init-faster-whisper.ps1`, `.\cli\check-runtime.ps1`, and `.\cli\transcribe-audio.ps1` use `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe` by default. `LISTENKIT_FASTER_WHISPER_VENV_DIR` overrides the environment directory on every supported platform. WSL follows the Bash/Linux path rather than the native Windows path.

The native Windows public boundary is `.\cli\generate-markdown.ps1`; it provides the same URL/local-media, subtitle-first, ASR-fallback, JSON, and Markdown contract as the Bash entrypoint without requiring Bash.

Non-interactive callers should pass `--auto-init` or run the platform `init-faster-whisper` entrypoint before transcription.

The Cache runtime is owned exclusively by ListenKit. Downstream projects must call ListenKit through its CLI and JSON contract; they must not import packages from this environment. The platform `check-runtime` entrypoint verifies Python 3.14, the runtime location, the installed faster-whisper distribution, and a bounded import without modifying the environment.

The runtime must not live under iCloud Drive (`Library/Mobile Documents`). It contains native libraries and model dependencies that need predictable local filesystem access. `LISTENKIT_FASTER_WHISPER_VENV_DIR` can override the default root, but the initializer and health check reject iCloud-backed targets.

Avoid documenting or using raw `python3 -m venv .venv` setup commands. They bypass the supported runtime path and health checks.

Fixed model defaults:

- faster-whisper: `small`
- MLX Whisper: `mlx-community/whisper-small-mlx`
- beam size: `5`

On Apple Silicon, `auto` first probes MLX and prepares the pinned
`mlx-whisper` runtime when needed. Once Metal is ready, the MLX helper is chosen
and reports `engine=mlx-whisper`, `device=metal`, and `compute_type=float16`.
Explicit `--engine mlx` makes this a requirement instead of allowing a fallback.
`LISTENKIT_MLX_AUTO_PREPARE=0` disables dependency preparation and
`LISTENKIT_MLX_MODEL` overrides the compatible model repository.

The Bash and native Windows entrypoints both use the Python core's
`--device auto --compute-type auto` policy:

1. Query CTranslate2 for actual CUDA devices and supported compute types.
2. Merge NVIDIA name, Compute Capability, and dedicated free VRAM from
   `nvidia-smi` when it is available.
3. When an NVIDIA driver is present on Windows or Linux, install CUDA 12 cuBLAS
   and cuDNN 9 into the managed venv if the libraries are not already usable.
4. Prefer `float16` with at least 3072 MiB free; below that, prefer a supported
   lower-memory type such as `int8_float16`.
5. Attempt any NVIDIA generation that CTranslate2 reports as supported. On a
   CUDA library or out-of-memory failure, retry a lower-memory CUDA type and
   only then use `cpu` + `int8` in automatic mode.

The auto policy does not infer compatibility from a marketing model name alone.
AMD and Intel GPUs remain on the optimized CPU path because CTranslate2's
prebuilt GPU backend is CUDA-only. Intel Macs, and Apple Silicon automatic mode
after a reported MLX preparation failure, use CTranslate2's Apple Accelerate
optimized CPU backend. The CTranslate2 macOS wheel itself does not expose a
Metal/MPS GPU backend; Apple Silicon GPU execution is provided by MLX.

Explicit `--device cuda` never silently falls back to CPU. It fails with the
CUDA diagnostic after any lower-memory CUDA retry. `--device cpu` always avoids
CUDA probing. The equivalent environment controls are `LISTENKIT_ASR_DEVICE`,
`LISTENKIT_ASR_COMPUTE_TYPE`, and `LISTENKIT_CUDA_DEVICE_INDEX`.

Apple Speech can be forced with:

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --engine apple
```

The bundled helper is built from `tools/apple-speech-helper/` on first use. It launches a local macOS app through `/usr/bin/open` so Speech permission prompts can be shown. Set `APPLE_SPEECH_HELPER=/path/to/helper` only when you want to override the bundled helper.

Any helper must return:

- `schema_version` (`1` for current built-in backends)
- `engine`
- `locale`
- `full_text`
- `segments`
- `timing_complete`

The subtitle backend uses the same transcript JSON shape. It is only used for URL input by the platform `generate-markdown` entrypoint; the platform `transcribe-audio` command remains a local audio ASR command.

The corresponding native Windows commands use the same basenames with `.ps1` extensions.

Readers accept legacy payloads without `schema_version` as v1 for compatibility. An explicit version other than `1` is unsupported and must fail before rendering or downstream processing.

If a backend fails after producing JSON, it should return an `error` object as the first top-level field:

```json
{
  "error": {
    "type": "backend_error",
    "message": "human-readable failure reason"
  }
}
```

An error payload is terminal. Renderers and adapters must not render it as a transcript; they should surface the error and ask the user to fix the backend or rerun transcription. The shell CLI checks for this leading top-level `error` shape without requiring Python on the Apple Speech path.

## Future Backends

Potential future engines:

- cloud ASR APIs

Any future backend should preserve the same transcript JSON shape so adapters and renderers do not fork.
