# 项目专有工程与治理约束

## 1. 运行时与环境隔离

- 托管 `faster-whisper` / `mlx-whisper` 运行时固定使用受支持的独立 Python 3.14 环境，位于仓库外和 iCloud Drive 外的隔离路径。
- 禁止在仓库内建立临时虚拟环境替代项目隔离运行时。
- CLI 主机兼容 Python 3.10+。

## 2. 文本与 I/O 契约

- 全局强制使用 UTF-8 I/O 与 LF 换行符（参考 `.gitattributes`）。
- 自动化命令默认非交互运行，自动清理可能干扰运行时的 `PYTHONHOME` 与 `PYTHONPATH`。

## 3. 契约与公共入口唯一性

- 正常转写集成 MUST 调用公共入口 `python -m listenkit_cli generate-markdown` 或平台分发器（`cli/listenkit.sh`、`cli/listenkit.ps1`）。
- 禁止为绕过公共流程而直接调用 `yt-dlp`、`ffmpeg` 或 `tools/*`；低层接口仅限项目自测。
- Transcript schema 当前固定为 v1，必须使用原子方式写入文件，执行报告必须独立于转写产物输出。

## 4. 交付前全量验证流水线

交付代码、公共契约或 Spec Kit 工件变更前必须通过：

```bash
# 源码编译与测试
python -m compileall -q listenkit_cli cli tools
python -m unittest discover -s tests -v

# Spec Kit 治理与集成健康检查
specify integration status --json
python3 tools/spec-kit-governance/governance.py verify
```
