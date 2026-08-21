# Cursor 规则：ListenKit

在本仓库中工作时，以 CLI 作为事实来源：

- `python -m listenkit_cli generate-markdown`：跨平台程序化入口
- `cli/listenkit.sh generate-markdown`：macOS/Linux/WSL 主机 Python 环境不确定时使用
- `.\cli\listenkit.ps1 generate-markdown`：原生 Windows 分发器
- `generate-markdown --output path/name.md`：同时生成 `path/name.json` 结构化产物
- URL 流程优先尝试平台字幕，同时导入本地听力音频
- 低层导入、字幕提取、ASR、渲染、原始下载器和 `tools/*` 仅用于调试和维护

不要在编辑器规则中重复业务逻辑。宿主需要文件化执行状态时使用 `--report-json`。

macOS/Linux/WSL 使用 `.sh`，原生 Windows 使用 `.ps1`；Git Bash 不是 WSL，WSL 不得作为 Windows 路径的透明包装器。Git Bash/MSYS2/Cygwin 中 `.sh` 入口会以退出码 64 失败，请使用 Python 或 PowerShell。

保持 ASR 引擎和设备为自动默认值。只有用户明确要求可复现的 CPU 执行时才强制 CPU。

预期 Markdown 输出包含：

- `Source`
- `Transcript`

本适配器只负责转写生成。除非下游项目明确要求，不添加学习笔记、Obsidian、Anki 或复习系统结构。

只处理你有权下载、录制、转写和学习的材料；不要重新分发受版权保护的音频或转写稿。完整边界见 `PRIVACY_AND_COPYRIGHT.md`。
