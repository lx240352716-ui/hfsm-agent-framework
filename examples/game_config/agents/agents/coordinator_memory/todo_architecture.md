# 项目 TODO（唯一权威文件）

> **规则**：所有待办只在本文件维护。已完成项移入 `done.md`。
> **策略**：先建后拆——按新架构构建新文件，测试通过后再删除旧文件。
> 最后更新: 2026-03-23 (P12.0 pending 暂存区完成)
> 设计文档: `architecture_design.md`

---

## P0 — 架构设计定稿

> 依赖：无。后续所有工作都依赖 P0 的结论。

### P0.1 确认架构方案 ✅
- [x] 确认 Agent 精简方案：仅保留主策划(L0)、战斗策划(L1)、数值策划(L1)、执行策划(L2)
- [x] 确认 L3 自动化层范围：qa_runner + table_validator + merge_to_excel + change_tracker
- [x] 确认每个 Agent 的 MD 文件归属（见 `architecture_design.md` 第四章）
- [x] 确认每个 Agent 是否需要 Workflow JSON（主策划 → 无；战斗/执行 → 有；数值 → 新建）

### P0.2 定义打回/回退协议 ✅
- [x] 定义回退数据结构：`{ error_log, original_handoff, failed_step, retry_hint }`
- [x] 定义 L3→L2 回退：QA 报错 → 执行策划重填（带报错 Log + 原始 staging）
- [x] 定义 L2→L1 回退：执行发现设计缺字段 → 战斗/数值补设计（带 handoff + 缺失清单）
- [x] 定义 AI 上下文保持：回退 JSON 作为系统提示注入被退回 Agent 的 prompt

### P0.3 决定 standard.json 去留 ✅
- [x] 盘点 standard.json 中哪些步骤已被状态机 + Agent 独立 Workflow 覆盖
- [x] 决定：**暂时保留**，MVP 后再处理

---

## P1 — 构建新架构文件（不删旧文件）

> 依赖：P0 定稿。**只增不删，新旧共存。**

### 1.1 主策划新 MD（3 个新建）✅
- [x] 新建 `coordinator_memory/knowledge.md` — 从 understanding.md 提取通用知识
- [x] 新建 `coordinator_memory/examples.md` — 整理已有案例
- [x] 新建 `coordinator_memory/lessons.md` — 从 postmortem 提取教训

### 1.2 路由配置 ✅
- [x] 新建 `scripts/configs/routing.json` — 需求类型→角色→子工作流映射
- [x] 新建 `test_routing.py` — 校验 routing.json 合法性（5/5 通过）

### 1.3 数值策划 Workflow ✅
- [x] 新建 `scripts/configs/workflows/numerical.json` — 轻量工作流
- [x] 强制输出为标准 handoff JSON 格式

### 1.4 修复关键 MD 内容（改不删）✅
- [x] `translation.md` — 速查表引用改为 condition_map/factor_whitelist，12 个中文字段名改 Row6 英文
- [x] `qa_rules.md` — Factor速查.md → factor_whitelist.json
- [x] `error_solutions.md` — 已删除（不再需要）

### 1.5 文件复制（从 senior 到新归属，保留原文件）✅
- [x] 复制 `module_table_map.md` → coordinator_memory/
- [x] 复制 `numerical_sheet_index.md` → executor_memory/
- [x] 提取 `s6_equip_check.md` 内容 → 追加到 executor_rules.md

---

## P2 — MVP 验证（先跑通再抽象）✅

> 依赖：P1 新文件就绪。

- [x] 选一个真实需求（"纯数值调整" buff参数微调）
- [x] 手动模拟 L0→L1→L2→L3 全链路（test_mvp_chain.py 16/16 通过）
- [x] 记录每个环节的输入/输出实际格式
- [x] 验证 handoff 数据无损传递
- [x] 验证打回时报错信息足够 AI 定位问题
- [x] 根据结果决定是否需要写状态机引擎

### ❗ MVP 发现的 bug
- [x] `qa_runner.py` 外键校验用 Row6 英文名查 SQLite → 改用 `get_sqlite_col()` 转换（已修复）
- [x] L2 align 丢弃了 `buff参数1`/`buff参数2`/`buff参数3` — P9.4 重构后改为 `_ref_id` 直查，不再做列名对齐，根因已消除

---

## P3 — 状态机引擎 ✅

> 依赖：P2 结论。已使用 pytransitions 库实现。

- [x] HFSM 引擎（pytransitions HierarchicalMachine）
- [x] 分层结构注册（coordinator → design → executor → pipeline）
- [x] 事件定义（dispatch, design_approved, escalate, qa_failed 等 8 个）
- [x] Guard 条件（7 条层间转移全部带条件方法）
- [x] Skill 入口（/design workflow）
- [x] 启动/恢复脚本（hfsm_bootstrap.py）
- [x] 端到端测试通过（full flow + rollback + escalate）

文件清单：
- `scripts/core/hfsm_registry.py` — 分层注册 + Guard 条件
- `scripts/core/hfsm_bootstrap.py` — 启动/恢复脚本
- `.agents/workflows/design.md` — Skill 入口
- `scripts/tests/test_hfsm.py` — 端到端测试

---

## P4 — 清理旧文件 ✅

> 依赖：P2 + P3 全部完成，新架构已验证。

### 4.1 删除冗余 MD（10 个）✅
- [x] coordinator: `execution.md`、`summary.md`、`numerical_design_knowledge.md`
- [x] combat: `execution.md`
- [x] executor: `execution.md`、`understanding.md`、`summary.md`
- [x] numerical: `summary.md`
- [x] qa: `summary.md`
- [x] senior: `summary.md`

### 4.2 删除旧目录 ✅
- [x] 删 `senior_memory/`（有价值文件已在 P1 复制走）
- [x] 删 `user_preferences/`
- [x] 合并 `执行策划/` → `executor_memory/`（execution_hooks.py + id_ranges.json + table_defaults.json）

### 4.3 归档 ✅
- [x] `postmortem_*.md` ×3 → `archive/`

---

## P5 — 落地三层架构（知识层 / 流程层 / 数据层）

> 依赖：P2 MVP 验证通过。目标：把 `architecture_design.md` 三-B 章定义的标准结构落实到每个 Agent 目录。
> 设计参考：`architecture_design.md` 第三-B章 + 第四章

### 5.1 创建 transitions.json（关联关系 + 切换条件）✅
- [x] `coordinator_memory/transitions.json` — 可派发 combat/numerical，可接收升级
- [x] `combat_memory/combat_transitions.json` — 正向→executor，升级→coordinator，接收打回
- [x] `numerical_memory/numerical_transitions.json` — 正向→executor，升级→coordinator，接收打回
- [x] `executor_memory/executor_transitions.json` — 正向→L3，打回→combat/numerical
- [x] `scripts/configs/l3_transitions.json` — 通过→完成，不通过→打回 L2

### 5.2 创建数据层文件（input/output JSON）✅
- [x] 定义各 Agent 的 `input.json` / `output.json` schema（字段清单）
- [x] coordinator: `input.json`（用户需求解析）+ `output.json`（路由结果）
- [x] combat: `input.json`（接收路由）+ `output.json`（设计方案 handoff）
- [x] numerical: `input.json`（接收路由）+ `output.json`（数值方案 handoff）
- [x] executor: `input.json`（接收 handoff）+ `output.json`（staging 数据）

### 5.3 补全缺失的流程层脚本 ✅
- [x] `numerical_memory/numerical_hooks.py` — 数值校验钩子

### 5.4 验证
- [x] 编写 `test_transitions.py` — 校验所有 transitions.json 格式合法、目标 Agent 存在（5/5 通过）
- [x] 用一个真实需求走通 input.json → output.json 数据流 — P9-P11 清明节礼包端到端已验证

---

## P6 — 分布式 Workflow 注册 + 接入引擎

> 依赖：P3 状态机引擎完成。目标：每个 Agent 声明自己的 workflow，引擎自动组装并驱动执行。

### 6.1 创建 Agent Workflow 定义文件 ✅
- [x] `coordinator_memory/process/coordinator_workflow.py` — 主策划 workflow
- [x] `combat_memory/process/combat_workflow.py` — 战斗策划 workflow
- [x] `numerical_memory/process/numerical_workflow.py` — 数值策划 workflow
- [x] `executor_memory/process/executor_workflow.py` — 执行策划 workflow

### 6.2 整理 Agent 目录结构
- [x] combat_memory → 迁移平铺文件到 knowledge/process/data/ 子目录 — P10.1 完成
- [x] numerical_memory → 同上 — P10.1 完成
- [x] executor_memory → 同上 — P10.1 完成

### 6.3 改造 hfsm_registry.py ✅
- [x] 从各 Agent workflow.py 读取定义，自动组装 HFSM（替代硬编码）
- [x] 层级命名：coordinator / design / executor / pipeline
- [x] on_enter/on_exit 回调自动绑定

### 6.4 主策划 Workflow 全流程 ✅
- [x] `coordinator_hooks.py` — 4 个无参函数（从文件读数据）
- [x] 知识重构：rules.md（规则+铁规+踩坑） + examples.md（自动积累）= 2 文件
- [x] 删除旧文件：coordinator_knowledge.md、coordinator_module_table_map.md、coordinator_lessons.md
- [x] 输出格式确定：JSON `{dispatch: {role: {requirement, modules}}}`

### 6.5 Machine Hooks + 层间路由 ✅
- [x] `scripts/core/machine_hooks.py` — 层间 on_enter 回调（design / executor / pipeline）
- [x] design 层增加 `router` 初始状态
- [x] 数据驱动队列路由：`_auto_route_design()` + `_route_next()`
- [x] `agent_done` 事件统一各 Agent 完成通知
- [x] `queued=True` 支持 on_enter 内触发事件
- [x] 4 场景测试通过：combat+numerical / numerical-only / combat-only / guard

### 6.6 数值策划 workflow 完善（模拟验证后的发现）

> 6 状态框架 + hooks 已写完。以下是模拟清明节礼包流程后发现需要补的细节。

#### hooks 要改的

- [x] **on_enter_locate 加 search_table 集成** — P10.2 on_exit_locate 已集成参考行搜索
- [x] **on_enter_locate 加参考数据查询** — P10.2 ref_candidates 已实现
- [x] **on_enter_fill hook（新增）** — P10.1 已新增，加载 fill/rules.md + fill/examples.md
- [x] **on_enter_output 加 max_id 自动分配** — P6.8 executor write 阶段已处理 ID 分配
- [x] **on_exit_output 案例格式优化** — P12.0 改为 pending 机制，P11 review 统一归档

#### MD 知识要改的

- [x] **numerical_rules.md 补表名搜索规则** — P10 知识分层后已融入 locate/rules.md
- [x] **systems_index.md 加表名关键词** — 已更新
- [x] **table_directory.md 增量更新机制** — gen_table_dir.py + rebuild_registry.py 已支持

#### CLI 工具要改的

- [x] `cli/search_table.py` — 按关键词搜表（已完成）
- [x] `cli/query.py` — SQL 查询（已完成）
- [x] `cli/search_table.py` 加 `--sample` 参数 — 已有 cli/query.py 替代，可直接 SQL 查询

#### 测试要改的

- [x] `test_hfsm.py` — 4 场景通过（已完成）
- [x] `test_numerical_sim.py` — 6 状态模拟通过（已完成）
- [x] 端到端真实需求验证 — P9-P11 清明节礼包已走通完整流程

### 6.7 战斗策划 hooks 补全
- [x] 战斗策划 hooks 实现 — P12.4 已重写 6 个 hooks
- [x] 端到端验证 — 待真实战斗需求时验证

### 6.8 执行策划 workflow 重构
- [x] 拆 `fill_confirm` → `fill`(llm) + `fill_confirm`(pause)
- [x] 砍 `review` 状态，`write` 直接写 Excel
- [x] 新建 `executor_fill_rules.md`（三重查询降级规则）
- [x] 新建 `id_relations.md`（跨表 ID 引用关系 + 逗号字段解析规则）
- [x] 更新 `executor_rules.md` / `executor_design_patterns.md` / `executor_handoff_contract.md`
- [x] fill 三级参考查找（主键→逗号字段跨表→兜底）
- [x] fill 链式参考查找（从参考主行提取 chain_ids）
- [x] fill_confirm 展示 en+cn 双语字段名
- [x] null ≠ 0 规则：代码层（write skip None）+ 知识库铁规
- [x] write 输出命名用需求名 + 同名加后缀
- [x] lineage_trace 记录 allocated_ids / data / id_replacements
- [x] 去掉 refresh_index 防止临时输出污染源索引
- [x] 新增 merge_confirm（pause）+ merge（script）状态
- [x] merge 增量合并到源 Excel + 刷新索引
- [x] executor_done.json — L2 完成信号
- [x] 测试验证通过（清明节礼包端到端 7 状态）
- [x] write + merge 全面迁移 COM Excel（win32com），去掉 openpyxl 写入
- [x] 清理死代码：file_ops.py 瘦身、删 merge_to_excel.py / exec_write_excel.py / combat_rules.md 等

---

## P7 — L3 自动化层：QA + Merge 分离 ✅

> 依赖：P6.8 执行策划 workflow 完成。
> 核心思路：执行策划不应自己改源表，QA 作为独立第三方审核，通过后才允许 merge。
> 设计参考：`architecture_design.md` L3 自动化层

### 7.1 L2 执行策划瘦身（7 状态 → 5 状态）✅

- [x] 从 `executor_hooks.py` 删除 `on_enter_merge_confirm`
- [x] 从 `executor_hooks.py` 删除 `on_enter_merge`
- [x] `on_enter_write` 成为 L2 终态，输出 `executor_done.json` 标记 L2 完成
- [x] 更新 `executor_workflow.py` 状态定义（去掉 merge_confirm / merge）
- [x] 更新 `executor_hooks.py` docstring（5 状态）

### 7.2 L3 QA Agent 新建（独立目录 + 状态机 + hooks）✅

> 和其他 Agent 一样的结构：qa_memory/process/ 下放 workflow + hooks

- [x] 新建 `agents/qa_memory/process/` 目录
- [x] 新建 `qa_workflow.py`（L3 状态机定义：qa → merge → done）
- [x] 新建 `qa_hooks.py`（L3 的 hook 文件）
- [x] `on_enter_qa`：读 `executor_done.json` → 调用 `qa_runner.run_qa()` 校验
  - 通过 → 自动进入 merge
  - 不通过 → 生成 rollback JSON → 通知用户 → 用户确认后打回 L2
- [x] `on_enter_merge`：COM Excel 写入源表 + 刷新 SQLite 索引（从 executor 搬过来）
- [x] `on_enter_done`：输出最终结果 + 变更日志

### 7.3 打回协议 ✅

- [x] 定义 L3→L2 打回数据格式：`{ error_log, original_output, failed_checks, retry_hint }`
- [x] QA 不通过 → 通知用户（展示报错 Log）→ 用户确认打回 → L2 从 `fill_confirm` 重入
- [x] 用户可选择：打回 L2 修改 / 手动修正 / 忽略继续

### 7.4 整合到 HFSM ✅

- [x] `hfsm_registry.py` 注册 L3 pipeline 子状态（qa → merge → done，从 qa_workflow.py 动态加载）
- [x] `machine_hooks.py` on_enter_pipeline 回调已有
- [x] `l3_transitions.json` 更新（删旧 merge_to_excel 引用，改为 qa→merge→done）
- [x] pipeline_done → completed（替代旧 pipeline_track）
- [x] executor_write → pipeline（替代旧 executor_review）

### 7.5 QA 校验规则完善 ✅

- [x] 规则 1：ID 空值 + 唯一性
- [x] 规则 2：跨表外键引用（精确 FK_MAP，不再模糊匹配）
- [x] 规则 3：Buff 因子白名单
- [x] 规则 4：必填字段非空
- [x] 规则 5：数值合理性（价格≥0）
- [x] 规则 6：格式校验（逗号分隔字段 3 的倍数）
- [x] 规则 7：新 ID 与源表无冲突

### 7.6 文档更新 ✅

- [x] `architecture_design.md` — L2 改为 5 状态，L3 改为 qa_memory agent
- [x] `l3_transitions.json` — 3 步 pipeline
- [x] `todo_architecture.md` — 本节

### 7.7 测试验证 ✅

- [x] 端到端：L2 write → L3 qa → merge → done → verify max_ids → rollback
- [x] QA 7 条规则全部运行正确
- [x] 回滚验证通过（3 张表 max_id 恢复原始值）

文件清单：
- `agents/qa_memory/process/qa_workflow.py` — L3 状态机（3 状态）
- `agents/qa_memory/process/qa_hooks.py` — 3 个 Hook
- `scripts/tools/qa_runner.py` — 7 条校验规则引擎（重写）
- `scripts/configs/l3_transitions.json` — 新 L3 pipeline 配置
- `scripts/core/hfsm_registry.py` — 注册 QA workflow
- `agents/executor_memory/process/executor_workflow.py` — 5 状态
- `agents/executor_memory/process/executor_hooks.py` — 删 merge，write 成终态

---

## P8 — 架构清晰度（LLM↔Hook 分工）

> 依赖：P7 完成。目标：确保全流程每个环节的 LLM/代码分工明确。

### 8.1 Combat 与 Executor 接口对齐
- [x] 确认 combat output.json 是否与 numerical 一致（含 `_ref_id`, `_overrides`） — 已一致，combat_hooks.py 注释明确标注
- [x] 如果一致，executor 可无差别处理两种 L1 输出 — on_enter_execute 已统一处理
- [x] 如果不一致，定义适配层或统一格式 — 不适用，格式已一致

### 8.2 Numerical fill 阶段 LLM 填值规则
- [x] L1 fill 阶段 LLM 填值的来源和优先级规则需要文档化 — P10.1 已拆出 fill/rules.md
- [x] 明确：哪些值 L1 必须给、哪些可以留给 L2 补 — fill/rules.md + _overrides 机制已明确

### 8.3 多行场景支持
- [x] 验证：一个需求需要加多行（如多个掉落物）时，`_ref_id` 和 draft 生成逻辑是否支持 — P10.5 已修复并测试通过
- [x] 如不支持，设计多行 `_ref_id` 机制 — 已支持，逐行 _ref_id + 连续 ID 分配

### 8.4 无参考行场景
- [x] 定义 `_ref_id` 为空时的行为：报错 vs 从零建行 — 代码已处理：返回空参考行，LLM 自填
- [x] 如需从零建行，定义 LLM 如何填所有字段 — P10.3 fill 处理 not_found + retry_locate 回退机制

---

## P9 — Pipeline 修复（2026-03-20）

> 已完成的 pipeline 稳定性修复。

### 9.1 null≠0 规则 ✅
- [x] `on_enter_fill` 自动生成 draft 时，null 值标 uncertain 而非转 0
- [x] `on_enter_fill_confirm` auto-save 正确 flatten `{value: null}` → null
- [x] `on_enter_write` skip None 值（不写空单元格）

### 9.2 Output xlsx 完整表头 ✅
- [x] `on_enter_write` 从源表 COM ReadOnly 复制 Row1-6 → output xlsx
- [x] `_read_xlsx_data` (QA) Row6 读表头，Row7+ 读数据
- [x] `on_enter_merge` 跳过 Row1-6，Row7+ 读增量

### 9.3 COM Excel 统一 ✅
- [x] `table_reader.py` 新增 `get_com_excel()` / `open_workbook()` / `close_com_excel()`
- [x] 所有 hooks + test 脚本统一走 `table_reader` COM 入口
- [x] 删除所有内联 `import win32com.client`

### 9.4 短 ID 根治 ✅
- [x] 重构 `on_enter_fill`：删除正则+链式+三级匹配（~140行），替换为 `_ref_id` 直查（~25行）
- [x] 更新 `executor_fill_rules.md`：删除链式查找文档，改为 `_ref_id` 直查

### 9.5 测试脚本增强 ✅
- [x] `quick_cleanup.py` 增加 output 目录清理 + agent 中间数据清理

---

## P10 — L1 locate 重设计 + 知识分层 ✅

> 依赖：P9 完成。目标：locate 状态增加参考行搜索，知识文件按层级拆分。

### 10.1 知识库分层（全项目 5 个 Agent）✅

> 统一规则：`knowledge/{agent}_rules.md`（Agent 层）+ `knowledge/{状态名}/rules.md`（状态层）

#### 10.1.1 numerical_memory ✅

**拆 `numerical_rules.md`**：
- [x] 保留第四章铁规 + 第六章踩坑 → Agent 层通用
- [x] 第五章字段过滤规则 → 移入 `knowledge/locate/rules.md`
- [x] 第一~三章数值字段/取值/模板 → 移入 `knowledge/fill/rules.md`

**新建状态级目录**：
- [x] `knowledge/locate/rules.md` — 字段过滤 + 参考行定位方式（_ref_id 或 search_keywords）
- [x] `knowledge/locate/examples.md` — locate 案例（清明节礼包的表选择+关键词）
- [x] `knowledge/fill/rules.md` — 数值取值 + not_found 处理 + _overrides/_note 输出规则
- [x] `knowledge/fill/examples.md` — fill 案例（清明节礼包的售价/限购）

**清理**：
- [x] `numerical_examples.md` 清理重复案例（当前 4 条重复）

**改 hooks**：
- [x] `numerical_hooks.py` on_enter_locate → 加载 `locate/rules.md` + `locate/examples.md`
- [x] `numerical_hooks.py` on_enter_fill → 加载 `fill/rules.md` + `fill/examples.md`

#### 10.1.2 executor_memory ✅

**新建 knowledge/ 目录，根目录 MD 全部移入**：
- [x] `executor_rules.md` → `knowledge/executor_rules.md`
- [x] `executor_design_patterns.md` → `knowledge/executor_design_patterns.md`
- [x] `executor_sheet_index.md` → `knowledge/executor_sheet_index.md`
- [x] `executor_fill_rules.md` → `knowledge/fill/rules.md`
- [x] `id_relations.md` → `knowledge/write/rules.md`

**改 hooks**：
- [x] `executor_hooks.py` `_load_md()` 路径全部更新

#### 10.1.3 combat_memory ✅

**清理重复（根目录和 knowledge/ 各一份）**：
- [x] 删根目录 `combat_understanding.md`（保留 knowledge/ 内的）
- [x] 删根目录 `combat_translation.md`
- [x] 删根目录 `combat_condition_map.md`
- [x] 删根目录 `combat_examples.md`
- [x] 移 `combat_hooks.py` → `process/`（已有一份则删根目录的）

**按状态分层**：
- [x] `combat_understanding.md` → `knowledge/understand/rules.md`
- [x] `combat_translation.md` + `combat_condition_map.md` → `knowledge/translate/rules.md`
- [x] 新建 `knowledge/combat_rules.md`（从 understanding 提取通用铁规）

#### 10.1.4 qa_memory ✅

**新建 knowledge/ 目录**：
- [x] `qa_rules.md` → `knowledge/qa_rules.md`
- [x] `qa_understanding.md` + `qa_execution.md` → 合并为 `knowledge/qa/rules.md`
- [x] `qa_design_patterns.md` → `knowledge/qa_design_patterns.md`

#### 10.1.5 coordinator_memory ✅

**已有 knowledge/，只加状态级**：
- [x] 新建 `knowledge/dispatch/rules.md`（路由规则：需求类型→Agent 映射）

### 10.2 on_exit_locate 新增参考行搜索 ✅
- [x] 新增 `on_exit_locate` hook
- [x] 读 locate_result.json → 有 `_ref_id` 跳过，有 `search_keywords` 搜源表
- [x] 搜结果写入 `ref_candidates[]` + `ref_status`

### 10.3 fill 处理 not_found + 回退 locate ✅
- [x] fill 阶段读 `ref_status` → not_found 时问用户补 _ref_id
- [x] 用户补 _ref_id → 写入 locate_result.json → 触发 retry_locate 回到 locate
- [x] on_exit_locate 已有逻辑自动处理（有 _ref_id → 跳过搜索 → found）

### 10.4 HFSM 注册回退事件 ✅
- [x] 注册 `retry_locate` 事件：fill → locate
- [x] numerical_workflow.py 加 transition 定义

### 10.5 多行 Bug 修复 ✅
- [x] `on_enter_fill` 逐行查参考行（原来只查 rows[0] 的 _ref_id）
- [x] `on_enter_write` 逐行分配连续 ID（原来只给 rows[0] 分配新 ID）
- [x] 多行测试通过：3 行 _DropGroup（300111/300112/300113）+ QA 7 规则 + merge

---

## P11 — L0 review 回顾 + 案例归档 + 会话清理 ✅

> 依赖：P10 完成。目标：L3 完成后自动回到 L0 review，生成回顾报告、归档案例、清理中间数据。

### 11.1 L0 review 状态实现 ✅

**修改 coordinator_workflow.py**：
- [x] 增加 `wait_sub` 和 `review` 状态
- [x] 增加转移：`dispatched → wait_sub`，`sub_done → review`，`reviewed → done`

**新增 on_enter_review hook**：
- [x] 读 `qa_memory/l3_done.json`（变更摘要：表名、行数、ID）
- [x] 读 `output/任务名/lineage_trace.json`（完整数据 + 跨表引用）
- [x] 生成回顾报告返回给 LLM，LLM 输出用户可读的摘要

### 11.2 案例自动归档 ✅

> review hook 从 lineage_trace 提取案例，追加到状态级 examples.md

**locate 案例归档**：
- [x] 提取：表名 + _ref_id + search_keywords（如有）
- [x] 追加到 `numerical_memory/knowledge/locate/examples.md`

**fill 案例归档**：
- [x] 提取：_ref_id + _overrides + _note
- [x] 追加到 `numerical_memory/knowledge/fill/examples.md`

**需求级案例归档**：
- [x] 提取：需求名 + 模块列表 + 涉及表
- [x] 追加到 `numerical_memory/knowledge/numerical_examples.md`

### 11.3 异常检测 ✅

> 不阻塞，仅提示用户。review 阶段自动检查。

- [x] **跨表引用完整性**：Item.params 是否包含所有同批 _DropGroup ID
- [x] **名字/描述未修改**：新行的名字是否仍是参考行原名（应该改成新名字）
- [x] **_overrides 是否生效**：对比 filled_result 和 lineage_trace，确认覆盖字段已写入

### 11.4 任务结束清理 ✅

> L0 review 完成后（on_exit_review），清除本轮中间数据，保留最终产物。

**保留**：
- `output/任务名/`（xlsx + lineage_trace.json）
- 已归档到 examples.md 的案例

**清除**：
- [x] `numerical_memory/data/*.json`（locate_result, filled, output）
- [x] `executor_memory/data/*.json`（execute_result, align_result, draft_filled, filled_result, output, executor_done）
- [x] `qa_memory/*.json`（qa_result, merge_result, l3_done）
- [x] `coordinator_memory/data/*.json`（如有）

**实现**：
- [x] `on_enter_done` hook 遍历各 agent data 目录，删除 JSON 中间文件
- [x] 保留白名单文件（KEEP_FILES 配置）
- [x] LLM 上下文重置：输出"任务完成"信号，清除对话历史
- [x] 每个状态的 LLM 调用应为独立 API call（不继承上一轮任务的对话历史）

---

## P12 — Agent 文件结构统一 + 代码去重

> 依赖：P11 完成。目标：统一所有 Agent 的 workflow/hooks 结构，提取公共函数，消除重复代码。
> 最后更新: 2026-03-23

### 12.0 案例暂存区机制（pending_examples.json）✅

> 中间步骤禁止直接写 examples.md，必须走 pending → L0 review 提交。

- [x] `numerical_hooks.py` on_enter_match → 覆盖写 pending（初始化）
- [x] `numerical_hooks.py` on_exit_confirm → 改写 pending（原直写 numerical_examples.md）
- [x] `numerical_hooks.py` on_exit_output → 改写 pending（原直写 numerical_examples.md）
- [x] `coordinator_hooks.py` on_enter_parse → 覆盖写 pending（初始化）
- [x] `coordinator_hooks.py` on_exit_user_confirm → 改写 pending（原直写 coordinator_examples.md）
- [x] `coordinator_hooks.py` on_enter_review → 删除 4a/4b/4c 硬编码归档，改为遍历各 Agent 的 pending 提交
- [x] `test_knowledge_sim.py` → 41/41 通过（含 pending 初始化/追加/examples.md 未修改 验证）

### 12.1 提取公共 Hook 工具函数 ✅

> 3 个 hooks 文件各自定义了相同的 `_load_json`、`_save_json`、`_load_md`。

**[NEW] `scripts/core/hook_utils.py`**：
- [x] `load_json(filepath)` — 当前 numerical/executor 各有一份完全相同的实现
- [x] `save_json(filepath, data)` — 同上
- [x] `load_md(knowledge_dir, filename)` — 接受 knowledge_dir 参数，统一查找逻辑
- [x] `load_md_batch(knowledge_dir, filenames)` — 批量版（替代 coordinator 的 _load_md_files）
- [x] `append_pending(data_dir, target, content)` — pending 追加封装
- [x] `init_pending(data_dir, task_id='', requirement='')` — pending 初始化封装

**改 3 个 hooks 文件**：
- [x] `numerical_hooks.py` — 删除 `_load_json`/`_save_json`/`_load_md`，改为 `from hook_utils import ...`
- [x] `executor_hooks.py` — 同上
- [x] `coordinator_hooks.py` — 删除 `_load_md_files`，改为 `from hook_utils import ...`

### 12.2 统一路径常量 ✅

> 当前 4 个 hooks 文件各自硬编码 `G:\op_design`。`constants.py` 已有 `REFERENCES_DIR`。

**[MODIFY] `scripts/core/constants.py`**：
- [x] 新增 `AGENTS_DIR = os.path.join(REFERENCES_DIR, 'agents')`
- [x] 新增 `def agent_paths(agent_name)` → 返回 `{agent_dir, knowledge_dir, data_dir, process_dir}`

**改 4 个 hooks 文件**：
- [x] `numerical_hooks.py` — 改用 `agent_paths('numerical_memory')`
- [x] `executor_hooks.py` — 改用 `agent_paths('executor_memory')`
- [x] `coordinator_hooks.py` — 改用 `agent_paths()`（含 review/done 内部的局部变量）
- [x] `qa_hooks.py` — 改用 `agent_paths()` + 迁移 `_load_json/_save_json` 到 hook_utils

### 12.3 统一 workflow hooks 映射格式 → 并入 12.4 ✅

> coordinator_workflow.py 从嵌套格式统一为扁平格式。

### 12.4 处理 combat_hooks.py 重复 + 统一 workflow 格式 ✅

> `combat_memory/process/combat_hooks.py` 原为 `validate_combat_handoff` 的副本，已重写为真正的状态机 hooks。

- [x] 重写 `combat_hooks.py` — 6 个状态机 hooks（on_enter_match/split/categorize/translate/output + on_exit_confirm）
  - [x] 使用 `hook_utils` + `agent_paths`
  - [x] pending 机制（init_pending + append_pending）
- [x] 重写 `combat_workflow.py` — 从 4 状态扩为 7 状态（match/split/confirm/categorize/translate/output/review）
  - [x] 知识映射修正为实际文件名（understand/rules.md 等）
  - [x] hooks 映射用扁平格式
- [x] 统一 `coordinator_workflow.py` hooks 为扁平格式
- [x] 保留 `scripts/combat/combat_validator.py`（正确位置的 validator）

### 12.5 铁规文档化 ✅

> 将 pending 机制和 MD 写入规则写入全局规则文档。

- [x] `coordinator_rules.md` 加铁规第4条：中间状态禁止写 examples.md，只有 L0 review 可提交
- [x] `numerical_rules.md` 加铁规第6条：案例写入一律走 pending，match 阶段覆盖写清残留

