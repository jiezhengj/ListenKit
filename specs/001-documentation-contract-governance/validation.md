# 迁移验证记录

**日期**：2026-08-21

**分支**：`codex/spec-kit-migration`

## 结果摘要

| 检查 | 命令或范围 | 结果 |
|---|---|---|
| Spec Kit integration | `specify integration status --json` | 通过；`status: ok`，Codex managed files 缺失 0、修改 0、非法路径 0 |
| Python 编译 | `python3 -m compileall -q listenkit_cli cli tools` | 通过 |
| 单元测试 | `python3 -m unittest discover -s tests -v` | 通过；153 项，141 项通过，12 项因 Windows/托管运行时条件跳过 |
| Git 空白检查 | `git diff --check` | 通过 |
| 文档语言 | 项目维护 Markdown 逐文件审查 | 通过；说明文字为中文，命令/字段/路径/输出节名保留原文 |
| 重复入口 | 检查 `README.zh-CN.md`、历史一键安装计划和权威契约引用 | 通过；重复镜像与过时计划已删除，内容已迁移 |
| 应用行为 | `git diff main --` 与源代码范围审查 | 通过；没有应用源代码变更 |
| 分支推送 | `git push -u origin codex/spec-kit-migration` | 通过；origin 已建立同名远程分支 |
| 收敛补漏 | Windows 执行策略、安装器安全参数、终止型 error payload、版权边界和 Windows 入口审计 | 通过；T029-T033 已完成 |
| PR 状态 | `gh pr view 8 --repo feiyanqiqiao/ListenKit` | 通过；PR #8 为 OPEN，目标为 `main`，后续提交继续推送到同一 PR |

## 需求覆盖

| 需求 | 主要工件/文件 | 验证证据 |
|---|---|---|
| FR-001 | `.specify/`、`.specify/integration.json`、Codex manifest | integration status |
| FR-002 | `.specify/memory/constitution.md` | 宪章占位符检查、PR 审查 |
| FR-003 | `AGENTS.md`、`README.md`、`LLM_INTEGRATION.md`、`docs/`、`adapters/` | 文档逐文件审查 |
| FR-004 | `LLM_INTEGRATION.md`、`adapters/agent/` | 既有安装器 invariant 测试、文档审查 |
| FR-005 | `docs/output-format.md`、`listenkit_cli/`、`tests/` | transcript/report/schema 测试 |
| FR-006/FR-009 | `spec.md`、`plan.md`、`tasks.md`；删除历史计划 | Git diff、内容转移核对 |
| FR-007 | 本 feature 全部 Spec Kit 工件 | 工件存在性和追踪表 |
| FR-008 | 代码、CLI、运行时和 CI 未改动 | Git diff、153 项测试 |
| FR-010 | `quickstart.md`、本记录和 Git 检查 | 命令结果与工作区审查 |

## 平台限制

- 本次验证在 macOS/Python 3.14.4 完成；Windows-only 测试按测试标记跳过。
- CI 仍负责 macOS、Ubuntu、Windows 矩阵、Windows PowerShell 5.1/7 入口和 Windows 真实 faster-whisper runtime job。
- Apple Speech 权限、Apple Silicon Metal 选择和真实 NVIDIA 设备声明未因本次文档迁移新增实机承诺；仍以对应设备验证为准。
- 收敛复核确认没有剩余 CRITICAL、HIGH、MEDIUM 或 LOW 文档契约缺口；未新增应用源代码变更。
