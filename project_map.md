# 项目路径说明书 — HFSM Agent Framework

> 最后更新：2026-03-23

## 总览

```
<your_project>/
├── .agents/workflows/        ← AI workflow 定义（斜杠命令）
├── CLAUDE.md                 ← AI 全局规则
├── excel/                    ← 源数据 Excel 文件（1264 个）
└── references/               ← 项目主体
```

---

## .agents/workflows/ — AI 斜杠命令

| 文件 | 说明 |
|------|------|
| `design.md` | `/design` 命令：启动策划工作流，激活分层状态机 |
| `query-db.md` | `/query-db` 命令：查询 SQLite 索引数据库的标准方法 |

---

## references/ — 项目主体

```
references/
├── agents/           ← Agent 角色系统（知识库 + 工作流 + Hooks）
├── design/           ← 设计参考文档（Buff因子/目标/时机查找表）
├── domains/          ← 功能域知识（按游戏系统分类）
├── mapping/          ← 表间关系与映射规则
├── output/           ← 运行产出（暂存区输出）
├── scripts/          ← 所有 Python 脚本
├── staging/          ← 暂存输出的具体案例
├── index.md          ← 项目总索引
└── naming_convention.md ← 命名规范
```

---

## references/agents/ — Agent 角色系统

每个 Agent 统一三层目录结构：`knowledge/`（知识库）、`process/`（工作流+Hooks）、`data/`（运行时数据）

### coordinator_memory/ — 主策划 (L0)

| 文件/目录 | 说明 |
|-----------|------|
| `knowledge/coordinator_rules.md` | 主策划工作规则 |
| `knowledge/coordinator_examples.md` | 参考案例 |
| `process/coordinator_workflow.py` | L0 工作流定义（JSON 结构） |
| `process/coordinator_hooks.py` | L0 各步骤的 Hook 函数 |
| `data/review_report.md` | 评审报告输出 |
| `architecture_design.md` | 整体架构设计文档 |
| `todo_architecture.md` | 项目 TODO（唯一维护点） |
| `done.md` | 已完成事项归档 |

### combat_memory/ — 战斗策划 (L1)

| 文件/目录 | 说明 |
|-----------|------|
| `knowledge/combat_rules.md` | 战斗策划规则 |
| `knowledge/understand/` | 理解层知识（游戏机制分析） |
| `knowledge/translate/` | 翻译层知识（自然语言→配置字段） |
| `process/combat_workflow.py` | L1.combat 工作流定义 |
| `process/combat_hooks.py` | L1.combat Hook 函数 |
| `data/` | 运行时输入/输出数据 |

### numerical_memory/ — 数值策划 (L1)

| 文件/目录 | 说明 |
|-----------|------|
| `knowledge/numerical_rules.md` | 数值策划规则 |
| `knowledge/numerical_examples.md` | 数值填写案例 |
| `knowledge/requirement_structures.md` | 需求结构定义 |
| `knowledge/systems_index.md` | 游戏系统索引 |
| `knowledge/system_*.md` | 各子系统知识（角色/装备/经济/抽卡等） |
| `knowledge/table_directory.md` | 表目录（全量表结构参考） |
| `knowledge/locate/` | 定位步骤知识 |
| `knowledge/fill/` | 填写步骤知识 |
| `process/numerical_workflow.py` | L1.numerical 工作流定义 |
| `process/numerical_hooks.py` | L1.numerical Hook 函数 |

### executor_memory/ — 执行策划 (L2)

| 文件/目录 | 说明 |
|-----------|------|
| `knowledge/executor_rules.md` | 执行策划规则 |
| `knowledge/executor_design_patterns.md` | 执行层设计模式 |
| `knowledge/executor_sheet_index.md` | Sheet 页索引 |
| `knowledge/fill/` | 填写步骤知识 |
| `knowledge/write/` | 写入步骤知识 |
| `process/executor_workflow.py` | L2 工作流定义 |
| `process/executor_hooks.py` | L2 Hook 函数 |

### qa_memory/ — QA (L3)

| 文件/目录 | 说明 |
|-----------|------|
| `knowledge/qa_rules.md` | QA 规则 |
| `knowledge/qa_design_patterns.md` | QA 设计模式 |
| `knowledge/qa/` | QA 子知识 |
| `process/qa_workflow.py` | L3 工作流定义 |
| `process/qa_hooks.py` | L3 Hook 函数 |

### archive/ — 历史案例归档

| 文件 | 说明 |
|------|------|
| `postmortem_shadow_clone.md` | 如影随形（影子技能）复盘 |
| `postmortem_flaw.md` | 缺陷复盘 |
| `postmortem_ur_redhair.md` | UR红发案例复盘 |
| `report_ur_redhair.html` | UR红发可视化报告 |

---

## references/scripts/ — Python 脚本

### core/ — 核心引擎（9 个文件）

| 文件 | 说明 |
|------|------|
| `constants.py` | 全局常量、路径定义、Agent 路径解析器 |
| `machine.py` | 分层状态机 (HFSM) 引擎 |
| `hfsm_bootstrap.py` | 状态机初始化启动脚本 |
| `hfsm_registry.py` | 状态机注册表（所有 Agent 的工作流注册） |
| `workflow.py` | 工作流执行器（step 驱动、hook 调度） |
| `machine_hooks.py` | 状态机全局 Hook |
| `table_reader.py` | Excel/SQLite 表读取核心（含 `get_columns`、`query_db`） |
| `hook_utils.py` | Agent Hook 公共工具函数 |
| `file_ops.py` | 文件操作工具 |

### cli/ — 命令行工具（3 个文件）

| 文件 | 说明 |
|------|------|
| `query.py` | SQL 查询入口（`/query-db` 调用此脚本） |
| `check_factor.py` | 查询 Buff 因子 |
| `search_table.py` | 搜索表名/列名 |

### combat/ — 战斗相关验证（2 个文件）

| 文件 | 说明 |
|------|------|
| `combat_validator.py` | 战斗配置校验器 |
| `whitelist.py` | 白名单定义 |

### configs/ — 配置文件

| 文件/目录 | 说明 |
|-----------|------|
| `table_registry.json` | 表注册表（所有表的元信息：路径、Sheet、主键等） |
| `l3_transitions.json` | L3 状态转换配置 |
| `rules/factor_whitelist.json` | 因子白名单 |

### tools/ — 工具脚本（3 个文件）

| 文件 | 说明 |
|------|------|
| `gen_table_dir.py` | 生成表目录文档 |
| `qa_runner.py` | QA 自动运行器 |
| `rebuild_registry.py` | 重建 `table_registry.json` |

### workflow/ — 工作流辅助（2 个文件）

| 文件 | 说明 |
|------|------|
| `change_tracker.py` | 变更追踪器（记录修改了哪些表） |
| `handoff.py` | Agent 间交接（L1→L2 数据传递） |

### vendor/ — 第三方工具

| 文件 | 说明 |
|------|------|
| `sqlite3.exe` | SQLite 命令行工具（备用查询方式） |

### tests/ — 测试脚本（43 个文件）

| 分类 | 代表文件 | 说明 |
|------|----------|------|
| 端到端流程 | `test_full_pipeline.py`, `test_mvp_chain.py` | 完整流水线测试 |
| 状态机 | `test_hfsm.py`, `test_machine.py`, `test_transitions.py` | HFSM 引擎测试 |
| 工作流 | `test_workflow.py`, `test_routing.py` | 工作流执行/路由测试 |
| Agent 模拟 | `test_coordinator_sim.py`, `test_executor_sim.py`, `test_knowledge_sim.py` | 各 Agent 模拟测试 |
| Hook | `test_executor_hooks.py`, `test_new_hooks.py` | Hook 函数测试 |
| 数据完整性 | `test_align.py`, `test_row6_compliance.py`, `test_en_output.py` | 数据对齐/Row6/英文输出 |
| 执行器 | `test_executor_auto.py`, `run_executor_flow.py`, `run_executor_full.py` | 执行器自动化测试 |
| 查询脚本 | `query_*.py` | 特定表数据查询（调试用） |
| 工具 | `check_*.py`, `scan_row6.py`, `search_refs.py` | 检查/扫描工具 |
| 清理 | `clean_output.py`, `cleanup_test_data.py`, `quick_cleanup.py` | 测试数据清理 |
| 其他 | `test_clean_run.py`, `test_l3_real.py`, `test_review.py`, `test_stale_refs.py`, `test_locate_filter.py` | 各类回归测试 |

### output/ — 运行产出

空目录，运行时自动生成输出文件。

---

## references/design/ — 设计参考文档

| 文件/目录 | 说明 |
|-----------|------|
| `design_index.md` | 设计文档总索引 |
| `factor_lookup.md` | Buff 因子查找表 |
| `target_lookup.md` | Buff 目标查找表 |
| `timing_lookup.md` | 时机查找表 |
| `standalone_client_plan.md` | 独立客户端计划 |
| `data/怀旧服数值总表.xlsx` | 怀旧服数值参考 |
| `data/数值总表.xlsx` | 主数值总表 |
| `data/战斗表.xlsx` | 战斗配置参考 |
| `data/时机.xlsx` | 时机定义参考 |
| `templates/` | 模板文档 |

---

## references/domains/ — 功能域知识

按游戏系统分类的领域知识文档：

| 文件 | 说明 |
|------|------|
| `skill.md` | 技能系统知识（最大，24KB） |
| `buff.md` | Buff 系统知识 |
| `boss.md` | Boss 系统知识 |
| `hero.md` | 角色系统知识 |
| `general.md` | 通用知识 |
| `scene.md` | 场景系统 |
| `ship.md` | 舰船系统 |
| `soul.md` | 灵魂系统 |

---

## references/mapping/ — 表间映射

| 文件 | 说明 |
|------|------|
| `README.md` | 映射模块说明 |
| `table_relations.md` | 表间关系定义 |
| `user_relations.md` | 用户自定义关系 |
| `item_templates.md` | 道具模板 |

---

## references/staging/ — 暂存输出案例

| 目录 | 说明 |
|------|------|
| `soul_skill/` | 灵魂技能案例输出 |
| `_mvp_test/` | MVP 测试案例输出 |
