---
name: generate-markdown
description: 从 URL 或本地音视频生成 transcript Markdown 和同 stem transcript JSON。
---

# 生成 Markdown

当用户希望 ListenKit 从一个网络音视频 URL 或本地音视频文件生成转写产物时使用本技能。

## 流程

1. 确认只有一个输入源：URL 或本地媒体路径。
2. 选择输出 Markdown 路径和用户要求的语言标签。
3. 从仓库根目录运行共享程序化入口：`python -m listenkit_cli generate-markdown`。主机 Python 环境不确定时，在 macOS/Linux/WSL 使用 `cli/listenkit.sh generate-markdown`，原生 Windows 使用 `.\cli\listenkit.ps1 generate-markdown`。

Git Bash、MSYS2 和 Cygwin 是原生 Windows，不是 WSL；`.sh` 入口会以退出码 64 失败。stdout 捕获不可靠时使用 Python 或 PowerShell 分发器并读取 `--report-json`。

包装器从 `--language` 推导 ASR locale。URL 输入时，Markdown 标题默认使用可用的平台视频标题；本地输入时默认使用源文件名。只有需要覆盖时才使用 `--locale` 或 `--title`。

对于 `--output work/name.md`，包装器同时写入 `work/name.md` 和 `work/name.json`。可读转写使用 Markdown；下游结构化转换使用 JSON。

URL 输入会优先尝试平台字幕。字幕可用时从字幕渲染并跳过 ASR，同时仍尝试导入本地音频供听力使用；字幕不可用时回退到导入音频和 ASR。

下游流程已经选择明确时间范围时，使用 `cli/export-audio-slices.py --input <audio> --manifest <json> --output-dir <dir>` 导出片段。ListenKit 校验并导出范围；语义分组仍由下游负责。只有重叠 padding 确实有意时才加 `--allow-overlap`。

## 规则

- ListenKit 输出只包括 transcript Markdown 和同 stem transcript JSON。
- 下游明确请求片段时使用 `cli/export-audio-slices.py`，不要直接使用原始 `ffmpeg`。
- 保持 ASR 引擎和设备为自动默认值；只有用户明确要求可复现 CPU 执行时才强制 CPU。
- 不要通过本技能暴露已有音频、已有 transcript JSON、字幕提取、ASR、导入、渲染、原始下载器或 `tools/*` 工作流；这些只属于 ListenKit 调试和维护。
- 除非下游项目明确要求，不添加学习笔记模板、Obsidian frontmatter、wikilinks、Anki 卡片或复习计划。
- 将语言学习分析留在通用转写技能之外。
- 遵守版权，不帮助重新分发受版权保护的转写稿或音频。

## CLI 示例

URL 输入：

```bash
cli/listenkit.sh generate-markdown \
  --url "https://example.com/video" \
  --language Japanese \
  --output work/sample-transcript.md \
  --report-json work/sample-execution.json \
  --auto-init
```

本地媒体：

```bash
cli/listenkit.sh generate-markdown \
  --input ~/Desktop/recording.wav \
  --language English \
  --output work/recording-transcript.md \
  --report-json work/recording-execution.json \
  --auto-init
```

原生 Windows 使用相同选项的 PowerShell 语法：

```powershell
.\cli\listenkit.ps1 generate-markdown `
  --input "C:\Media\recording.wav" `
  --language English `
  --output work\recording-transcript.md `
  --report-json work\recording-execution.json `
  --auto-init
```
