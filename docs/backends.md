# 后端

本文档是 ListenKit 内部维护参考。外部 LLM Agent 应遵循 `LLM_INTEGRATION.md`，调用平台公共入口，不要直接调用后端命令。

## v1

当前支持三个本地 ASR 后端和一个 URL 字幕后端：

- `auto`：默认选择器
- `mlx`：Apple Silicon 上使用 MLX Whisper 与 Metal GPU
- `faster-whisper`：在 CUDA 或优化 CPU 上使用 CTranslate2
- `apple`：可选，默认使用随项目提供的 Apple Speech helper
- `yt-dlp-subtitles`：高层 URL 流程在平台字幕可用时使用

后端维护边界为：

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --auto-init
```

原生 Windows 使用同参数的 `.\cli\transcribe-audio.ps1`。这不是外部 Agent 的正常集成入口；外部 Agent 必须使用 `generate-markdown`。

Bash 环境下 faster-whisper 的 Python 选择顺序为：

1. `FASTER_WHISPER_PYTHON`
2. 显式设置的 `LISTENKIT_FASTER_WHISPER_VENV_PYTHON`
3. `~/Library/Caches/ListenKit/venvs/cpython-314/bin/python`
4. 通过 `--auto-init`、`LISTENKIT_AUTO_INIT=1` 或交互式 TTY 授权初始化

原生 Windows 默认使用 `%LOCALAPPDATA%\ListenKit\venvs\cpython-314\Scripts\python.exe`。`LISTENKIT_FASTER_WHISPER_VENV_DIR` 可在所有支持平台覆盖环境目录；WSL 遵循 Bash/Linux 路径。

原生 Windows 的首选公共分发器是 `.\cli\listenkit.ps1 generate-markdown`；`.\cli\generate-markdown.ps1` 是仍受支持的兼容包装器。二者提供相同的网址/本地媒体、字幕优先、ASR fallback、JSON 和 Markdown 契约，且不要求 Bash。

非交互调用方应传入 `--auto-init`，或先运行平台对应的 `init-faster-whisper` 入口。

Cache 运行时完全由 ListenKit 管理。下游项目必须通过 CLI 和 JSON 契约调用 ListenKit，不得导入该环境内的包。平台 `check-runtime` 入口只读检查 Python 3.14、运行时位置、faster-whisper 分发包和有界导入，不修改环境。

运行时不得放在 iCloud Drive（`Library/Mobile Documents`）下，因为其中的原生库和模型依赖需要稳定的本地文件系统。初始化器和健康检查会拒绝 iCloud 路径。

不要记录或使用 `python3 -m venv .venv` 作为安装方案；它会绕过受支持的运行时路径和健康检查。

固定模型默认值：

- faster-whisper：`small`
- MLX Whisper：`mlx-community/whisper-small-mlx`
- beam size：`5`

Apple Silicon 上，`auto` 会先探测并在需要时准备固定版本的 `mlx-whisper` 运行时；Metal 就绪后选择 MLX，并报告 `engine=mlx-whisper`、`device=metal` 和 `compute_type=float16`。显式 `--engine mlx` 会把该路径变为必需条件；`LISTENKIT_MLX_AUTO_PREPARE=0` 可禁用准备，`LISTENKIT_MLX_MODEL` 可覆盖兼容模型仓库。

Bash 和原生 Windows 入口都使用 Python 核心的 `--device auto --compute-type auto` 策略：

1. 查询 CTranslate2 实际 CUDA 设备和支持的计算类型。
2. 在可用时从 `nvidia-smi` 合并 NVIDIA 名称、Compute Capability 和专用可用显存。
3. Windows/Linux 存在 NVIDIA 驱动时，如果库不可用，将 CUDA 12 cuBLAS 与 cuDNN 9 安装到托管 venv。
4. 可用显存至少 3072 MiB 时优先 `float16`；更低时优先支持的低显存类型，例如 `int8_float16`。
5. 尝试 CTranslate2 报告支持的 NVIDIA 设备；CUDA 库或显存失败时重试低显存类型，自动模式最后才使用 `cpu` + `int8`。

自动策略不只根据营销型号判断兼容性。由于 CTranslate2 预构建 GPU backend 仅支持 CUDA，AMD 和 Intel GPU 保持在优化 CPU 路径。Intel Mac，以及 Apple Silicon 自动 MLX 准备失败后，使用 CTranslate2 的 Apple Accelerate CPU backend。CTranslate2 macOS wheel 不提供 Metal/MPS GPU；Apple Silicon GPU 由 MLX 提供。

显式 `--device cuda` 在低显存 CUDA 重试后失败时不得静默回退 CPU；`--device cpu` 始终跳过 CUDA 探测。对应的环境变量是 `LISTENKIT_ASR_DEVICE`、`LISTENKIT_ASR_COMPUTE_TYPE` 和 `LISTENKIT_CUDA_DEVICE_INDEX`。

可强制使用 Apple Speech：

```bash
cli/transcribe-audio.sh --audio-path <path> --locale <bcp47> --engine apple
```

随项目提供的 helper 首次使用时从 `tools/apple-speech-helper/` 构建，并通过 `/usr/bin/open` 启动本地 macOS app，以便显示 Speech 权限提示。只有需要覆盖默认 helper 时才设置 `APPLE_SPEECH_HELPER=/path/to/helper`。

任何 helper 都必须返回：

- `schema_version`（当前内置后端为 `1`）
- `engine`
- `locale`
- `full_text`
- `segments`
- `timing_complete`

字幕 backend 使用相同的 transcript JSON 形状，只在平台 `generate-markdown` URL 输入中使用；平台 `transcribe-audio` 仍是本地音频 ASR 命令。

原生 Windows 使用相同 basename 的 `.ps1` 命令。读取方为兼容性接受没有 `schema_version` 的 legacy payload；显式声明除 `1` 之外的版本时，必须在渲染或下游处理前失败。

如果 backend 在生成 JSON 后失败，必须将 `error` 对象作为顶层第一个字段：

```json
{
  "error": {
    "type": "backend_error",
    "message": "human-readable failure reason"
  }
}
```

错误 payload 是终止状态。渲染器和适配器不得把它渲染成转写稿，而应暴露错误并要求用户修复 backend 或重试。Apple Speech 路径即使不依赖 Python，也会检查这个顶层 `error` 形状。

## 未来后端

潜在的未来引擎包括 cloud ASR APIs。任何未来 backend 都必须保持相同的 transcript JSON 形状，以避免适配器和渲染器分叉。
