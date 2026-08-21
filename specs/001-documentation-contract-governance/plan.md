# 项目文档与契约治理基线实施计划

**分支**：`codex/spec-kit-migration` | **日期**：2026-08-21 | **规格**：[spec.md](./spec.md)

**输入**：基于现有 ListenKit 工程、公共集成契约、输出格式说明、后端说明、CI 和测试建立 Spec Kit 治理基线。

## 摘要

本迁移为现有 ListenKit 项目补齐标准 Spec Kit 基础设施和一组可审查的治理工件，不改变运行时实现。迁移内容分为四层：

1. 用现有仓库事实建立中文 constitution 和治理规则。
2. 将当前公共入口、输出 schema、运行时隔离、跨平台行为和 Agent 边界整理为一份基线 feature。
3. 将项目维护文档统一为中文，按职责去除重复和过时入口；保留命令、字段、路径和协议字面量。
4. 用 tasks、validation 和 convergence 将需求映射到实际文件、测试和 CI，并在 Git/PR 层复核无价值损失。

## 技术背景

**语言/版本**：项目 CLI 主机 Python 3.10+；托管 ASR 运行时 Python 3.14；迁移不改变代码语言。

**主要依赖**：当前 Spec Kit CLI `0.16.6.dev0`、Codex integration、现有 Python 核心、Shell/PowerShell 分发器和 GitHub Actions。

**存储**：Markdown、JSON、Spec Kit 工件和 Git；本次不增加数据库或运行时存储。

**测试**：`python3 -m compileall -q listenkit_cli cli tools`；`python3 -m unittest discover -s tests -v`；`specify integration status --json`；Git diff 与内容审计。

**目标平台**：macOS、Linux、WSL 和原生 Windows；本次迁移不扩展平台范围。

**项目类型**：本地优先、跨平台 Python CLI 与 Agent 集成适配器。

**性能目标**：不改变转写性能或运行时策略；文档迁移只要求不引入额外运行时步骤。

**约束**：不得改变 transcript schema、原子输出、UTF-8、非交互、Python 3.14 隔离、平台分发器和公共入口行为；不得手工修改 Spec Kit manifest 管理的技能文件。

**范围**：根目录文档、`adapters/` 项目维护文档、`docs/`、Spec Kit 基础设施和一个基线 feature；应用源代码与现有测试逻辑仅用于核对，不作无关重构。

## 宪章检查

*门禁：Phase 0 研究前以及 Phase 1 设计后均需通过。*

- [x] 公共入口与边界唯一：迁移只整理文档和工件，保留 `generate-markdown` 作为正常入口。
- [x] 契约与模式优先：保留 `LLM_INTEGRATION.md`、`docs/output-format.md` 的现行 schema 与执行报告事实，不重复复制全文。
- [x] 本地优先与运行时隔离：不修改运行时目录、模型策略或初始化行为。
- [x] 跨平台与非交互：保留 CI 的三平台矩阵与 Windows 真实 runtime job；不改变入口脚本。
- [x] 测试与证据优先：任务包含编译、unittest、integration status、Git 审计和验证报告。
- [x] 适配器瘦身与中文文档：项目维护文档翻译为中文，Spec Kit 生成技能由 manifest 管理且不手工改写。

## 研究与设计产物

Phase 0 与 Phase 1 的产物如下：

- [research.md](./research.md)：现有文档职责、Spec Kit 运行时、权威事实和去重决策。
- [data-model.md](./data-model.md)：契约、工件、验证证据和追踪关系的逻辑模型。
- [quickstart.md](./quickstart.md)：维护者验证迁移结果的最短流程。
- [contracts/](./contracts/)：本次不新增机器接口；目录保留为空，不创建重复契约副本。

## 项目结构与迁移范围

### Spec Kit 工件

```text
.specify/
├── memory/constitution.md
├── integrations/
├── scripts/
├── templates/
└── workflows/
.agents/skills/                 # Spec Kit 生成且由 manifest 管理
specs/001-documentation-contract-governance/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
├── validation.md
├── convergence.md
└── checklists/requirements.md
```

### 项目维护文档

```text
AGENTS.md                       # 项目规则与入口
README.md                       # 中文默认入口
LLM_INTEGRATION.md              # Agent 集成事实来源
PRIVACY_AND_COPYRIGHT.md        # 隐私与版权边界
EXAMPLES.md                     # 维护者 fixture 示例
adapters/                       # 各 Agent 的薄适配器说明
docs/install.md                 # 用户安装与运行时准备
docs/backends.md                # 后端实现与选择策略
docs/output-format.md           # 输出 schema 与字段
docs/debugging.md               # 维护与调试接口
docs/audio-hijack.md            # 可选音频输入流程
```

### 删除或合并范围

- 删除 `README.zh-CN.md`，将其有效内容并入中文 `README.md`，避免默认入口和中文镜像重复。
- 删除 `docs/one-click-agent-install-plan.md`，将其中仍有效的用户流程、测试意图、安装边界和文档分层纳入本 feature 与现行文档；不保留备份副本。
- 保留英文/日文 sample transcript 的目标语言正文；将样例说明、维护者说明和模板外层文档改为中文，避免破坏它们作为语言样例的数据价值。

## 复杂度记录

本次没有违反宪章的复杂度增加。Spec Kit 生成的 `.agents/skills` 和 `.specify` 基础设施是用户明确要求的标准集成，不属于应用层重复结构；项目 feature 工件只记录治理迁移，不复制完整公共契约。
