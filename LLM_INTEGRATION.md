# ListenKit LLM 集成契约

本文档是外部 LLM Agent 和自动化集成的事实来源。关键不变量必须同步到 `adapters/agent/listenkit-agent-instructions.md`。

## Agent 安装与使用

当用户要求读取 GitHub 仓库并安装 ListenKit 时：

1. 克隆仓库并进入仓库目录。
2. 检查 `yt-dlp` 和 `ffmpeg` 是否可用。缺少任一依赖时，询问用户安装或授权安装；不得使用低层 pipeline 绕过 ListenKit。
3. 如果知道用户的 Agent 规则或上下文目标，安装 Agent 指令：

   ```bash
   cli/install-agent-instructions.sh --target <agent-rules-file-or-dir>
   ```

   Windows 使用 `.\cli\install-agent-instructions.ps1 --target <agent-rules-file-or-dir>`。

4. 如果不知道持久化规则或上下文目标，不得猜测。使用以下固定提示：

   ```text
   I can install ListenKit instructions, but I need the path to your agent rules/context file or directory. If you only want to use it once, I can skip installation and run ListenKit directly.
   ```

5. 如果用户需要可粘贴的备用内容，打印指令：

   ```bash
   cli/install-agent-instructions.sh --print
   ```

`cli/install-agent-instructions.sh` 只安装 Agent instructions，不安装 Homebrew 软件包、Python、faster-whisper、Apple Speech 资源或 ASR 模型文件。对应的原生 Windows 安装器是 `.\cli\install-agent-instructions.ps1`，范围相同。

持久安装模式支持 `--force` 覆盖已有目标和 `--dry-run` 只显示 source/target 而不写文件；`--dry-run` 必须与 `--target` 一起使用。`--print` 与 `--target`、`--force`、`--dry-run` 互斥，且只向 stdout 输出可粘贴的指令块。

如果用户只要求读取 GitHub 仓库并使用 ListenKit 一次，可以跳过持久安装，直接运行公共入口。用户未指定 `--output` 时，优先使用 `work/<safe-source-stem>-transcript.md`；无法稳定取得 source stem 时使用 `work/transcript.md`。完成后应告知用户本次只使用了 ListenKit，未必完成持久化 Agent 安装。

## 公共入口

共享 Python CLI 是程序化事实来源。使用 Python 3.10+ 的 Agent 可在所有平台从仓库根目录执行同一命令：

```bash
python -m listenkit_cli generate-markdown \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --report-json work/sample-execution.json \
  --auto-init
```

当主机 Python 环境或 `PYTHONPATH` 不确定时，使用平台分发器。它会清理继承的 Python 环境变量并选择兼容的 CLI 解释器：

```bash
cli/listenkit.sh generate-markdown \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --report-json work/sample-execution.json \
  --auto-init
```

原生 Windows 使用对应的 PowerShell 分发器：

```powershell
.\cli\listenkit.ps1 generate-markdown `
  --url "https://example.com/video" `
  --language Japanese `
  --output work\sample-transcript.md `
  --report-json work\sample-execution.json `
  --auto-init
```

`cli/generate-markdown.sh` 和 `.\cli\generate-markdown.ps1` 仍是受支持的高层便捷包装器。`.sh` 仅用于 macOS/Linux/WSL；Git Bash、MSYS2 和 Cygwin 是原生 Windows 环境，不是 WSL，其中 `.sh` 入口会主动以退出码 64 失败。请使用 Python 或 PowerShell 分发器，不要把原生 Windows 路由到 WSL，因为 WSL 拥有独立的文件系统、运行时路径和 ASR 环境。

Windows 分发器会删除继承的 `PYTHONHOME`/`PYTHONPATH`，使用 UTF-8 标准输入输出，并按以下顺序探测 Python：显式 `LISTENKIT_CLI_PYTHON`、托管运行时、标准用户目录和 Program Files 的 Python 3.14、`py -3.14`、`python3.14`、`python`。CLI 主机需要 Python 3.10+；创建或修复托管 ASR 运行时仍需要真正的 Python 3.14。直接调用 `python -m listenkit_cli` 时，Windows 也会配置 UTF-8 流。

本地媒体输入时，将 `--url <url>` 替换为 `--input <path>`。

ListenKit 通过公共入口负责媒体获取、字幕选择、ASR fallback、转写规范化和纯文本转写渲染。外部 Agent 不得重复实现或绕过这些阶段。

自动 ASR 采用加速优先策略：Apple Silicon 使用准备好的 MLX/Metal 运行时，Windows/Linux NVIDIA 使用托管 CUDA。Agent 应保持引擎和设备为 `auto`，除非用户要求可复现的 CPU 执行，否则不得强制 CPU。`--auto-init` 授权创建或修复缺失的核心运行时。初始化和托管运行时转写可能下载加速依赖及选定模型。所有自动化入口默认非交互；缺失运行时必须返回错误，除非显式提供 `--auto-init` 或 `LISTENKIT_AUTO_INIT=1`。

URL 输入时，Markdown 标题默认使用平台视频标题（如果可用）；本地输入时默认使用源文件名。只有需要显式覆盖时才使用 `--title`。

## 输出契约

当输出路径为：

```text
work/sample-transcript.md
```

公共入口会生成：

- `work/sample-transcript.md`：可读的转写 Markdown
- `work/sample-transcript.json`：包含标准化文本、分段、来源引擎、实际设备、fallback 诊断、locale 和时间信息的结构化 JSON

下游 Agent 可按需要读取：

- 下一步需要阅读时使用 Markdown。
- 下一步需要结构化文本、分段、时间或引擎元数据时使用 JSON。

提供 `--report-json <path>` 时，ListenKit 还会原子写入独立的执行报告。报告记录 `status`、耗时、产物路径、实际引擎/设备元数据、fallback 诊断或结构化错误，不包含完整转写正文，也不得与 Markdown 或 transcript JSON 共用路径。

版本协商时，`doctor` 会在平台诊断前报告 `listenkit_version`、`doctor_schema_version`、`transcript_schema_version` 和 `execution_report_schema_version`。

完整字段与 schema 规则见 [`docs/output-format.md`](docs/output-format.md)。

## 可选音频片段导出

当下游流程已经选择明确的音频时间范围时，通过 ListenKit 导出片段：

```bash
cli/export-audio-slices.py \
  --input work/audio/source.m4a \
  --manifest work/source.slices.json \
  --output-dir work/slices \
  --padding-seconds 0.15 \
  --overwrite
```

manifest 是通用格式：

```json
{
  "version": 1,
  "slices": [
    {"id": "S01", "start": 4.0, "end": 19.0}
  ]
}
```

ListenKit 会校验范围、应用有界 padding、导出非空且同 stem 的 `SNN.m4a` 文件，并打印 JSON 报告。只有在下游明确需要带 padding 的重叠片段且能够处理报告中的 overlap 时，才使用 `--allow-overlap`。语义分组、标签、学习笔记渲染和应用记录仍由下游流程负责。

## 下游转换

ListenKit 在转写规范化和纯文本渲染处停止。Markdown 或 JSON 生成后，下游 Agent 可以将其转换为摘要、学习笔记、词汇表、复习卡或应用专属记录。这些转换不属于 ListenKit 契约，不得通过绕过 ListenKit 内部流程来实现。

## 不得绕过公共入口

正常集成不得直接调用以下命令作为捷径：

- `yt-dlp`
- `ffmpeg`
- `tools/*`
- `cli/extract-subtitles.sh`
- `cli/transcribe-audio.sh`
- `cli/import-audio.sh`
- `cli/render-listening-note.py`

Windows 对应的低层 `.ps1` 命令同样受此规则约束。直接调用低层接口只允许用于 ListenKit 自身调试或维护，详见 [`docs/debugging.md`](docs/debugging.md)。`cli/export-audio-slices.py` 是受支持的例外：下游已经选择明确时间范围时可以调用它。

## 隐私与版权

默认转写在本地完成，但下游 AI 编辑可能将转写文本和元数据发送给所使用的模型服务商。只处理你有权下载、录制、转写和学习的材料，不要使用本项目重新分发受版权保护的音频或转写稿。完整边界见 [`PRIVACY_AND_COPYRIGHT.md`](PRIVACY_AND_COPYRIGHT.md)。
