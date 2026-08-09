# ListenKit

ListenKit 是一个本地优先的多语言音视频转写工具链。它接收视频网址或本地媒体文件，输出便于阅读的 Markdown 转写稿，以及同名的结构化 JSON。

简体中文 | [English](README.md)

## 快速开始

macOS / Linux / WSL：

```bash
git clone https://github.com/feiyanqiqiao/ListenKit.git
cd ListenKit
# macOS 使用 Homebrew；Linux 请通过系统包管理器安装同名工具。
brew install yt-dlp ffmpeg
cli/generate-markdown.sh --help
cli/generate-markdown.sh --url "https://example.com/video" --language Japanese --output work/sample.md --auto-init
```

Windows 10/11 PowerShell：

```powershell
winget install Python.Python.3.14
winget install yt-dlp.yt-dlp
winget install Gyan.FFmpeg
.\cli\generate-markdown.ps1 --help
.\cli\generate-markdown.ps1 --url "https://example.com/video" --language Japanese --output work\sample.md --auto-init
```

Windows 流程是原生 PowerShell 实现，不依赖 Bash、WSL、Git Bash 或 MSYS2。如果脚本执行策略受限，可使用 `powershell -ExecutionPolicy Bypass -File .\cli\generate-markdown.ps1 ...`。

默认 ASR 策略会优先准备和使用硬件加速：

- Apple Silicon macOS：自动安装隔离的 MLX Whisper 运行依赖并使用 Metal GPU。
- Windows / Linux + NVIDIA：自动准备运行环境内的 CUDA 12 cuBLAS 与 cuDNN 9，优先尝试 GPU；显存不足时先降低 CUDA 精度，失败原因会写入输出后才回退到 CPU INT8。
- Intel Mac：使用 CTranslate2 的 Apple Accelerate CPU 后端。
- `--device cpu` 可强制 CPU；`--device cuda` 可强制 CUDA 且禁止 CPU fallback；Apple Silicon 上 `--engine mlx` 可强制要求 MLX/Metal。

命令会生成：

```text
work/sample.md
work/sample.json
```

## 安装给 AI Agent

如果已知 Agent 规则或上下文文件位置：

```bash
cli/install-agent-instructions.sh --target <规则文件或目录>
```

Windows 使用 `.\cli\install-agent-instructions.ps1` 的相同参数。若不知道目标位置，请参考 `LLM_INTEGRATION.md` 中的 `--print` 方案。

## 文档

- `LLM_INTEGRATION.md`：AI / Agent 集成契约
- `docs/install.md`：依赖、运行环境、硬件加速和故障排查
- `docs/backends.md`：ASR 引擎和加速策略
- `docs/debugging.md`：维护与底层调试接口
- `docs/output-format.md`：Markdown 与 JSON 输出格式
- `PRIVACY_AND_COPYRIGHT.md`：隐私与版权边界

## 功能边界

输入：

- yt-dlp 支持的网址
- 本地音频、视频或其他媒体文件
- Audio Hijack 保存到本地的录音

输出：

- 包含来源、语言、转写引擎、实际设备和正文的纯 Markdown
- 包含标准化文本、分段、时间戳和硬件 fallback 诊断的同名 JSON

ListenKit 不绑定 Codex，也不只支持日语。公开 CLI 支持 Japanese、English、Chinese 和 Korean 标签。它只负责获取媒体、优先提取平台字幕、执行本地 ASR 和规范化转写稿；笔记、摘要、单词卡和间隔复习属于下游应用。

## 适配器

- 通用 Agent：`adapters/agent/listenkit-agent-instructions.md`
- Codex：`adapters/codex/SKILL.md`
- Claude：`adapters/claude/CLAUDE.md`
- Cursor：`adapters/cursor/foreign-listening.md`

正常集成只应调用 macOS / Linux / WSL 的 `cli/generate-markdown.sh`，或原生 Windows 的 `.\cli\generate-markdown.ps1`，不要重复实现下载、字幕选择、ASR 和渲染流程。

## 隐私与版权

默认转写在本机完成：可用的 Apple Silicon Mac 使用 MLX Whisper，其余平台使用 faster-whisper；首次运行可能下载模型。macOS 还可选择 Apple Speech。后续处理转写文本的工具可能把文本发送给你使用的模型服务商。请只处理你有权使用的内容，详见 `PRIVACY_AND_COPYRIGHT.md`。
