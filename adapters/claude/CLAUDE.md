# ListenKit

使用仓库 CLI，不要在提示文本中重实现 pipeline。优先从仓库根目录调用 `python -m listenkit_cli generate-markdown`；主机 Python 环境不确定时，在 macOS/Linux/WSL 使用 `cli/listenkit.sh generate-markdown`，原生 Windows 使用 `.\cli\listenkit.ps1 generate-markdown`。

正常流程：

```bash
cli/listenkit.sh generate-markdown \
  --url <url> \
  --language <label> \
  --output <md> \
  --report-json <execution-json> \
  --auto-init
```

高层命令也接受单一输入源 `--input <path>`，并从 `--language` 推导 ASR locale。URL 标题默认使用平台标题；本地标题默认使用源文件名，除非显式覆盖。

保持 ASR 引擎和设备为自动默认值。只有用户明确要求可复现的 CPU 执行时才强制 CPU。

对于 `--output path/name.md`，将 `path/name.md` 作为可读转写，将 `path/name.json` 作为结构化产物。stdout 捕获不可靠时读取 execution report，不要修改 ListenKit 以迁就 Claude 宿主的 PATH 或 shell。

URL 输入会优先尝试平台字幕，同时尝试导入本地音频；字幕不可用时回退到导入音频和 ASR。

正常集成不得调用低层导入、字幕提取、ASR、渲染、原始下载器或 `tools/*`；这些只用于 ListenKit 调试和维护。

输出保持为 transcript JSON 或纯 transcript Markdown。除非下游项目明确要求，不添加学习笔记模板、Obsidian 语法、Anki 卡片或复习计划。

Windows 参数和输出契约相同。原生 Windows 不得通过 WSL；Git Bash/MSYS2/Cygwin 是原生 Windows，`.sh` 入口会以退出码 64 失败，请使用 Python 或 PowerShell 分发器。宿主 stdout、shell 或 PATH 有问题时优先使用 `--report-json`。

只处理你有权下载、录制、转写和学习的材料；不要重新分发受版权保护的音频或转写稿。完整边界见 `PRIVACY_AND_COPYRIGHT.md`。
