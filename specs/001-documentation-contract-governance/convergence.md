# 收敛记录：项目文档与契约治理基线

**日期**：2026-08-21

**分支**：`codex/spec-kit-migration`

## 收敛结论

本地实现已经满足 `spec.md`、`plan.md` 和 `tasks.md` 规定的迁移范围；迁移只改变项目文档、Spec Kit 治理工件和重复/过时文档结构，没有改变 ListenKit 应用源代码或公共运行时行为。

首次迁移审计发现 5 项公共契约记录遗漏：Windows 执行策略恢复路径、安装器安全参数、终止型 transcript 错误 payload、版权边界和 Windows 入口表述一致性。按照收敛原则，未改写前序记录，而是追加 T029-T033 并完成修正。

## 需求到证据映射

| 范围 | 实现/文档 | 验证 |
|---|---|---|
| FR-001/FR-002 | `.specify/`、`.agents/skills/`、`.specify/memory/constitution.md` | `specify integration status --json` 返回 `status: ok` |
| FR-003/FR-009 | `AGENTS.md`、`README.md`、`docs/`、`adapters/`；删除 `README.zh-CN.md` 和历史一键安装计划 | 文档逐文件审查、重复入口搜索、Git diff |
| FR-004/FR-005 | `LLM_INTEGRATION.md`、`docs/output-format.md`、`docs/backends.md`、适配器摘要 | 安装器 invariant 测试、现有 schema/report/backend 测试 |
| FR-006/FR-007 | `spec.md`、`plan.md`、`research.md`、`data-model.md`、`quickstart.md`、`tasks.md`、checklist、validation | 工件完整性检查、需求/任务/证据映射 |
| FR-008 | `listenkit_cli/`、`cli/`、`tools/`、`tests/` 未被迁移修改 | `git diff main --` 源码范围为空，153 项测试通过 |
| FR-010/SC-007 | `validation.md`、本记录、分支交付流程 | 编译、unittest、integration status、Git 审查；分支已推送，PR 目标为 `upstream/main` |

## 收敛补漏结果

| 任务 | 修正位置 | 结果 |
|---|---|---|
| T029 | `README.md`、`docs/install.md`、`LLM_INTEGRATION.md` | 补齐 `ExecutionPolicy Bypass` 恢复路径 |
| T030 | `LLM_INTEGRATION.md`、`adapters/agent/listenkit-agent-instructions.md` | 明确 `--force`、`--dry-run`、`--print` 的互斥和无写入边界 |
| T031 | `docs/output-format.md`、`LLM_INTEGRATION.md` | 记录终止型 `backend_error` payload，并禁止继续渲染 |
| T032 | `LLM_INTEGRATION.md`、通用 Agent 指令、Claude/Cursor 适配器、`docs/backends.md` | 补齐版权边界并统一首选 Windows 分发器与兼容包装器 |
| T033 | `validation.md`、本记录 | 重新完成文档审计、Spec Kit status、编译、153 项测试、Git 检查和 PR 状态核对 |

## 任务收敛

- T001-T027 已完成并在 `tasks.md` 标记为 `[x]`。
- T028 已完成分支提交、推送和 PR 创建；PR 为 `feiyanqiqiao/ListenKit#8`。
- T029-T033 已完成；补漏后的文档审计没有剩余 CRITICAL、HIGH、MEDIUM 或 LOW 缺口。
- PR #8 仍为 OPEN，最新收敛提交将继续推送到该 PR，不创建重复 PR。

## 已知限制

- 当前验证运行在 macOS/Python 3.14.4；Windows-only 测试跳过，由 CI 的三平台矩阵负责。
- Apple Speech 权限、Apple Silicon Metal 和真实 NVIDIA 设备声明没有新增本地以外的支持承诺，仍需对应实机或 CI 证据。
- Spec Kit 生成技能中的英文文本属于 manifest 管理的工具基础设施，未手工改写；项目维护规则和说明均已中文化。
