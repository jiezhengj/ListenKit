# 任务：项目文档与契约治理基线

**输入**：`spec.md`、`plan.md`、`research.md`、`data-model.md`、`quickstart.md`

**任务格式**：`[ID] [P?] [US#] 描述`

**范围约束**：本 feature 不修改 ListenKit 应用源代码；Spec Kit 生成且由 manifest 管理的文件不得手工改写。

## 阶段 1：初始化与治理基础设施

**目的**：建立可识别、可验证的 Spec Kit 项目基础。

- [x] T001 [P] [US3] 核对 `.specify/init-options.json`、`.specify/integration.json` 和 Codex manifest，确认项目使用 `codex` integration per FR-001。
- [x] T002 [P] [US3] 将项目文档语言、Agent 入口和交付前检查规则写入 `AGENTS.md` per FR-003。
- [x] T003 [US3] 用现有公共契约和测试证据填充 `.specify/memory/constitution.md`，完成版本、日期和同步影响报告 per FR-002。
- [x] T004 [P] [US3] 保持 `.agents/skills/` 和 `.specify/integrations/*.manifest.json` 的生成内容一致，不修改 manifest 管理的技能文件 per FR-001。

## 阶段 2：基础事实与追踪结构

**目的**：为所有用户故事建立唯一事实来源和验证映射。

- [x] T005 [P] [US3] 创建并复核 `specs/001-documentation-contract-governance/research.md`，记录权威文档、去重和语言决策 per FR-006/FR-009。
- [x] T006 [P] [US3] 创建并复核 `specs/001-documentation-contract-governance/data-model.md`，定义文档事实、Spec Kit 工件、任务和验证证据的关系 per FR-007。
- [x] T007 [P] [US3] 创建并复核 `specs/001-documentation-contract-governance/quickstart.md`，列出 integration status、编译、unittest、diff 和文档审计命令 per FR-010。
- [x] T008 [US3] 生成 `specs/001-documentation-contract-governance/checklists/requirements.md`，完成需求质量审查并保留未完成实现项与质量审查的区别 per FR-007。

**检查点**：constitution、spec、研究记录和设计追踪结构完成后，进入文档迁移。

## 阶段 3：用户故事 1——中文且无重复的文档入口（优先级：P1）

**目标**：项目维护文档统一为中文，并按职责保留唯一权威入口。

**独立测试**：逐个阅读维护文档，确认中文正文、唯一职责和命令/字段可复制；运行文档审计搜索确认没有过时计划入口。

- [x] T009 [P] [US1] 将现有有效内容整理为中文 `README.md`，保留 Quick Try、Agent 安装、文档路由、功能边界、适配器和隐私版权入口 per FR-003。
- [x] T010 [P] [US1] 删除与中文 `README.md` 重复的 `README.zh-CN.md`，并确认有效内容已转移 per FR-009。
- [x] T011 [P] [US1] 将 `LLM_INTEGRATION.md` 翻译为中文，保留完整安装、公共入口、输出契约、片段导出和不得绕过规则 per FR-004。
- [x] T012 [P] [US1] 将 `docs/install.md`、`docs/backends.md`、`docs/debugging.md`、`docs/audio-hijack.md` 和 `docs/output-format.md` 翻译为中文，并按职责去除重复说明 per FR-003/FR-005。
- [x] T013 [P] [US1] 将 `EXAMPLES.md`、`PRIVACY_AND_COPYRIGHT.md` 和 `templates/listening-note.md` 的项目说明整理为中文，保留样例数据和输出契约字面量 per FR-003。
- [x] T014 [P] [US1] 将 `adapters/agent/listenkit-agent-instructions.md`、`adapters/claude/CLAUDE.md`、`adapters/codex/SKILL.md` 和 `adapters/cursor/foreign-listening.md` 的维护说明整理为中文，保持适配器无业务逻辑 per FR-003。
- [x] T015 [US1] 将 `docs/one-click-agent-install-plan.md` 中仍有效的流程、测试意图和边界核对到 spec/plan/tasks 后删除该历史计划 per FR-006/FR-009。

**检查点**：维护者从 `README.md` 可以找到中文文档路由；历史计划不再作为当前实施入口。

## 阶段 4：用户故事 2——稳定的 Agent 公共契约（优先级：P1）

**目标**：确保文档迁移不改变 Agent 的入口、产物、schema 和错误语义。

**独立测试**：运行现有 CLI 帮助和模拟测试，核对文档中的契约字面量与代码/测试使用一致。

- [x] T016 [P] [US2] 对照 `listenkit_cli/cli.py`、`listenkit_cli/workflow.py` 和 `LLM_INTEGRATION.md`，核对 `generate-markdown` 的参数、标题和产物路径 per FR-004。
- [x] T017 [P] [US2] 对照 `docs/output-format.md`、`listenkit_cli/transcription.py`、`listenkit_cli/execution_report.py` 和相关测试，核对 schema v1、错误 payload、原子写入和 report 独立路径 per FR-005。
- [x] T018 [P] [US2] 对照 `docs/backends.md`、`docs/install.md`、运行时模块和跨平台测试，核对 Python 3.14、隔离路径、auto-init、CUDA/MLX fallback 和非交互行为 per FR-004/FR-008。
- [x] T019 [US2] 检查 `adapters/*` 仅调用共享入口、不重复实现媒体获取、字幕、ASR 或渲染；记录任何不一致并修正文档而不修改应用逻辑 per FR-004/FR-008。

## 阶段 5：用户故事 3——可追踪的 Spec Kit 交付（优先级：P2）

**目标**：形成从需求到验证和收敛的完整治理记录。

- [x] T020 [P] [US3] 建立 `specs/001-documentation-contract-governance/validation.md`，将 FR/SC 映射到文件、测试、CI job、运行结果和平台限制 per FR-007/FR-010。
- [x] T021 [P] [US3] 检查 `specs/001-documentation-contract-governance/spec.md`、`plan.md`、`tasks.md` 和 checklist 没有占位符、互相冲突或复制完整权威契约 per FR-007。
- [x] T022 [US3] 运行 `specify integration status --json`，确认 managed files 缺失数和修改数为 0 per SC-002。
- [x] T023 [US3] 运行 `python3 -m compileall -q listenkit_cli cli tools` 和 `python3 -m unittest discover -s tests -v`，记录总数、通过数、跳过数及平台限制 per SC-005。
- [x] T024 [US3] 运行 Git diff、`git diff --check`、删除文件价值转移审计和文档重复搜索，确认无应用源代码的非必要变更 per SC-006。

## 阶段 6：收敛、提交与交付

**目的**：完成实施后的规格一致性检查，并为 GitHub PR 准备证据。

- [x] T025 [US3] 创建 `specs/001-documentation-contract-governance/convergence.md`，逐项记录需求、任务、实现文件、验证证据和剩余平台限制 per FR-007/SC-004。
- [x] T026 [US3] 将已完成任务标记为 `[x]`，对任何未完成项追加明确的 convergence 任务，不得静默宣告完成 per FR-007。
- [x] T027 [US3] 检查仓库根目录 `.gitattributes`、工作区、未跟踪文件、分支名和提交范围，确保只包含本次迁移且没有有价值内容丢失 per FR-010。
- [x] T028 [US3] 提交迁移分支，推送 `codex/spec-kit-migration` 到 `origin`，并创建指向 `upstream/main` 的 GitHub PR per SC-007。

## 阶段 7：Convergence——补齐契约遗漏

**目的**：处理迁移后审计发现的公共契约遗漏，不改写前序任务记录。

- [x] T029 [US1] 在 `README.md`、`docs/install.md` 和 `LLM_INTEGRATION.md` 保留 Windows 执行策略受限时的 `powershell -NoProfile -ExecutionPolicy Bypass -File` 恢复路径。
- [x] T030 [US1] 在 `LLM_INTEGRATION.md` 和 `adapters/agent/listenkit-agent-instructions.md` 记录 Agent 安装器的 `--force`、`--dry-run`、`--print` 互斥和无写入边界 per FR-006。
- [x] T031 [US2] 在 `docs/output-format.md` 增加终止型 transcript `error` payload 形状及禁止渲染规则，并保持 `LLM_INTEGRATION.md` 的权威链接一致 per FR-005。
- [x] T032 [US1] 在 `LLM_INTEGRATION.md`、通用 Agent 指令、Claude 和 Cursor 适配器中补齐版权边界引用，并统一 Windows 首选分发器与兼容包装器的表述 per FR-003/FR-004。
- [x] T033 [US3] 重新运行文档审计、Spec Kit status、编译、unittest、Git diff 和 PR head 检查；更新 `validation.md` 与 `convergence.md`，确认没有新的高/中/低缺口。

## 依赖与执行顺序

### 阶段依赖

- 阶段 1 无依赖，必须先完成 Spec Kit 初始化和 constitution。
- 阶段 2 依赖阶段 1，建立需求和追踪基础。
- 阶段 3 与阶段 4 可在阶段 2 后并行，二者分别修改文档和进行契约核对。
- 阶段 5 依赖阶段 3、阶段 4 的实际结果。
- 阶段 6 依赖所有迁移和验证任务完成。

### 并行机会

- T005-T007 可并行创建互不重叠的治理记录。
- T009-T014 可按文件集合并行处理，但每个文件只能由一个执行者负责。
- T016-T018 可并行做只读契约核对。
- T020-T024 可在文档迁移完成后并行准备验证材料；最终 convergence 必须汇总所有结果。

## 实施策略

1. 先完成 Spec Kit 基础设施和 constitution。
2. 迁移文档并删除重复/过时入口，同时保持代码和输出字面量稳定。
3. 运行测试和 Git 审计，修复文档冲突或价值遗漏。
4. 形成 validation/convergence，提交、推送并创建 PR。
