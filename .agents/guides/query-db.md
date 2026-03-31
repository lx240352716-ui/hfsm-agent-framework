---
description: how to query SQLite database (table_index.db)
---

# 查询 SQLite 数据库

## 规则

> **禁止使用 `python -c` 执行任何 SQL 查询。**
> PowerShell 会破坏 `%`（LIKE 通配符）和中文字符编码。

## 方法 1：cli/query.py（标准入口）

// turbo
```powershell
python scripts/cli/query.py "SQL语句"
```

示例：
```powershell
python scripts/cli/query.py "SELECT DISTINCT [buffId] FROM [_Buff] LIMIT 5"
```

## 方法 2：sqlite3.exe（备用）

// turbo
```powershell
scripts/vendor/sqlite3.exe -json scripts/core/table_index.db "SQL语句"
```

## 方法 3：Python 代码内部（生产代码用）

```python
from table_reader import query_db
results = query_db("SELECT * FROM [表名] WHERE [字段名]='值'")
```

## 其他 CLI 工具

```powershell
python scripts/cli/check_factor.py <因子名>              # 查因子
python scripts/cli/manage_pending.py --list              # 查 pending
python scripts/cli/manage_pending.py --discard           # 丢弃 pending
```
