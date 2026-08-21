# 迁移验证快速开始

在仓库根目录执行：

```bash
specify integration status --json
python3 -m compileall -q listenkit_cli cli tools
python3 -m unittest discover -s tests -v
git diff --check
git status --short --branch
```

预期结果：

- Spec Kit 返回 `status: ok`，Codex managed files 的缺失数和修改数为 0。
- Python 编译检查成功。
- 全部可在当前平台执行的 unittest 通过；平台专属测试可以按测试说明跳过。
- Git diff 没有空白错误，工作区只包含本次迁移所需的文件。

文档审查时使用以下命令定位项目维护文档：

```bash
rg --files -g '*.md' -g '!**/.agents/**' -g '!**/.specify/**'
rg -n "generate-markdown|schema_version|report-json|auto-init|transcribe-audio" README.md LLM_INTEGRATION.md docs adapters
```

不要把命令输出中的 JSON 字段、CLI 选项或 Markdown 输出节名翻译成不可复制的形式；中文要求作用于说明文字。
