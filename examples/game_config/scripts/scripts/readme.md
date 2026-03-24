# 🏗️ Scripts

本地执行的 Python 脚本库，按功能分目录。

## 目录结构

| 目录 | 说明 | 文件 |
|------|------|------|
| `core/` | 公共工具（所有脚本的基础） | `constants.py`, `table_reader.py`, `table_validator.py`, `file_ops.py`, `utils.py`, `workflow.py` |
| `combat/` | 战斗业务校验 | `whitelist.py`, `combat_validator.py` |
| `cli/` | AI agent 命令行工具 | `query.py`, `check_factor.py` |
| `tools/` | 通用工具脚本 | `merge_to_excel.py`, `qa_runner.py` |
| `workflow/` | 角色间交接与变更追踪 | `handoff.py`, `change_tracker.py` |
| `tests/` | 测试脚本 | `test_workflow.py`, `test_row6_compliance.py`, `test_stale_refs.py` |
| `configs/` | JSON 配置文件 | `table_registry.json`, `workflows/`, `rules/` |
| `vendor/` | 第三方工具 | `sqlite3.exe` |
| `archive/` | 历史一次性脚本（仅归档，不维护） | 70+ 文件 |

## 使用方式

所有脚本通过 `sys.path.insert` 引用 `core/` 目录：

```python
import sys, os
sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'core'))
from utils import query_db, read_table
```

## 命名前缀

> 详见 [`naming_convention.md`](../naming_convention.md)

| 前缀 | 含义 | 位置 |
|------|------|------|
| `check_` | 检查/查询（只读） | `cli/` 或 `combat/` |
| `test_` | 测试脚本 | `tests/` |
| 无前缀 | 公共工具 | `core/` |
