# 输出格式

渲染后的转写 Markdown 使用固定的章节契约：

```markdown
# Title

## Source

## Transcript
```

## 章节规则

- `Source`：来源引用或音频文件名、语言、locale、转写引擎、实际 ASR 设备和计算类型（可用时）、加速 fallback 原因（适用时）、时间状态和生成时间。
- `Transcript`：经过轻度空格和段落清理的 ASR 文本。

格式保持为纯 Markdown。ListenKit 不添加学习分析章节；下游项目可以将转写内容转换为自己的笔记格式。

## Transcript JSON

内置后端输出 schema v1：

```json
{
  "schema_version": 1,
  "engine": "faster-whisper",
  "device": "cuda",
  "device_index": 0,
  "device_name": "NVIDIA GeForce RTX 4070",
  "compute_type": "float16",
  "locale": "ja-JP",
  "full_text": "...",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "timing_complete": true
}
```

必需语义字段为 `engine`、`locale`、`full_text`、`segments` 和 `timing_complete`。没有 `schema_version` 的旧 payload 按 legacy v1 读取；显式声明未知 schema version 时必须拒绝，不能猜测含义。

faster-whisper payload 还会报告选定的 `device`、`device_index` 和 `compute_type`。有 NVIDIA 元数据时会加入 `device_name`。自动 CUDA 执行发生 fallback 时，`fallback_from` 列出失败的设备/类型尝试，`fallback_reason` 记录有界诊断。

MLX Whisper payload 使用 `engine: "mlx-whisper"`、`device: "metal"`、设备索引 `0` 和 `compute_type: "float16"`。渲染后的 Markdown 包含实际引擎、设备和计算元数据。自动 MLX 不可用时，执行的 faster-whisper 引擎/设备会使 fallback 路径可见；CUDA 尝试失败时还会使用 `fallback_from` 和 `fallback_reason`。

### Backend 错误 payload

如果 backend 失败并输出 JSON，错误 payload 是终止状态，必须把 `error` 对象作为顶层第一个字段：

```json
{
  "error": {
    "type": "backend_error",
    "message": "human-readable failure reason"
  }
}
```

渲染器和适配器不得将错误 payload 当作转写稿渲染；必须暴露错误并要求用户修复 backend 或重试。明确声明但未知的 schema version 同样必须拒绝，不能猜测其含义。

## Execution Report JSON

`generate-markdown` 和 `transcribe-audio` 接受 `--report-json <path>`。execution report 是独立且原子写入的状态产物，不替代同 stem 的 transcript JSON，并且有意省略完整转写正文。

成功示例：

```json
{
  "schema_version": 1,
  "listenkit_version": "1.0.0",
  "command": "generate-markdown",
  "status": "ok",
  "started_at": "2026-08-10T10:00:00Z",
  "finished_at": "2026-08-10T10:00:08Z",
  "duration_seconds": 8.0,
  "outputs": {
    "markdown": "work/sample.md",
    "transcript_json": "work/sample.json"
  },
  "transcription": {
    "schema_version": 1,
    "engine": "mlx-whisper",
    "device": "metal",
    "compute_type": "float16",
    "locale": "en-US",
    "timing_complete": true
  }
}
```

失败时 `status` 为 `error`，`error` 对象包含异常类型和消息。报告路径必须与 Markdown 和 transcript JSON 路径不同。调用方遇到未知 execution-report schema version 时应视为不支持，不能猜测其含义。
