# References 顶层索引

> 角色启动时只读此文件，按需加载下层。

## 命名规范

> 所有新建文件必须遵守 → [`naming_convention.md`](naming_convention.md)

## 配置表关联 (domains/)

| 领域 | 文件 | 规模 |
|---|---|---|
| Buff | `domains/buff.md` | ~115 引用 |
| 技能 | `domains/skill.md` | ~1200 引用 |
| Boss | `domains/boss.md` | ~45 引用 |
| 英雄 | `domains/hero.md` | ~18 引用 |
| 魂/霸气 | `domains/soul.md` | ~17 引用 |
| 场景 | `domains/scene.md` | ~7 引用 |
| 舰船 | `domains/ship.md` | ~5 引用 |
| 通用 | `domains/general.md` | ~35 引用 |

## 数值资料 (design/)

| 文件 | 说明 |
|---|---|
| `design/design_index.md` | 设计文档→Sheet→关键参数 |
| `design/factor_lookup.md` | Buff 因子速查表 |
| `design/timing_lookup.md` | 时机 ID 速查表 |
| `design/target_lookup.md` | 目标 ID 速查表 |
| `design/templates/` | 模块化方案模板（预留） |

## 映射 (mapping/) — 表间关系

> 表名/路径/字段查询直接用 `query_db()` + `get_headers()`，无需文件。

| 文件 | 大小 |
|---|---|
| `mapping/item_templates.md` | <1KB |
| `mapping/table_relations.md` | <1KB |
| `mapping/user_relations.md` | 增量积累 |

## 记忆持久层 (agents/)

| 文件 | 归属 | 说明 |
|---|---|---|
| `agents/error_solutions.md` | 主策划 R/W | 异常解法库 |
| `agents/user_preferences/preferences.md` | 全域 R / 主策 W | 用户偏好 |
| `agents/senior_memory/module_table_map.md` | 资深 R/W | 模块→表映射 |
| `agents/numerical_memory/design_decisions.md` | 数值 R/W | 消耗/曲线决策 |
| `agents/executor_memory/executor_solutions.md` | 执行 R/W | 盲区字段解法 |
| `agents/executor_memory/executor_rules.md` | 执行 R/W | QA打回铁规 |
| `agents/qa_memory/qa_rules.md` | QA R/W | 业务红线 |
