# 游戏策划多Agent协作工作流

> 本项目使用 AI 多角色协作完成游戏配表全流程（需求→设计→填表→QA）。
> 详细规则见 Skills 文件夹的 `SKILL.md`。

## 项目结构

```
G:\op_design\
├── CLAUDE.md               ← 本文件（项目入口）
├── excel\                   ← ★ 源数据（只读，程序端同步）
│   ├── *.xlsx                  配置表
│   ├── fight\, recruit\, ...   子目录配置表
│   └── (无其他内容)
└── references\              ← ★ 工程数据（AI工作区）
    ├── index.md                入口
    ├── naming_convention.md    ★ 命名规范（所有新建文件必须遵守）
    ├── domains\                按系统拆分的表关联
    ├── design\                 数值资料 + 速查表 + 模板
    ├── mapping\                全量重型数据（按需加载）
    ├── scripts\                脚本（分 core/combat/tools/tests/archive）
    │   └── archive\            一次性脚本归档
    ├── output\                 ★ 输出目录（不改源文件，每任务一个子目录）
    └── agents\                 ★ 智能体记忆持久层（6个角色各自私有）
```

## 核心规则速览

0. **不知道就不填，立即上报**（反幻觉铁律）
1. 先读映射再工作，绝不靠猜
2. 只插新行不改旧行；新增行绿底红字
3. ID 按同 Type 段位顺延
4. 未确认字段填 `"待补充"` + 红底
5. **双通道分离**：自然语言只传逻辑；数据通过 `utils.save_handoff()` 输出 JSON
6. **交接契约**：角色间交付必须用结构化格式，禁止自然语言传递数据值
7. **源数据与工程数据分离**：`excel/` 只放源表，`references/` 放所有AI工程产物
8. **必须用 Workflow**：配表流程通过 `Workflow` 框架执行，定义见 `scripts/configs/workflows/*.json`

## 工作流

### S_Standard（开荒模式）
S1-S9 状态机 + S_Patch 补丁流程。适用于**第一次做的新系统**。

### S_Express（量产模式）⚡
适用条件：`design_patterns.md` 有同类模板 且 变更<30行 且 不涉及新表。

跳过 L0，通过 `--start-at` 直接从 L1 开始：

```
coordinator_rules.md 判断领域 → hfsm_bootstrap.py --start-at L1.xxx → 状态机接管后续流程
```

规则：
- 跳过 L0（不需要拆模块，用户已明确改什么）
- L1→L2 仍由状态机控制，保留 Hook 校验
- 输出到 `output/{任务名}/`（不直写源表）
- 仍生成 CHANGES.md
- 因子名从 `factor_whitelist.json` 直取，未知因子查库后注册

## 数据读取

- 配置表：`excel/` 目录下所有 xlsx（header=1，第2行起为字段名）
- 参考资料：`references/design/`
- 输出位置：`references/output/{任务名}/`

### ⚠️ 大表读取规则（必须遵守）

> `references/scripts/utils.py` 内置自动索引机制，**所有角色必须通过 `read_table()` 或 `query_db()` 读表**，
> **禁止直接 `pd.read_excel()` / `openpyxl.load_workbook()` 读 fight/ 下的大表**。

| 方式 | 适用场景 | 示例 |
|------|----------|------|
| `query_db(sql)` | 精确查询已索引大表 | `query_db("SELECT * FROM [_Buff] WHERE [Buff因子] LIKE '%cri%'")` |
| `read_table(path)` | 读取整表为DataFrame | 自动索引>1MB文件，调用者无感 |
| `get_headers(path)` | 只读表头 | 快速获取列名 |
| `find_row_by_id(path, id)` | 按主键查单行 | 自动走SQLite |

已索引表：`_Buff` / `FightBuff` / `BuffActive` / `_BuffCondition`
索引文件：`references/scripts/core/table_index.db`

### 输出规范

| 工具 | 用途 |
|------|------|
| `write_output(task, table, headers, rows)` | Upsert导出xlsx |
| `save_handoff(task, role, data)` | 结构化交接JSON |
| `ChangeTracker(task, task_desc=, design_todos=)` | 变更追踪 + CHANGES.md(含任务拆解todo) |

### 配置模板

被动技能buff等完整配置模板见 `references/agents/combat_memory/design_patterns.md`

