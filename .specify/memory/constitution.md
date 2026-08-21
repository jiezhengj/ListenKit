<!--
同步影响报告
- 版本变更：占位模板 → 1.0.0
- 新增原则：公共入口与边界唯一；契约与模式优先；本地优先与运行时隔离；
  跨平台与非交互；测试与证据；适配器瘦身与中文文档。
- 新增章节：约束与边界；开发与验证流程。
- 删除内容：所有未定义的模板占位符。
- 后续事项：无。
-->

# ListenKit 项目宪章

## 核心原则

### I. 公共入口与边界唯一

ListenKit 的正常集成 MUST 通过 `python -m listenkit_cli generate-markdown` 或平台分发器调用共享公共入口。入口统一负责媒体获取、字幕选择、ASR fallback、转写规范化和 Markdown 渲染；Agent 适配器和下游应用 MUST NOT 重复实现或绕过这些阶段。音频片段导出仅在下游已经确定明确时间范围时作为受支持的补充接口使用。

### II. 契约与模式优先

所有跨进程和下游可消费的输出 MUST 遵守已记录的 transcript JSON 与执行报告契约。内置 transcript schema 当前为 v1；读取方 MUST 拒绝明确声明但未知的模式版本，不得猜测其含义。Markdown、transcript JSON 和 execution report MUST 保持职责分离；文件写入 MUST 使用原子方式，执行报告 MUST NOT 复用转写产物路径。

### III. 本地优先与运行时隔离

默认转写 MUST 优先使用本地 ASR。托管 ASR 运行时 MUST 使用受支持的 Python 3.14，并置于仓库外、iCloud Drive 外的隔离路径；不得通过仓库内临时虚拟环境替代项目运行时。自动初始化必须由 `--auto-init` 或等价的显式授权触发；诊断命令 MUST 保持只读，不得修改系统 Python、系统 CUDA 驱动或调用方环境。

### IV. 跨平台与非交互行为

共享 Python 核心、macOS/Linux/WSL 分发器和原生 Windows PowerShell 分发器 MUST 保持一致的参数、输出和错误契约。自动化入口 MUST 默认非交互、使用 UTF-8 I/O，并清理可能污染运行时选择的 `PYTHONHOME` 与 `PYTHONPATH`。平台能力、权限和硬件加速的结论只有在对应平台完成验证后才能写入文档或作为支持承诺。

### V. 测试与证据优先

涉及公共契约、运行时策略、跨平台分发、输出模式或 Agent 集成的变更 MUST 同步更新针对性测试和文档。交付前 MUST 运行 Python 源码编译检查和完整 unittest；CI MUST 覆盖项目声明支持的平台，真实运行时或硬件结论 MUST 有匹配的设备验证。规格、计划、任务、测试结果和收敛结论必须能够互相追踪。

### VI. 适配器瘦身与中文文档

Agent-specific 文件 MUST 只描述共享契约和调用方式，不得加入 provider-specific 业务逻辑。项目维护的所有文档（包括 README、规范、计划、任务、清单、架构说明、Agent 集成说明和变更说明）MUST 使用中文；代码、API 名称、命令、文件路径、协议字段、配置键和上游专有名词保留原文，并在必要时补充中文解释。Spec Kit 生成的、由 manifest 管理的工具技能文件属于工具基础设施，MUST NOT 被项目手工改写。

## 约束与边界

- `LLM_INTEGRATION.md` 是外部 Agent 集成契约的事实来源，`adapters/agent/listenkit-agent-instructions.md` 必须与其关键不变量保持同步。
- CLI 主机兼容 Python 3.10+；托管 faster-whisper 运行时固定使用 Python 3.14。不得以直接调用 `yt-dlp`、`ffmpeg`、`tools/*` 或低层 CLI 作为正常集成捷径。
- 下游摘要、学习笔记、词卡、间隔复习和应用专属记录不属于 ListenKit 核心转写契约。
- 只处理用户有权使用的媒体和文本；文档不得暗示 ListenKit 提供受版权保护的音频或转写内容。

## 开发与验证流程

- 实质性功能、行为变更、兼容性变更和复杂缺陷 MUST 按 Spec Kit 生命周期推进：`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → validate → converge`。低风险文字修正和只读调查可省略不适用的阶段。
- 接受规格后，实施只能修改计划和任务明确的范围；若实现暴露出需求或假设错误，必须先更新对应 Spec Kit 工件，不得静默偏离。
- `validate` 必须记录测试、构建、静态检查、模式检查和平台验证结果；`converge` 必须在宣告完成前确认规格、计划、任务、实现和验证一致。
- Git 提交前必须检查工作区、diff、未跟踪文件和换行符；PR 描述必须说明规格工件、实现范围、验证结果和已知限制。

## 治理

本宪章是项目级工程约束。任何变更必须在同一 PR 中更新同步影响报告、版本号和受影响的 Spec Kit 工件，并说明为什么现有原则仍然适用或需要调整。版本遵循语义化版本：新增或实质扩展原则递增 MINOR，删除或重新定义原则递增 MAJOR，澄清和非语义修订递增 PATCH。每次涉及代码或公共契约的 PR 都必须检查本宪章、运行适用验证，并由收敛检查确认没有未覆盖的需求或任务。复杂度增加必须有明确的需求依据；不得以生成备份、重复文档或未追踪的临时结构掩盖迁移不完整。

**版本**：1.0.0 | **批准日期**：2026-08-21 | **最后修订**：2026-08-21
