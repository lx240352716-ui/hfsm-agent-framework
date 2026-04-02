# 命名规范

> 创建: 2026-03-13
> 所有新建文件必须遵守此规范。

## 总则

- **语言**: 全部英文（output 任务目录除外）
- **风格**: `snake_case`（小写 + 下划线）
- **禁止**: 大写字母开头、空格、特殊符号、拼音缩写

## Python 脚本

格式: `{前缀}_{描述}.py`

| 前缀 | 含义 | 位置 |
|------|------|------|
| `exec_` | 执行脚本（写入数据） | `combat/` |
| `check_` | 检查/查询（只读） | `combat/` 或 `tools/` |
| `query_` | 数据查询 | `combat/` 或 `tools/` |
| `test_` | 测试脚本 | `tests/` |
| `pipeline_` | 状态机/流水线 | `core/` 或模块目录 |
| 无前缀 | 公共工具 | `core/` |

## JSON 配置

格式: `{用途}_{范围}.json`（如 `factor_whitelist.json`）

## Markdown 文档

| 类型 | 格式 | 示例 |
|------|------|------|
| 角色记忆 | 固定名 | `understanding.md`, `execution.md` |
| 速查表 | `{内容}_lookup.md` | `factor_lookup.md` |
| 复盘 | `postmortem_{英文名}.md` | `postmortem_shadow_clone.md` |
| TODO | `todo_{主题}.md` | `todo_architecture.md` |
| 日报 | `daily_{YYYYMMDD}.md` | `daily_20260311.md` |
| 报告 | `report_{英文名}.md` | `report_shadow_clone.md` |

## Output 文件

**任务目录用中文**: `{模块}_{中文任务名}/`（如 `buff_如影随形/`）

目录内自动生成文件保持原有命名。

## 数据文件

保持程序端原始文件名，不改。

## 文件夹

全英文 `snake_case`，Output 任务目录除外。
