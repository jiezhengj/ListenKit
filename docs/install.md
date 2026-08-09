# Install

This document covers system dependencies, backend initialization, and troubleshooting. Normal users and external agents should run `cli/generate-markdown.sh` on macOS/Linux/WSL or `.\cli\generate-markdown.ps1` on native Windows. Lower-level commands are backend or debugging references, not the public agent entrypoint.

## Dependencies

```bash
brew install yt-dlp ffmpeg
```

Linux users should install equivalent `yt-dlp` and `ffmpeg` packages with their system package manager.

Windows 10/11 users can install the verified winget packages from PowerShell:

```powershell
winget install Python.Python.3.14
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg
```

Restart the terminal after installation, then run `.\cli\doctor.ps1`. ListenKit checks `yt-dlp.exe` and `ffmpeg.exe` on `PATH`; it does not silently install system packages.

Python 3.14 is required for the faster-whisper runtime. On macOS, Homebrew Python 3.14 is the supported bootstrap Python. Other lightweight maintenance scripts remain compatible with Python 3.10+.

The default ASR environment is platform-specific:

- macOS and Linux Bash: `~/Library/Caches/ListenKit/venvs/cpython-314`
- Windows PowerShell: `%LOCALAPPDATA%\ListenKit\venvs\cpython-314`

On a typical Windows installation, the latter expands to `C:\Users\<username>\AppData\Local\ListenKit\venvs\cpython-314`, and its interpreter is `Scripts\python.exe`. WSL uses the Linux/Bash path inside the WSL filesystem, not the Windows path.

The runtime is deliberately stored outside the repository and outside iCloud Drive. It contains large native libraries whose loading can stall while iCloud is hydrating or coordinating files. Do not place the runtime under `Library/Mobile Documents`.

On Apple Silicon, the same managed environment also contains the pinned
`mlx-whisper` package used for Metal GPU transcription. The optional Apple
Speech backend requires macOS with Speech APIs and Xcode command line tools for
the bundled Swift helper build.

## Automatic Backend And Runtime

The default ASR engine is `auto`:

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --auto-init
```

`--auto-init` authorizes ListenKit to create or repair the local Cache runtime
and install `faster-whisper`. Once the managed runtime exists, transcription
also verifies and, when needed, prepares MLX/Metal on Apple Silicon or managed
CUDA on Windows/Linux NVIDIA before selecting a backend. For a one-time manual
setup, run this script from anywhere:

```bash
cli/init-faster-whisper.sh
```

The initializer installs the direct dependency pinned in
`requirements-faster-whisper.txt`. On Apple Silicon it also installs the
verified `requirements-mlx-whisper.txt` dependency set. Transitive packages
such as CTranslate2, ONNX Runtime, PyAV, MLX, and mlx-metal are selected by those
packages. The runtime snapshot under `docs/runtime-snapshot-python314.txt` is
diagnostic evidence only and is not an installation lock file.

Check an existing environment without changing it:

```bash
cli/check-runtime.sh
```

Windows PowerShell has native initialization, health-check, diagnosis, and complete transcript entrypoints:

```powershell
.\cli\init-faster-whisper.ps1
.\cli\check-runtime.ps1
.\cli\doctor.ps1
.\cli\generate-markdown.ps1 --input "C:\Media\sample.m4a" --language English --output work\sample.md --auto-init --device auto
```

The Windows entrypoints support Windows PowerShell 5.1 and PowerShell 7 and run through the shared cross-platform Python core. They do not require Bash or WSL. Apple Speech remains macOS-only; Windows uses faster-whisper.

Do not initialize with `python3 -m venv .venv` in the repository. Use the ListenKit initializer so the native runtime remains outside iCloud and uses the supported Python version.

To use a different runtime location, set `LISTENKIT_FASTER_WHISPER_VENV_DIR`. The target must remain outside iCloud Drive:

```bash
LISTENKIT_FASTER_WHISPER_VENV_DIR=/path/outside/icloud \
  cli/init-faster-whisper.sh
```

In PowerShell:

```powershell
$env:LISTENKIT_FASTER_WHISPER_VENV_DIR = "D:\ListenKit\venvs\cpython-314"
.\cli\init-faster-whisper.ps1
```

Advanced users can use an external Python environment:

```bash
FASTER_WHISPER_PYTHON=/path/to/python \
  cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP
```

In PowerShell:

```powershell
$env:FASTER_WHISPER_PYTHON = "D:\Python\faster-whisper\Scripts\python.exe"
.\cli\transcribe-audio.ps1 --audio-path work\audio\sample.m4a --locale ja-JP
```

Default settings:

- faster-whisper model: `small`
- MLX Whisper model: `mlx-community/whisper-small-mlx`
- beam size: `5`
- Apple Silicon macOS: `mlx-whisper` + Metal GPU + float16
- Windows/Linux NVIDIA: automatic CUDA preparation and compute-type selection
- Windows/Linux without NVIDIA: optimized `cpu` + `int8`
- Intel macOS: CTranslate2 Apple Accelerate optimized CPU backend + `int8`

On Windows and Linux, automatic selection first checks the NVIDIA driver and
CTranslate2 device capabilities. Initialization installs `nvidia-cublas-cu12`
and `nvidia-cudnn-cu12` into ListenKit's isolated venv when needed; it does not
modify a system CUDA installation. Package DLL/shared-library directories are
injected only into ListenKit child processes. The policy prefers `float16` when
at least 3072 MiB of dedicated VRAM is free and prefers `int8_float16` below
that threshold when supported. Older or temporarily memory-constrained NVIDIA
devices are still attempted with a supported lower-memory compute type instead
of being rejected from model name, age, or a static VRAM threshold.

ListenKit never installs or changes the NVIDIA system driver. If the driver is
present, managed CUDA dependencies are prepared by the platform initializer or
before managed-runtime transcription. Set `LISTENKIT_CUDA_AUTO_PREPARE=0` only
to disable this behavior deliberately. `doctor` remains read-only and reports
the driver, managed libraries, devices, compute types, memory, and automatic
choice.

### Apple Silicon MLX/Metal

On an M-series Mac, automatic mode probes the managed MLX runtime and prepares
it when needed. A successful probe selects `mlx-whisper` on the Metal GPU. The
first transcription downloads `mlx-community/whisper-small-mlx`; later runs
reuse the Hugging Face cache. Use `--engine mlx` to require this path and fail
clearly if Metal is not ready. Set `LISTENKIT_MLX_MODEL` to another compatible
MLX Whisper repository only when you intentionally want a different model.

If automatic MLX preparation fails, ListenKit prints the reason and uses
faster-whisper through CTranslate2's Apple Accelerate CPU backend. Set
`LISTENKIT_MLX_AUTO_PREPARE=0` only to disable managed preparation deliberately.
`doctor` is read-only: it reports Apple Silicon, MLX and Metal availability,
versions, default device, model cache, and the engine that automatic mode would
select.

Intel Macs use **Apple Accelerate**, an optimized CPU backend. CTranslate2's
prebuilt macOS wheel does not expose Metal/MPS GPU execution. The optional
`--engine apple` backend uses Apple's Speech framework, whose hardware
scheduling is controlled by macOS.

Device controls:

```powershell
# Safe automatic selection and CPU fallback (default)
.\cli\transcribe-audio.ps1 --audio-path work\audio\sample.m4a --locale ja-JP --device auto

# Reproducible CPU-only execution
.\cli\transcribe-audio.ps1 --audio-path work\audio\sample.m4a --locale ja-JP --device cpu

# Require CUDA device 0; failure is reported and never hidden by CPU fallback
.\cli\transcribe-audio.ps1 --audio-path work\audio\sample.m4a --locale ja-JP --device cuda --device-index 0 --compute-type float16
```

The same settings can be supplied with `LISTENKIT_ASR_DEVICE`,
`LISTENKIT_ASR_COMPUTE_TYPE`, and `LISTENKIT_CUDA_DEVICE_INDEX`. Explicit CLI
arguments take precedence. These device and compute controls apply to
faster-whisper; MLX always uses Metal. The first run may download the selected
model and take significantly longer than later cached runs.

Common faster-whisper failures:

- auto-init was not authorized in a non-interactive shell
- `faster-whisper` is not installed in the selected Python environment
- model download is blocked or incomplete
- the audio file is missing or unreadable
- the selected runtime is not Python 3.14
- the selected runtime is stored in iCloud Drive
- the import health check exceeds 60 seconds
- CUDA preparation failed because the driver, package download, or managed
  cuBLAS/cuDNN libraries are unavailable
- every supported CUDA precision failed (for example due to actual OOM), after
  which automatic mode records the reason and uses CPU

Common MLX failures:

- the Mac is Intel rather than Apple Silicon
- Metal is unavailable to the process
- managed dependency or model download is blocked
- MLX auto-preparation was deliberately disabled

## Apple Speech Backend

Apple Speech is an optional local macOS backend. ListenKit bundles a small helper app that is built on first use and launched through `/usr/bin/open` so macOS can show Speech permission prompts.

The default helper lives at:

```text
tools/apple-speech-helper/run-apple-speech-helper.sh
```

Use it with:

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --engine apple
```

You can still point to an external helper:

```bash
APPLE_SPEECH_HELPER=/path/to/run-apple-speech-helper.sh \
  cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --engine apple
```

The helper contract is:

```bash
run-apple-speech-helper.sh --audio-path <path> --locale <bcp47>
```

It must print JSON with:

```json
{
  "engine": "apple",
  "locale": "ja-JP",
  "full_text": "...",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "timing_complete": true
}
```

Common Apple Speech failures:

- Speech recognition permission denied
- macOS version too old for the selected Speech APIs
- Locale not supported on the current Mac
- Required speech assets are not installed
- Audio file path is missing or unreadable
- Xcode command line tools or the macOS SDK are missing

## Audio Hijack

Audio Hijack is optional. Use it to record system or app audio into a local file, then pass that file to:

```bash
cli/import-audio.sh --input <recording> --output-dir work/audio
```
