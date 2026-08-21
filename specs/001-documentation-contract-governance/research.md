# 迁移研究记录

## 研究问题

### Spec Kit 项目状态

仓库原本没有 `.specify/`，因此不是已初始化的 Spec Kit 项目。当前 CLI 为 `specify 0.16.6.dev0`，Codex CLI 可用。使用 `specify init --here --force --non-interactive --integration codex` 在仓库根目录初始化，生成的 integration status 必须作为运行时事实来源。

### 权威事实分层

- `AGENTS.md`：项目级 Agent 操作约束、入口和交付前验证。
- `LLM_INTEGRATION.md`：外部 Agent 安装、公共入口、产物和不得绕过入口的完整契约。
- `docs/output-format.md`：Markdown、transcript JSON v1 和 execution report 字段/版本规则。
- `docs/backends.md`：ASR 后端、运行时、GPU/CPU fallback 和平台实现策略。
- `docs/install.md`：用户安装、初始化、诊断和平台运行时准备。
- `.github/workflows/test.yml` 与 `tests/`：可执行验证入口和平台覆盖证据。

Spec Kit 工件只记录本次治理迁移的需求、决策、任务和追踪，不复制以上文档全文。

### 去重决策

1. `README.md` 作为唯一默认入口；`README.zh-CN.md` 的有效中文内容并入后删除。
2. `docs/one-click-agent-install-plan.md` 已描述一项已实现的文档/安装重构，不再作为当前计划；迁移其有效决策后删除。
3. `LLM_INTEGRATION.md` 保持 Agent 契约权威；`adapters/agent/listenkit-agent-instructions.md` 只保留可安装摘要，`adapters/*` 只保留对应 Agent 的薄说明。
4. `docs/install.md` 负责用户操作，`docs/backends.md` 负责实现策略；两者可以引用同一事实，但不重复完整段落。
5. `docs/output-format.md` 保留 schema 字段唯一解释；其它文档只描述集成者必须知道的产物摘要。

### 语言决策

项目维护文档的叙述、标题和说明改为中文；命令、代码、路径、JSON 字段、Markdown 输出节名和目标语言样本文本保持原文，以避免破坏可复制性和既有契约。Spec Kit 生成技能文件由 manifest 管理，不能为了语言规则手工改写。

### 验证决策

迁移验证必须同时覆盖：Spec Kit 管理文件完整性、文档内容审计、Python 编译、完整 unittest、Git diff 与删除文件价值转移。Windows、Apple Silicon、Apple Speech 和硬件加速声明仍以对应平台实机或 CI 证据为准，不因本地 macOS 检查而扩大支持承诺。
