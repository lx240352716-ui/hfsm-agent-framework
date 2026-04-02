# 游戏配表 AI Agent 系统 — 分层状态机架构设计

> 版本 2.0 | 2026-03-17

---

## 一、核心设计原则

| 原则 | 说明 |
|------|------|
| **大模型只做理解，脚本负责执行** | MD 帮 AI 想清楚，脚本帮 AI 做对事 |
| **配置驱动，消灭幻觉** | 路由、默认值、校验规则全在 JSON，不在 MD |
| **状态机管"谁做"，Workflow 管"怎么做"** | 层间解耦，改一个角色不影响其他角色 |
| **结构性错误靠脚本，语义性错误靠用户** | 脚本 catch ID 不存在；用户 catch ID 用错了 |
| **错误写入记忆，不再重犯** | 用户纠正 → lessons.md → 自主学习闭环 |
| **先验证再抽象** | 不造引擎框架，先用真实任务走通整条链 |

---

## 二、Agent 精简（7 → 4）

### 删除的 Agent

| 原 Agent | 原职责 | 为什么删 | 新归属 |
|----------|--------|---------|--------|
| 资深策划 | 定 Scope + Review | Scope = 查映射表，主策划能做；Review = 脚本 + 用户 | 主策划 + QA 脚本 |
| QA Agent | 校验主键/外键/白名单 | 全是硬性规则，纯脚本 | qa_runner.py |
| 写入 Agent | 合并数据 | 纯脚本 | merge_to_excel.py |

### 保留的 4 个 Agent

| Agent | 层级 | 核心思考能力 | 为什么需要大模型 |
|-------|------|------------|----------------|
| **主策划** | L0 决策 | 理解需求 → 拆模块 → 派发 | 复杂需求拆分（如 UR 装备 12 模块） |
| **战斗策划** | L1 设计 | 拆句 → 四要素 → 结构化设计 | 自然语言→配表字段的语义转换 |
| **数值策划** | L1 设计 | 查参考值 → 确认参数 | 数值合理性判断 |
| **执行策划** | L2 执行 | 接收设计 → 补全 → 分配 ID | 字段补全的业务逻辑 |

---

## 三、分层状态机

### 层级定义

```
L0  决策层 ── 主策划
       ↓ routing.json
L1  设计层 ── 战斗策划 / 数值策划（按需）
       ↓ handoff JSON
L2  执行层 ── 执行策划
       ↓ executor_done.json
L3  QA Agent ── QA → Merge → Done
```

### 分层规则

| 规则 | 说明 |
|------|------|
| 层内回退不升级 | QA 打回执行策划，主策划不参与 |
| 跨层回退需升级 | L2 发现设计有漏洞，回 L1，主策划介入 |
| 层间通过 handoff 传递 | 结构化 JSON，格式由 handoff_contract.md 约定 |
| 用户确认 = 状态转换门槛 | L1→L2 前用户确认设计方案 |
| **打回必带上下文** | 回退时携带：报错 Log + 原始 handoff + 失败步骤 |

### 状态转换总图

```
                    ┌─────────────────────┐
                    │  L0 决策层           │
                    │  ┌───────────────┐  │
  用户需求 ────────►│  │   主策划       │  │
                    │  │ 理解→分类→派发 │  │
                    │  └───────┬───────┘  │
                    └──────────┼──────────┘
                               │ routing.json
                    ┌──────────▼──────────┐
                    │  L1 设计层           │
                    │  ┌──────┐ ┌──────┐  │
                    │  │战斗  │ │数值  │  │
                    │  │策划  │ │策划  │  │
                    │  └──┬───┘ └──┬───┘  │
                    │     └──┬─────┘      │
                    │        ▼            │
                    │   用户确认设计方案    │◄── 错了→lessons
                    └────────┬────────────┘
                             │ handoff
                    ┌────────▼────────────┐
                    │  L2 执行层           │
                    │  ┌───────────────┐  │
                    │  │   执行策划     │  │
                    │  │ resolve→align  │  │
                    │  │ →fill→ids     │  │
                    │  │ →staging      │  │
                    │  └───────┬───────┘  │
                    └──────────┼──────────┘
                               │ 触发脚本
                    ┌──────────▼──────────┐
                    │  L3 自动化层         │
                    │  QA ──► Merge ──►   │
                    │  │       │     追踪  │
                    │  ▼不通过  │          │
                    │  打回L2（带报错Log） │
                    └─────────────────────┘
                               │ 通过
                               ▼
                          用户确认完成
```

---

## 三-B、Agent 标准化三层架构

> **核心思想**：大模型只管"想"，脚本负责"做"和"搬"。

每个 Agent 的内部文件按 **知识层 / 流程层 / 数据层** 三类组织：

```
agent_memory/
  │
  ├── 📚 知识层（Knowledge — 给 LLM 读的上下文）
  │   ├── knowledge.md       # 领域知识：概念、规则、表关系
  │   ├── rules.md           # 铁规：必须遵守的硬约束
  │   ├── examples.md        # 案例：做过的实现参考
  │   └── lessons.md         # 教训：踩坑与纠正记录
  │
  ├── ⚙️ 流程层（Process — 驱动自动化执行）
  │   ├── workflow.json      # 工作流：步骤定义与顺序
  │   ├── hooks.py           # 钩子脚本：workflow 中可调用的 Python 函数
  │   └── transitions.json   # 🆕 关联与切换：可跳转目标 + 条件
  │
  └── 📦 数据层（Data — 业务数据交换，不经过 LLM）
      ├── input.json         # 🆕 上游传入的结构化数据
      ├── output.json        # 🆕 本 Agent 产出的结构化数据
      └── config.json        # 本 Agent 的静态配置（默认值、ID 段位等）
```

### 三层职责边界

| 层 | 谁读 | 谁写 | 内容生命周期 |
|----|------|------|------------|
| 知识层 | LLM | 人类 / AI 协作 | 长期稳定，偶尔更新 |
| 流程层 | 脚本引擎 | 人类 | 架构期定义，运行期只读 |
| 数据层 | 脚本 | 脚本 | 每次任务重建，用完即归档 |

> **关键约束**：数据层的 `input.json` / `output.json` 由 Python 脚本读写，
> **禁止** LLM 在对话中复制粘贴传递大段 JSON — 这是消灭幻觉的核心手段。

### `transitions.json` 结构定义

每个 Agent 的 `transitions.json` 描述它与其他 Agent 的关联关系和切换条件：

```json
{
  "agent": "combat",
  "layer": "L1",
  "can_handoff_to": [
    {
      "target": "executor",
      "condition": "design_approved_by_user",
      "data_contract": "handoff_contract.md"
    }
  ],
  "can_escalate_to": [
    {
      "target": "coordinator",
      "condition": "scope_exceeds_combat",
      "payload": ["error_log", "original_requirement"]
    }
  ],
  "can_receive_rejection_from": [
    {
      "source": "executor",
      "condition": "missing_fields_in_handoff",
      "payload": ["error_log", "original_handoff", "failed_step"]
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `can_handoff_to` | 正向流转：完成后交给谁 |
| `can_escalate_to` | 升级：超出自身能力范围时向上报 |
| `can_receive_rejection_from` | 被打回：谁可能把任务退回来，以及退回时必须携带什么 |
| `condition` | 触发条件（枚举值，脚本可判断） |
| `data_contract` | 数据格式契约文档 |
| `payload` | 切换时必须携带的上下文字段 |

---

## 四、每个 Agent 的文件结构（目标态）

> 按三层架构统一展示。🆕 标记为需要新建的文件。

### L0 主策划 `coordinator_memory/`

| 层 | 文件 | 说明 |
|----|------|------|
| 📚 知识 | `knowledge.md` | 模块体系、需求类型、表关系 |
| 📚 知识 | `examples.md` | 做过的案例 |
| 📚 知识 | `lessons.md` | 踩坑记录 |
| 📚 知识 | `module_table_map.md` | 模块→表映射 |
| ⚙️ 流程 | `routing.json` | 需求类型→角色映射（等价于 workflow） |
| ⚙️ 流程 | 🆕 `transitions.json` | 可派发目标 + 接收回退条件 |
| 📦 数据 | 🆕 `input.json` | 接收用户需求的结构化解析结果 |
| 📦 数据 | 🆕 `output.json` | 派发给 L1 的路由结果 + 拆分后的子任务 |
| 管理 | `todo_architecture.md` / `done.md` | TODO |

### L1 战斗策划 `combat_memory/`

| 层 | 文件 | 说明 |
|----|------|------|
| 📚 知识 | `combat_understanding.md` | 四要素拆解方法论 |
| 📚 知识 | `combat_translation.md` | 需求→字段翻译 |
| 📚 知识 | `combat_examples.md` | 实现参考 |
| 📚 知识 | `combat_condition_map.md` | 条件 ID 映射 |
| 📚 知识 | `combat_rules.md` | 铁规 |
| 📚 知识 | `combat_clause_checklist.md` | 子句核对清单 |
| ⚙️ 流程 | `combat.json`（在 workflows/） | 拆句→分类→翻译→交付 |
| ⚙️ 流程 | `combat_hooks.py` | 校验钩子 |
| ⚙️ 流程 | 🆕 `combat_transitions.json` | 正向→executor，升级→coordinator |
| 📦 数据 | 🆕 `input.json` | 接收 L0 路由过来的需求 |
| 📦 数据 | 🆕 `output.json` | 输出设计方案（handoff 格式） |

### L1 数值策划 `numerical_memory/`

| 层 | 文件 | 说明 |
|----|------|------|
| 📚 知识 | `numerical_master_knowledge.md` | 数值知识库 |
| 📚 知识 | `numerical_understanding.md` | 字段位置、取值规则 |
| 📚 知识 | `numerical_design_patterns.md` | 数值模板 |
| 📚 知识 | `numerical_design_decisions.md` | 决策记录 |
| ⚙️ 流程 | `numerical.json`（在 workflows/） | 轻量工作流，强制 handoff 格式 |
| ⚙️ 流程 | 🆕 `numerical_hooks.py` | 数值校验钩子 |
| ⚙️ 流程 | 🆕 `numerical_transitions.json` | 正向→executor，升级→coordinator |
| 📦 数据 | 🆕 `input.json` | 接收 L0 路由过来的需求 |
| 📦 数据 | 🆕 `output.json` | 输出数值方案（handoff 格式） |

### L2 执行策划 `executor_memory/`

| 层 | 文件 | 说明 |
|----|------|------|
| 📚 知识 | `executor_rules.md` | 铁规 |
| 📚 知识 | `executor_handoff_contract.md` | handoff 格式契约 |
| 📚 知识 | `executor_design_patterns.md` | 设计模式 |
| 📚 知识 | `executor_sheet_index.md` | 表列含义 |
| ⚙️ 流程 | `executor.json`（在 workflows/） | execute→align→fill→fill_confirm→write |
| ⚙️ 流程 | `executor_hooks.py` | 5 个 Hook |
| ⚙️ 流程 | 🆕 `executor_transitions.json` | 正向→L3 QA，打回→combat/numerical |
| 📦 数据 | `table_defaults.json` | 默认值配置 |
| 📦 数据 | `id_ranges.json` | ID 段位配置 |
| 📦 数据 | 🆕 `input.json` | 接收 L1 的 handoff 数据 |
| 📦 数据 | 🆕 `output.json` | 输出 staging 数据（给 L3 脚本） |

### L3 QA Agent `qa_memory/`

| 层 | 文件 | 说明 |
|----|------|------|
| ⚙️ 流程 | `qa_workflow.py` | 状态机：qa → merge → done |
| ⚙️ 流程 | `qa_hooks.py` | 3 个 Hook（校验/合并/完成） |
| ⚙️ 流程 | `qa_runner.py`（在 tools/） | 7 条校验规则引擎 |
| ⚙️ 流程 | `l3_transitions.json` | 通过→完成，不通过→打回 L2 |

---

## 五、防线体系

```
┌─────────────────────────────────────────────┐
│  第一道：自动化脚本（结构性错误）            │
│  ID 不存在/重复、外键断裂、因子不在白名单    │
│  → 脚本报错打回，不需要人工                  │
├─────────────────────────────────────────────┤
│  第二道：用户确认（语义性错误）              │
│  时机 ID 用错、数值不合理、设计有逻辑问题    │
│  → 用户纠正 → Agent lessons → 不再犯        │
└─────────────────────────────────────────────┘
```

---

## 六、已知风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 状态机引擎工程量大 | 造框架容易翻车 | **先不造引擎**，用 MVP 真实任务验证架构，再抽象 |
| 回退时上下文断裂 | AI 被打回后不知道改哪里 | 打回协议：必须携带报错 Log + 原始 handoff + 失败步骤标识 |
| 数值策划无 Workflow | 输出格式不受控 | 补 `numerical.json` 轻量工作流 |
| `standard.json` 仍存在 | 新旧架构冲突 | MVP 验证通过后再决定废弃/重写 |

---

## 七、文件清理（20 个操作）

### 删除 11 个

| 文件 | 原因 |
|------|------|
| `coordinator_memory/execution.md` | 被状态机取代 |
| `coordinator_memory/summary.md` | 重复 |
| `coordinator_memory/numerical_design_knowledge.md` | 不属于主策划 |
| `combat_memory/execution.md` | 合并到 combat_rules.md |
| `executor_memory/execution.md` | SOP 在 workflow |
| `executor_memory/understanding.md` | 合入 executor_rules |
| `executor_memory/summary.md` | 重复 |
| `numerical_memory/summary.md` | 重复 |
| `qa_memory/summary.md` | 重复 |
| `senior_memory/summary.md` | 重复 |
| `user_preferences/preferences.md` | 全空 |

### 移动 3 个

| 文件 | 从 → 到 |
|------|---------|
| `module_table_map.md` | senior → coordinator |
| `numerical_sheet_index.md` | senior → executor |
| `s6_equip_check.md` | senior → 合入 executor_rules |

### 新建 3 个

| 文件 | 说明 |
|------|------|
| `coordinator/knowledge.md` | 通用知识 |
| `coordinator/examples.md` | 案例 |
| `coordinator/lessons.md` | 教训 |

### 目录归并 3 个

| 操作 | 说明 |
|------|------|
| 删 `senior_memory/` | 有价值文件已移走 |
| 删 `user_preferences/` | 全空 |
| 合并 `执行策划/` 到 `executor_memory/` | 统一目录 |

---

## 八、优先级执行路线图

### 依赖关系

```
P0 架构定稿
 ├──► P0.5 MVP 验证（用真实需求跑通全链路）
 │      │
 │      ├── 成功 → P2 路由 → P3 数值Workflow → P4 状态机引擎
 │      └── 失败 → 回 P0 修改架构
 │
 └──► P1 MD清理（可与 P0.5 并行，不改代码）
```

### P0 — 架构设计定稿 ⏱ 1天

> 依赖：无。所有后续工作都依赖 P0。

| 决策项 | 选项 | 判定标准 |
|--------|------|---------|
| 分层状态机架构（4 Agent + 自动化层） | 确认 / 修改 | 本文档七章内容全部审核通过 |
| 打回/回退协议 | 定义数据格式 | 报错 Log + 原始 handoff + 失败步骤标识 |
| `standard.json` 去留 | 保留 / 废弃 / 拆分 | MVP 验证后决定 |

### P0.5 — MVP 验证 ⏱ 1-2天

> 依赖：P0。目的：先跑通再抽象，不造无用的引擎框架。

| 步骤 | 做什么 | 验证什么 |
|------|--------|---------|
| 1 | 选一个简单真实需求（如"纯数值调整"） | — |
| 2 | 手动模拟 L0 主策划分类 | routing 逻辑是否成立 |
| 3 | 手动模拟 L1 数值策划设计 | handoff 格式是否够用 |
| 4 | 用 execution.json 执行 L2 | 现有 Workflow 引擎是否兼容 |
| 5 | 触发 L3 QA + Merge | 自动化层是否无缝衔接 |
| 6 | 模拟一次打回 | 报错信息是否足够 AI 修正 |
| **判定** | 全链路跑通 → P2 | 跑不通 → 回 P0 修设计 |

### P1 — MD 文件清理 ⏱ 1天（与 P0.5 并行）

> 依赖：P0。不改代码，低风险。

| 子任务 | 数量 | 风险 |
|--------|------|------|
| 删除冗余文件 | 11 个 | 低（已确认无引用） |
| 移动文件 | 3 个 | 低 |
| 新建知识库文件 | 3 个 | 中（内容需从旧文件提取整理） |
| 修复 MD 内容 | 3 个 | 中（translation.md 改动最大） |
| 目录归并 | 3 个 | 低 |

### P2 — 路由配置 ⏱ 1天

> 依赖：P0.5 MVP 通过。

- 创建 `routing.json`
- 分类结果校验逻辑
- `test_routing.py` 测试

### P3 — 数值策划 Workflow ⏱ 半天

> 依赖：P0.5 中确认输出格式。

- 创建 `numerical.json`
- 强制 handoff JSON 格式

### P4 — 状态机引擎 ⏱ 视 MVP 结果

> 依赖：P0.5 结论。**如果 MVP 手动走通且不需要复杂调度，则不做 P4。**

| 条件 | 决策 |
|------|------|
| MVP 手动走通，流程简单 | 不写引擎，靠 AI 对话串联 |
| MVP 暴露了需要自动回退/并行的场景 | 写轻量引擎或改造 workflow.py |

### 总工期估算

```
P0（1天）──► P0.5（1-2天）──► P2（1天）──► P3（半天）──► P4（视情况）
      │
      └──► P1（1天，并行）

最短路径：3.5 天（如果 P4 不做）
最长路径：5+ 天（如果 P4 需要写引擎）
```
