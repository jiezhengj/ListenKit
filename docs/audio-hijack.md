# Audio Hijack

Audio Hijack 是一种可选的采集方式，适用于无法直接下载的来源。

推荐流程：

1. 创建一个录制目标应用或系统音频的 session。
2. 将录音保存为 WAV、AIFF、M4A 或 MP3。
3. 在片段结束后停止录音。
4. 从本地文件生成转写产物：

```bash
cli/generate-markdown.sh \
  --input ~/Music/AudioHijack/session-recording.wav \
  --language Japanese \
  --output work/my-recording.md \
  --auto-init
```

这会同时写入 `work/my-recording.md` 和 `work/my-recording.json`。

本项目 v1 不自动配置或控制 Audio Hijack。
