# 项目文档与契约治理基线

**功能分支**：`codex/spec-kit-migration`

**创建日期**：2026-08-21

**状态**：已接受，迁移实施中

**输入**：将现有 ListenKit 工程迁移为标准 Spec Kit 项目，统一项目文档语言，保留公共契约与验证证据，消除过时和重复的治理入口。

## 用户场景与测试

### 用户故事 1——维护者能够找到唯一的中文项目文档入口（优先级：P1）

作为 ListenKit 维护者，我希望 README、安装说明、Agent 集成契约、后端说明和输出格式说明都使用中文，并且每类事实只有一个权威入口，从而能够在修改项目时快速判断应该更新哪份文档。

**为什么是这个优先级**：语言与权威入口是后续规格、计划和 PR 审查的基础；如果文档互相冲突，任何迁移都无法可靠收敛。

**独立测试**：逐项检查项目维护的 Markdown 文档，确认中文正文、清晰的文档路由和无重复的权威说明；对每个公共契约事实都能定位到唯一权威文档。

**验收场景**：

1. **给定**维护者从仓库根目录开始，**当**阅读 README 和文档索引，**那么**能够用中文找到安装、集成、输出格式、后端和调试说明。
2. **给定**维护者要修改 Agent 集成行为，**当**查找事实来源，**那么** `LLM_INTEGRATION.md`、可安装摘要和适配器之间的职责边界是明确且不互相矛盾的。
3. **给定**一份历史计划已被实现，**当**维护者查阅项目文档，**那么**不会把历史方案误认为当前实施计划。

### 用户故事 2——Agent 能够按稳定契约使用 ListenKit（优先级：P1）

作为外部 Agent，我希望只调用 ListenKit 的公共入口，并获得 Markdown、transcript JSON 和 execution report 的稳定说明，从而不需要重实现下载、字幕、ASR 或渲染流程。

**为什么是这个优先级**：这是项目对外集成的核心价值，契约漂移会直接造成下游失败或数据损坏。

**独立测试**：根据契约文档执行入口帮助检查和模拟本地流程，确认参数、产物路径、schema v1、错误行为和非交互初始化规则一致。

**验收场景**：

1. **给定**Agent 处理 URL 或本地媒体，**当**调用 `python -m listenkit_cli generate-markdown` 或平台分发器，**那么**能够获得 Markdown 和同名 transcript JSON，并可选获得独立的 execution report。
2. **给定**下游只需要导出已经确定的时间片段，**当**调用公开片段导出接口，**那么**不会要求 ListenKit 推断语义分组，也不会绕过转写公共入口。
3. **给定**运行时缺失或 schema 版本未知，**当**入口执行，**那么**自动化流程得到结构化错误或明确不支持结果，不会静默猜测或交互阻塞。

### 用户故事 3——贡献者能够用 Spec Kit 追踪治理变更（优先级：P2）

作为贡献者，我希望项目拥有 constitution、spec、plan、tasks、checklist、validation 和 convergence 工件，从而能在修改公共契约或跨平台行为时追踪需求、实现、测试和收敛状态。

**为什么是这个优先级**：它不改变用户运行时行为，但能降低后续跨平台和 Agent 集成变更的回归风险。

**独立测试**：运行 Spec Kit integration status，检查基线 feature 的工件完整性，并将任务、实现位置和测试结果逐项映射。

**验收场景**：

1. **给定**仓库已经初始化 Spec Kit，**当**运行 `specify integration status --json`，**那么** Codex integration 的管理文件完整且未被手工改写。
2. **给定**贡献者审查一次治理变更，**当**查看 feature 工件，**那么**能够从需求 ID追踪到任务、项目文件、测试和验证结果。

### 边界情况

- Spec Kit 生成的、由 manifest 管理的技能文件包含英文模板文本；它们属于工具基础设施，不作为项目维护文档翻译，也不得手工改写导致 integration 漂移。
- 代码、命令、API 名称、路径、schema 字段和上游专有名词保留原文，但周围说明使用中文。
- 既有文档中的有效公共契约必须保留；如果内容已成为当前契约，应归并到唯一权威页，而不是复制到每个 Spec Kit 工件。
- 历史计划可以删除，不需要保留备份；删除前必须将仍然有效的决策、测试和边界转移到当前工件或权威文档。
- 本次迁移不改变 ListenKit 的 Python、CLI、ASR、输出 schema、运行时路径或平台支持范围。

## 需求

### 功能需求

- **FR-001**：项目 MUST 在根目录拥有可被当前 Spec Kit CLI 识别的 `.specify/`，并安装可验证的 Codex integration。
- **FR-002**：项目 MUST 维护一份中文 constitution，明确公共入口、输出契约、运行时隔离、跨平台、测试证据、适配器边界和文档语言原则。
- **FR-003**：项目维护的 README、集成契约、安装、后端、输出格式、调试、隐私和适配器说明 MUST 使用中文正文；代码、命令、路径、字段和专有名词可以保留原文。
- **FR-004**：公共 Agent 集成契约 MUST 继续以 `LLM_INTEGRATION.md` 为事实来源，且必须明确 `generate-markdown`、transcript JSON、execution report、初始化授权和不得绕过入口的规则。
- **FR-005**：输出格式说明 MUST 继续定义 transcript JSON schema v1 的必需字段、旧 payload 兼容策略、未知版本拒绝策略和 execution report 的独立路径规则。
- **FR-006**：原有一键安装方案中的有效用户流程、测试意图和边界 MUST 被迁移到当前 Spec Kit 工件或权威项目文档；已实现且过时的计划文件 MUST NOT 继续作为当前计划入口。
- **FR-007**：基线 feature MUST 包含 `spec.md`、`plan.md`、`tasks.md`、需求质量 checklist、validation 和 convergence，并在其中建立需求、文件和测试的可追踪关系。
- **FR-008**：迁移 MUST NOT 修改应用源代码或改变公共运行时行为；所有既有公共契约事实、平台边界、隐私版权限制和验证入口必须可在迁移后的文档中定位。
- **FR-009**：迁移 MUST 删除不再承担权威职责的重复或过时文档，不得以备份副本、同义计划或重复全文制造第二套事实来源。
- **FR-010**：提交前 MUST 通过 Spec Kit integration status、Python 编译检查、完整 unittest、Git diff 审查和工作区状态审查；推送前 MUST 确认目标分支和 PR 只包含本次迁移内容。

### 关键实体

- **公共集成契约**：描述外部 Agent 如何调用 ListenKit、读取产物以及遵守边界的稳定规则集合。
- **转写产物契约**：描述 Markdown、transcript JSON 和 execution report 的字段、版本、路径和错误语义。
- **Spec Kit 工件**：包括 constitution、spec、plan、tasks、checklist、validation 和 convergence，用于追踪治理变更。
- **验证证据**：包括测试文件、CI job、命令、运行结果和需要真实设备确认的限制。

## 成功标准

### 可度量结果

- **SC-001**：除 Spec Kit 生成且由 manifest 管理的工具技能文件外，项目维护的 Markdown 文档正文全部使用中文；代码、命令、路径、字段和专有名词保持可复制。
- **SC-002**：`specify integration status --json` 返回 `status: ok`，Codex integration 的 managed files 缺失数和修改数均为 0。
- **SC-003**：基线 feature 至少包含 7 类可审查工件：spec、plan、tasks、requirements checklist、validation、convergence，以及由项目 constitution 提供的治理约束。
- **SC-004**：迁移后的需求 ID、任务 ID、项目文件和测试证据均可逐项映射；核心需求的任务覆盖率达到 100%。
- **SC-005**：`python3 -m compileall -q listenkit_cli cli tools` 通过，`python3 -m unittest discover -s tests -v` 的全部非平台跳过测试通过，且测试数量与迁移前基线一致或增加。
- **SC-006**：Git 对比确认没有应用源代码的非必要改动；所有删除的文档均已完成价值转移，且仓库中不存在同一契约的重复权威版本。
- **SC-007**：迁移分支可以推送到 GitHub，并创建一个只描述本次 Spec Kit/文档治理迁移的 PR；PR 中包含验证结果、已知平台限制和文件清单。

## 假设

- 本次迁移使用当前已安装的 Spec Kit CLI `0.16.6.dev0` 和 Codex integration，不手工复制全局技能。
- `README.md` 作为 GitHub 默认入口保留；与其内容重复的语言镜像文件可以合并或删除。
- `LLM_INTEGRATION.md`、`docs/output-format.md` 和 `docs/backends.md` 等权威说明继续保留，但只保留各自职责范围，不把整篇内容复制到 feature 工件。
- 本次 PR 的目标仓库是 `origin` 指向的 `https://github.com/jiezhengj/ListenKit.git`；上游仓库是 `upstream` 指向的 `https://github.com/feiyanqiqiao/ListenKit.git`。
