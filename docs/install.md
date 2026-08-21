# 安装与运行时

本文档说明系统依赖、后端初始化和故障排查。外部 Agent 应从仓库根目录运行 `python -m listenkit_cli generate-markdown`，在 macOS/Linux/WSL 使用 `cli/listenkit.sh generate-markdown`，在原生 Windows 使用 `.\cli\listenkit.ps1 generate-markdown`。低层命令仅供后端维护和调试。

## 系统依赖

macOS：

```bash
brew install yt-dlp ffmpeg
```

Linux 请使用系统包管理器安装等价的 `yt-dlp` 和 `ffmpeg`。Windows 10/11 可使用：

```powershell
winget install Python.Python.3.14
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg
```

安装后重新打开终端并运行 `.\cli\doctor.ps1`。ListenKit 优先检查 `PATH`，也识别 WinGet Links 目录中的 `yt-dlp.exe` 和 `ffmpeg.exe`，不会静默安装系统软件包。

如果 PowerShell 执行策略受限，使用 `powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\listenkit.ps1 doctor`，或对 `generate-markdown` 传入相同的脚本参数。

faster-whisper 运行时需要 Python 3.14；macOS 使用 Homebrew Python 3.14 作为受支持的 bootstrap Python。其它轻量维护脚本兼容 Python 3.10+。

## Agent 与非登录 shell

桌面 Agent 可能继承精简的 `PATH`，或为自身嵌入式 Python 设置 `PYTHONHOME` 和 `PYTHONPATH`。`cli/listenkit.sh` 及 POSIX 包装器会删除这些 Python 变量、强制 UTF-8 I/O，并在 macOS 探测标准 Apple Silicon/Intel Homebrew 前缀，不修改父 Agent 环境。

原生 Windows 分发器提供相同隔离：删除继承的 Python 变量、使用 UTF-8 标准流并恢复调用方环境。Git Bash、MSYS2 和 Cygwin 是原生 Windows 环境，其中 `.sh` 入口会以退出码 64 失败；请使用 Python 或 PowerShell。

如果兼容的 CLI Python 不在 `PATH`，可以显式选择：

```bash
LISTENKIT_CLI_PYTHON=/path/to/python3 cli/listenkit.sh doctor
```

PowerShell：

```powershell
$env:LISTENKIT_CLI_PYTHON = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
.\cli\listenkit.ps1 doctor
```

Windows 分发器会依次尝试托管运行时、标准用户目录和 Program Files 的 Python 3.14、`py -3.14`、`python3.14` 和 `python`，每个候选都必须通过真实版本探测。

CLI 主机需要 Python 3.10+；托管 ASR 运行时固定 Python 3.14。缺失运行时在自动化中不会触发隐式提示；传入 `--auto-init` 才授权准备。低层 Bash transcriber 另有只供人工确认的 `--interactive-init`。

## 托管 ASR 运行时

默认运行时目录：

- macOS/Linux Bash：`~/Library/Caches/ListenKit/venvs/cpython-314`
- Windows PowerShell：`%LOCALAPPDATA%\ListenKit\venvs\cpython-314`

运行时必须在仓库外和 iCloud Drive 外。它包含大型原生库，避免放在 `Library/Mobile Documents` 下，以免文件协调或下载状态影响加载。使用 `LISTENKIT_FASTER_WHISPER_VENV_DIR` 覆盖时也必须满足这一限制。

默认 ASR 引擎为 `auto`：

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --auto-init
```

`--auto-init` 授权创建或修复本地 Cache 运行时并安装 `faster-whisper`。手动初始化使用：

```bash
cli/init-faster-whisper.sh
```

初始化器使用 `requirements-faster-whisper.txt` 中的直接依赖；Apple Silicon 还使用 `requirements-mlx-whisper.txt`。`docs/runtime-snapshot-python314.txt` 只提供诊断证据，不是安装锁定文件。

只读检查已有环境：

```bash
cli/check-runtime.sh
```

Windows 使用原生入口：

```powershell
.\cli\init-faster-whisper.ps1
.\cli\check-runtime.ps1
.\cli\doctor.ps1
.\cli\listenkit.ps1 generate-markdown --input "C:\Media\sample.m4a" --language English --output work\sample.md --report-json work\sample.execution.json --auto-init --device auto
```

Windows 入口同时支持 PowerShell 5.1 和 7，不依赖 Bash、Git Bash、MSYS2、Cygwin 或 WSL。不要在仓库内使用 `python3 -m venv .venv`，它会绕过受支持的路径和检查。

## 默认设置与 CUDA

- faster-whisper 模型：`small`
- MLX Whisper 模型：`mlx-community/whisper-small-mlx`
- beam size：`5`
- Apple Silicon：MLX Whisper + Metal + `float16`
- Windows/Linux NVIDIA：自动准备 CUDA 并选择计算类型
- 无 NVIDIA 的 Windows/Linux：优化 CPU + `int8`
- Intel macOS：Apple Accelerate 优化 CPU + `int8`

Windows/Linux 自动模式会先检查 NVIDIA 驱动和 CTranslate2 能力；需要时将 `nvidia-cublas-cu12` 和 `nvidia-cudnn-cu12` 安装到 ListenKit 隔离 venv，不修改系统 CUDA。至少 3072 MiB 专用显存时优先 `float16`，更低时优先 `int8_float16`；所有支持的 CUDA 类型都失败后才记录原因并回退 CPU。`doctor` 只读报告驱动、库、设备、显存和自动选择。

设备控制变量为 `LISTENKIT_ASR_DEVICE`、`LISTENKIT_ASR_COMPUTE_TYPE` 和 `LISTENKIT_CUDA_DEVICE_INDEX`；显式 CLI 参数优先。`--device cuda` 失败时不回退 CPU，`--device cpu` 始终跳过 CUDA 探测。

## Apple Silicon MLX/Metal

Apple Silicon 的 `auto` 会探测并在需要时准备托管 MLX 依赖。Metal 就绪后使用 `mlx-whisper`；首次转写可能下载 `mlx-community/whisper-small-mlx`，后续使用 Hugging Face 缓存。`--engine mlx` 要求该路径；`LISTENKIT_MLX_MODEL` 可覆盖兼容模型仓库；`LISTENKIT_MLX_AUTO_PREPARE=0` 可禁用准备。

如果 MLX 准备失败，ListenKit 会打印原因并通过 CTranslate2 Apple Accelerate CPU backend 使用 faster-whisper。`doctor` 只读报告 Apple Silicon、MLX/Metal、版本、模型缓存和自动选择。

## Apple Speech

Apple Speech 是可选的本地 macOS backend。ListenKit 首次使用时构建 `tools/apple-speech-helper/` 下的 helper，并通过 `/usr/bin/open` 启动本地 app，以便 macOS 显示 Speech 权限提示。

```bash
cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --engine apple
```

默认 helper：`tools/apple-speech-helper/run-apple-speech-helper.sh`。需要覆盖时：

```bash
APPLE_SPEECH_HELPER=/path/to/run-apple-speech-helper.sh \
  cli/transcribe-audio.sh --audio-path work/audio/sample.m4a --locale ja-JP --engine apple
```

helper 契约：

```bash
run-apple-speech-helper.sh --audio-path <path> --locale <bcp47>
```

它必须打印以下形状的 JSON：

```json
{
  "engine": "apple",
  "locale": "ja-JP",
  "full_text": "...",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "timing_complete": true
}
```

常见失败包括 Speech 权限被拒、macOS 版本过旧、locale 不支持、语音资源缺失、音频路径不可读，以及缺少 Xcode command line tools 或 macOS SDK。

## Audio Hijack

Audio Hijack 是可选输入方式。先把系统或应用音频录制为本地文件，再交给 ListenKit：

```bash
cli/import-audio.sh --input <recording> --output-dir work/audio
```

正常 Agent 集成仍应使用 `generate-markdown` 公共入口；本节低层命令只用于维护和调试。

## 常见失败

- 自动化未授权 `--auto-init`。
- faster-whisper 未安装、模型下载被阻止、音频缺失或不可读。
- 运行时不是 Python 3.14，或目标位于 iCloud Drive。
- 导入健康检查超过 60 秒。
- CUDA 驱动、下载、cuBLAS/cuDNN 或所有计算类型准备失败。
- MLX 运行在 Intel Mac、Metal 不可用、下载被阻止或自动准备被禁用。
