# ListenKit

ListenKit 是一个本地优先的多语言音视频转写工具链。它接收视频网址或本地媒体文件，输出便于阅读的 Markdown 转写稿，以及同名的结构化 JSON。

## 快速试用

macOS / Linux / WSL：

```bash
git clone https://github.com/feiyanqiqiao/ListenKit.git
cd ListenKit
# macOS 使用 Homebrew；Linux 请通过系统包管理器安装同名工具。
brew install yt-dlp ffmpeg
cli/listenkit.sh generate-markdown --help
cli/listenkit.sh generate-markdown --url "https://example.com/video" --language Japanese --output work/sample.md --report-json work/sample.execution.json --auto-init
```

Windows 10/11 PowerShell：

```powershell
winget install Python.Python.3.14
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg
.\cli\listenkit.ps1 generate-markdown --help
.\cli\listenkit.ps1 generate-markdown --url "https://example.com/video" --language Japanese --output work\sample.md --report-json work\sample.execution.json --auto-init
```

Windows 流程是原生 PowerShell 实现，不依赖 Bash、WSL、Git Bash 或 MSYS2。POSIX `.sh` 入口在 Git Bash/MSYS2/Cygwin 中会主动以退出码 64 拒绝；请使用 Python 或 PowerShell 分发器。

如果 PowerShell 执行策略受限，可使用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\cli\listenkit.ps1 generate-markdown --url "https://example.com/video" --language Japanese --output work\sample.md --auto-init
```

默认 ASR 策略会优先准备和使用硬件加速：Apple Silicon macOS 使用 MLX Whisper 与 Metal；Windows/Linux 的 NVIDIA 环境使用托管 CUDA，并在自动模式下记录失败原因后回退到 CPU INT8。Intel Mac 使用 CTranslate2 的 Apple Accelerate CPU 后端。

可用的显式设备控制包括：`--device cpu`（可复现的 CPU-only 执行）、`--device cuda`（要求 CUDA 且不允许 CPU fallback）和 Apple Silicon 上的 `--engine mlx`（要求 MLX/Metal）。默认情况下请保持 engine 和 device 为 `auto`。

运行结果：

```text
work/sample.md
work/sample.json
work/sample.execution.json
```

执行报告是可选产物，包含成功或失败、耗时、产物路径和实际 ASR 后端元数据，不复制完整转写正文。具备兼容 Python 的 Agent 也可以从仓库根目录直接调用 `python -m listenkit_cli generate-markdown`。

## 安装给 AI Agent

如果已知 Agent 规则或上下文文件位置：

```bash
cli/install-agent-instructions.sh --target <规则文件或目录>
```

Windows 使用 `.\cli\install-agent-instructions.ps1` 的相同参数。若不知道目标位置，请参考 `LLM_INTEGRATION.md` 中的 `--print` 方案。

## 文档

- `LLM_INTEGRATION.md`：AI / Agent 安装与使用契约
- `docs/install.md`：依赖、运行环境、硬件加速和故障排查
- `docs/backends.md`：ASR 引擎和加速策略
- `docs/debugging.md`：维护与底层调试接口
- `docs/output-format.md`：Markdown 与 JSON 输出格式
- `PRIVACY_AND_COPYRIGHT.md`：隐私与版权边界
- `.specify/memory/constitution.md`：项目工程原则
- `specs/`：Spec Kit 规格、计划、任务和验证工件

## 功能边界

```text
网址或本地媒体
  -> python -m listenkit_cli generate-markdown
     或 cli/listenkit.sh generate-markdown
     或 .\cli\listenkit.ps1 generate-markdown
  -> transcript Markdown + 同名 transcript JSON
```

输入：

- yt-dlp 支持的网址
- 本地音频、视频或其他媒体文件
- Audio Hijack 保存到本地的录音

输出：

- 包含来源、语言、转写引擎、实际设备和正文的纯 Markdown
- 包含标准化文本、分段、时间戳和硬件 fallback 诊断的同名 JSON
- 下游已经选好时间段时，可通过 `cli/export-audio-slices.py` 导出音频片段

ListenKit 不绑定 Codex，也不只支持日语。公开 CLI 支持 Japanese、English、Chinese 和 Korean 标签。它只负责获取媒体、优先提取平台字幕、执行本地 ASR 和规范化转写稿；笔记、摘要、单词卡和间隔复习属于下游应用。

## 适配器

- 通用 Agent：`adapters/agent/listenkit-agent-instructions.md`
- Codex：`adapters/codex/SKILL.md`
- Claude：`adapters/claude/CLAUDE.md`
- Cursor：`adapters/cursor/foreign-listening.md`

正常集成只应调用共享的 `generate-markdown` 命令：跨平台 Python 入口、macOS / Linux / WSL 的 `cli/listenkit.sh generate-markdown`，或原生 Windows 的 `.\cli\listenkit.ps1 generate-markdown`。需要文件化执行状态时使用 `--report-json`。不要重复实现下载、字幕选择、ASR 和渲染流程。

## 隐私与版权

默认转写在本机完成；首次运行可能下载模型和运行时依赖。后续处理转写文本的工具可能把文本发送给你使用的模型服务商。请只处理你有权使用的内容，详见 `PRIVACY_AND_COPYRIGHT.md`。
