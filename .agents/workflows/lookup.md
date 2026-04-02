---
description: "查配表资料：查因子、查表、查字段、查ID，统一入口"
allowed-tools: ["Bash"]
arguments: ["keyword"]
argument-hint: "要查的内容，如：连击因子 / FightBuff表字段 / buffId 1001"
whenToUse: "用户要查因子名、查表结构、查字段、查ID、查配表数据"
---

# 查配表资料

用户要查的内容：${keyword}

## 铁规

1. **只能调用以下 3 个脚本**，禁止使用 `python -c`，禁止新建脚本，禁止直接调用 sqlite3
2. **必须执行脚本获取真实结果**，禁止猜测或编造任何查询结果
3. **PowerShell 编码问题**：SQL 中的 `%`（LIKE 通配符）和中文字符必须通过脚本参数传入，不要在 PowerShell 中直接拼接

## 工具清单

你有且只有以下 3 个工具，根据用户输入选择一个执行：

### 工具 1：查因子 — `check_factor.py`

当用户输入像因子名（如 speed、cri、连击、暴击、减速）时执行：

// turbo
```shell
python scripts/cli/check_factor.py <因子名>
```

### 工具 2：搜表名/字段名 — `search_table.py`

当用户输入像表名或字段名（如 FightBuff、buffId、技能表、Skill）时执行：

// turbo
```shell
python scripts/cli/search_table.py <关键词>
```

### 工具 3：SQL 精确查询 — `query.py`

当用户输入包含 SELECT 或明确要求精确查询时执行：

// turbo
```shell
python scripts/cli/query.py "<SQL语句>"
```

## 选择规则

1. 输入像因子名 → 执行工具 1
2. 输入像表名或字段名 → 执行工具 2
3. 输入包含 SELECT 或要求精确数据 → 执行工具 3
4. 不确定 → 先执行工具 2 搜索，根据结果决定是否需要工具 3 补充

## 输出要求

- 用表格展示查询结果
- 如果没找到，告诉用户并建议换个关键词
- 如果工具 2 的结果需要进一步查询，主动用工具 3 补充
