# 治理追踪模型

## 实体

### 文档事实

表示一个对用户、Agent 或维护者有意义的稳定事实，例如公共入口、transcript schema v1、运行时路径或平台 fallback。

属性：事实 ID、中文说明、权威文档、允许引用的位置、当前状态。

### Spec Kit 工件

表示 constitution、spec、plan、research、data-model、quickstart、tasks、checklist、validation 或 convergence 中的一份治理记录。

属性：工件路径、所属 feature、内容职责、上游事实、下游引用。

### 任务

表示可以独立执行和审查的迁移动作。

属性：任务 ID、需求引用、文件范围、依赖、验证命令、完成状态。

### 验证证据

表示命令、测试、CI job 或真实设备检查的结果。

属性：证据 ID、命令或 job、覆盖范围、结果、环境、限制和时间。

## 关系

```text
文档事实
  ├── 由权威项目文档定义
  ├── 被 spec/plan/tasks 引用
  └── 由验证证据确认

Spec Kit 工件
  ├── spec 定义需求
  ├── plan 定义迁移边界
  ├── tasks 定义执行动作
  ├── checklist 审查需求质量
  ├── validation 记录执行结果
  └── convergence 确认需求、任务、实现和证据一致
```

## 不变量

- 一条公共契约事实只能有一个权威项目文档。
- 每个核心需求至少关联一个任务和一个验证证据。
- Spec Kit 生成文件的内容以 manifest 为准，不被项目迁移任务改写。
- 删除文档前，所有仍有效的事实必须已被权威文档或当前工件承接。
