# Mapping 目录

> 表间关系与映射信息。表名/路径/字段/关联查询请直接用 `query_db()` 和 `get_headers()`。

## 文件清单

| 文件 | 大小 | 用途 |
|---|---|---|
| `item_templates.md` | <1KB | 道具模板 |
| `table_relations.md` | <1KB | 表关系概览 |
| `user_relations.md` | <1KB | 用户自定义关联 |

## 查表方式

```python
from table_reader import query_db, get_headers

# 查某张表的列名
get_headers("fight/FightBuff.xlsx")

# 查某张表的数据
query_db("SELECT * FROM [FightBuff] WHERE fightBuffId=123")

# 查哪些表有某个字段（替代已删除的 static_relations.md）
query_db("SELECT name FROM sqlite_master WHERE type='table'")
# 然后逐表 PRAGMA table_info([表名]) 检查
```

> ⚠️ 已废弃：`schema_index.md`、`table_registry.md`、`static_relations.md` 已删除。
> 其功能已被 `query_db()` + `get_headers()` + `PRAGMA table_info` 完全替代。
