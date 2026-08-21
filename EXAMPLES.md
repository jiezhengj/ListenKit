# 渲染器 fixture 示例

仓库中的示例是合成数据，可以安全重新分发。

仓库不附带音频文件。这些示例用于维护者测试渲染器，使用合成的 transcript JSON，不是外部集成入口。外部集成应使用 `cli/listenkit.sh generate-markdown`；详见 `LLM_INTEGRATION.md`。

## 日语示例

```bash
cli/render-listening-note.py \
  --source-ref examples/sample-ja.m4a \
  --transcript-json examples/sample-transcript-ja.json \
  --title "Japanese Cafe Description" \
  --language Japanese \
  --output examples/sample-note-ja.md
```

## 英语示例

```bash
cli/render-listening-note.py \
  --source-ref examples/sample-en.m4a \
  --transcript-json examples/sample-transcript-en.json \
  --title "English Library Description" \
  --language English \
  --output examples/sample-note-en.md
```

## 预期 Markdown 结构

每个渲染后的 Markdown 文件都包含：

- `Source`
- `Transcript`

当前 schema v1 fixture 还展示实际 ASR 设备和计算元数据。这些合成示例使用 `cpu` + `int8`；真实输出记录实际执行的 backend 和 accelerator。

渲染器不添加学习分析章节。下游项目可以从 transcript JSON 或 Markdown 构建自己的笔记模板。
