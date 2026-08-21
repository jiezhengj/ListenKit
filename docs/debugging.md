# 调试与维护接口

本文档面向 ListenKit 维护者和集成调试，不是外部 LLM Agent 的公共契约。

正常集成应调用首选分发器：

```bash
cli/listenkit.sh generate-markdown (--url <url>|--input <path>) --language <label> --output <md>
```

原生 Windows：

```powershell
.\cli\listenkit.ps1 generate-markdown (--url <url>|--input <path>) --language <label> --output <md>
```

命令还会在 Markdown 旁写入同 stem 的 transcript JSON。外部 Agent 应读取该 JSON，不要直接调用更低层的接口。

## 公开片段导出

已经负责语义分组的下游流程可以调用：

```bash
cli/export-audio-slices.py --input <audio> --manifest <json> --output-dir <dir>
```

这是公开的补充接口，不是转写阶段。它接受明确时间范围，不推断句子、对话分组或应用元数据；默认会在相邻边界裁剪 padding，只有确实需要重叠 padding 时才使用 `--allow-overlap`。

## 低层 CLI

以下命令仍用于测试、维护、缓存和 pipeline 调试：

- `cli/import-audio.sh`：网址或本地媒体 -> 本地音频文件
- `cli/extract-subtitles.sh`：URL 字幕 -> transcript JSON
- `cli/transcribe-audio.sh`：本地音频文件 -> transcript JSON
- `cli/render-listening-note.py`：transcript JSON -> transcript Markdown

原生 Windows 提供对应的 `.ps1` 命令。平台 `doctor` 命令只读报告解析后的依赖和运行时健康状态；Windows/Linux 诊断包含 NVIDIA 驱动、托管 CUDA 库、设备和计算类型，macOS 诊断包含架构、MLX/Metal、版本、模型缓存和自动引擎。CUDA 或 MLX 准备只在初始化或托管运行时转写前执行，不在 `doctor` 中执行。

仅在调查特定阶段或维护 ListenKit 时使用这些命令。

## 后端 helper

`tools/` 下的 helper 都是实现细节：

- `tools/subtitles/vtt_to_transcript_json.py`
- `tools/faster-whisper/transcribe.py`
- `tools/mlx-whisper/transcribe.py`
- `tools/apple-speech-helper/`

外部 Agent 不得调用这些文件。它们由 CLI 包装，以确保公共 transcript 形状一致。

## 原始下载器调用

不要把原始 `yt-dlp` 字幕或音频命令作为集成捷径。ListenKit 的包装器负责字幕优先级、单条 URL 行为、音频转换、输出位置和 transcript 规范化。

只有调试下载器行为或编写 ListenKit 内部专项测试时，才允许直接调用原始下载器。
