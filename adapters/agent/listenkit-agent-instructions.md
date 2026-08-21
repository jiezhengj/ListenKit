# ListenKit Agent 指令

正常集成只能通过高层 transcript 公共命令使用 ListenKit。

根据当前运行环境选择入口：

- 任何拥有兼容仓库根目录 Python 的平台：`python -m listenkit_cli generate-markdown`
- macOS/Linux/WSL 分发器：`cli/listenkit.sh generate-markdown`
- 原生 Windows 分发器：`.\cli\listenkit.ps1 generate-markdown`

现有的 `cli/generate-markdown.sh` 和 `.\cli\generate-markdown.ps1` 便捷包装器仍受支持。原生 Windows 不得通过 WSL；Git Bash 不是 WSL，且 WSL 拥有不同的文件系统和 ASR 运行时。在 Git Bash/MSYS2/Cygwin 中 `.sh` 入口会以退出码 64 失败，请使用 Python 或 PowerShell 分发器。

## 正常流程

URL：

```bash
cli/listenkit.sh generate-markdown \
  --url "<url>" \
  --language <label> \
  --output <md> \
  --auto-init
```

本地音频或视频：

```bash
cli/listenkit.sh generate-markdown \
  --input <path> \
  --language <label> \
  --output <md> \
  --auto-init
```

规则：

- 必须恰好提供一个输入源：`--url` 或 `--input`。
- 必须提供 `--language` 和 `--output`。
- 除非用户明确选择不同的 backend 设置，否则使用 `--auto-init`。
- 保持 `--engine` 和 `--device` 为自动默认值；只有用户要求可复现的 CPU 执行时才强制 CPU。
- `--output path/name.md` 会同时生成 `path/name.md` 和 `path/name.json`。
- 自动化流程增加 `--report-json path/name.execution.json`，并从该文件读取状态、产物路径、实际 backend 元数据和错误。
- 不要为了补偿宿主 Agent 的 PATH、shell 或 stdout 捕获限制而修改本仓库；使用 Python/平台分发器和 report 文件。
- Windows 自动发现失败时才设置 `LISTENKIT_CLI_PYTHON`；CLI 主机兼容 Python 3.10+，托管 ASR 运行时仍固定 Python 3.14。
- 入口默认非交互；使用 `--auto-init` 授权运行时准备，不要等待隐式终端提示。
- 用户未指定输出路径时，优先使用 `work/<safe-source-stem>-transcript.md`；无法稳定获取 source stem 时使用 `work/transcript.md`。

安装指令支持 `--target <path>`、`--force` 和 `--dry-run`；`--dry-run` 只显示 source/target，不写文件。`--print` 与 `--target`、`--force`、`--dry-run` 互斥。

不得直接调用以下命令作为集成捷径（Do not call these directly as an integration shortcut）：

- `yt-dlp`
- `ffmpeg`
- `cli/import-audio.sh`
- `cli/extract-subtitles.sh`
- `cli/transcribe-audio.sh`
- `cli/render-listening-note.py`
- `tools/*`

这些是依赖、维护或调试接口。缺少 `yt-dlp`、`ffmpeg`、Python 或 backend 初始化时，应请求用户安装或授权缺失依赖，不得绕过 `cli/generate-markdown.sh`。

ListenKit 只负责纯转写 Markdown 和同 stem transcript JSON。摘要、学习笔记、词汇表、卡片和应用记录必须在 ListenKit 产物生成后作为独立下游转换。

下游流程已经选择明确时间范围时，使用受支持的接口导出片段，不要直接调用 `ffmpeg`：

```bash
cli/export-audio-slices.py \
  --input <audio> \
  --manifest <json> \
  --output-dir <dir> \
  --padding-seconds 0.15
```

只有重叠 padding 确实有意且下游能够处理时才使用 `--allow-overlap`。每个时间范围的语义仍由下游流程负责。

只处理你有权下载、录制、转写和学习的材料；不要重新分发受版权保护的音频或转写稿。完整边界见 `PRIVACY_AND_COPYRIGHT.md`。
