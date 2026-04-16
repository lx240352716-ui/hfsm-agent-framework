# 游戏策划多Agent协作工作流

> 本项目使用 AI 多角色协作完成游戏配表全流程（需求→设计→填表→QA）。
> 详细规则见 Skills 文件夹的 `SKILL.md`。

## 项目结构

```
./
├── CLAUDE.md               ← 本文件（项目入口）
├── knowledge/              ← ★ 知识库（不入 git）
│   ├── gamedata/               配置表 Excel（1000+ 张）
│   ├── gamedocs/               策划参考文档
│   └── *.md                    提练知识（速查表、系统描述、表关系）
├── output/                 ← ★ 输出目录
│   └── staging/                待确认产物
├── references/             ← ★ AI 引擎
│   ├── agents/                 智能体记忆持久层（5个角色）
│   └── scripts/                脚本（core/cli/server/configs/tests）
├── docs/                   ← 项目文档（架构、规范）
├── .dev/                   ← 开发管理（不入 git）
└── .env                    ← 环境变量
```

## 核心规则速览

0. **不知道就不填，立即上报**（反幻觉铁律）
1. 先读映射再工作，绝不靠猜
2. 只插新行不改旧行；新增行绿底红字
3. ID 按同 Type 段位顺延；**设计阶段用占位符 `<<NEW_X>>`，真实 ID 仅在 executor write 阶段分配**
4. 未确认字段填 `"待补充"` + 红底
5. **双通道分离**：自然语言只传逻辑；数据通过 `utils.save_handoff()` 输出 JSON
6. **交接契约**：角色间交付必须用结构化格式，禁止自然语言传递数据值
7. **源数据与工程数据分离**：`knowledge/` 放源表和知识，`references/` 放 AI 引擎
8. **必须用 HFSM**：配表流程通过分层状态机执行，定义见 `agents/*/process/*_workflow.py`

## 知识存储规则

1. **案例走暂存**：所有案例一律走 `pending_examples.json`，禁止直写 `*_examples.md`
2. **暂存生命周期**：match 阶段覆盖写（清残留）→ confirm/output 追加 → review/结束阶段提交
3. **分类存储**：踩坑/铁规 → 对应 Agent 的 `*_rules.md`；案例 → 对应 Agent 的 `*_examples.md`
4. **格式跟随目标文件**：写入前先读目标文件，按其现有格式追加
5. **写入方式**：`append_pending()` → `commit_pending()`（见 `hook_utils.py`）

## 复盘规则

每轮对话结束前（/design review、/consult 确认、/quick 完成），AI 自查：

1. 收集本轮所有问题（错误、用户纠正、用户确认项）
2. 去重：该问题是否曾出现过？
   - 首犯 → 写入对应 Agent 的踩坑记录
   - 重犯 → 升级为对应 Agent 的铁规
3. 写入方式：`append_pending()` → `commit_pending()`
4. 发布复盘报告

## 工作流

### S_Standard（开荒模式）

S1-S9 状态机 + S_Patch 补丁流程。适用于**第一次做的新系统**。

### S_Express（量产模式）⚡

适用条件：`design_patterns.md` 有同类模板 且 变更<30行 且 不涉及新表。

跳过 L0，通过 `--start-at` 直接从 L1 开始：

```
coordinator_rules.md 判断领域 → workflow_runner.py --skill excel --start-at L1.xxx → 状态机接管后续流程
```

规则：

- 跳过 L0（不需要拆模块，用户已明确改什么）
- L1→L2 仍由状态机控制，保留 Hook 校验
- 输出到 `output/{任务名}/`（不直写源表）
- 仍生成 CHANGES.md
- 因子名从 `factor_whitelist.json` 直取，未知因子查库后注册

## 数据读取

- 配置表：`knowledge/gamedata/` 目录下所有 xlsx（header=1，第2行起为字段名）
- 参考资料：`knowledge/`
- 输出位置：`output/{任务名}/`

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
