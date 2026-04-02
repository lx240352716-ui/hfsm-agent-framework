---
description: "快速修改：改数值、调参数、做变体，30行以内的小改动"
allowed-tools: ["Bash", "FileRead", "FileWrite"]
arguments: ["change"]
argument-hint: "改动描述，如：凯多暴击伤害1.2→1.5 / 暴击率5%改8%"
whenToUse: "用户要改一个数值、调一个参数、做一个变体，改动很小且有现成模板"
---

# 快速修改（S_Express 模式）

用户要做的改动：${change}

## 铁规

1. **必须执行现有脚本**，禁止新建脚本，禁止 `python -c`
2. **不编造因子名或表结构**，不确定用 `check_factor.py` 查
3. **用户确认后才能执行修改，不确认不改**
4. **所有规则从 CLAUDE.md 的 S_Express 段落读取**，不要自己发明流程

## 适用条件检查

先读 `CLAUDE.md` 的 S_Express 段落，确认满足条件：
- ✅ `agents/combat_memory/knowledge/design_patterns.md` 中有同类模板
- ✅ 变更 < 30 行
- ✅ 不涉及新建表

**如果不满足任一条件**，告诉用户"这个改动比较复杂，建议用 `/design` 走完整流程"，并说明原因。不要强行继续。

## 步骤

### Step 1: 判断领域

读取 `agents/coordinator_memory/knowledge/coordinator_rules.md`，判断该改动属于战斗策划还是数值策划。

**完成标准**：确定 --start-at 的目标状态（L1.combat 或 L1.numerical）。

### Step 2: 启动状态机

// turbo
```shell
python scripts/core/hfsm_bootstrap.py --start-at <目标状态>
```

**完成标准**：状态机从 L1 启动成功，输出了知识库文件列表。

### Step 3: 加载知识并出方案

读取状态机输出的知识库文件，按对应 Agent 的流程：
1. 从 `design_patterns.md` 找同类模板
2. 校验因子：

// turbo
```shell
python scripts/cli/check_factor.py <因子名>
```

3. 查现有数据：

// turbo
```shell
python scripts/cli/query.py "<SQL语句>"
```

**完成标准**：有明确的修改方案（改哪张表、哪个字段、从什么值改到什么值）。

### Step 4: 用户确认

将修改方案展示给用户：

| 表 | 操作 | 字段 | 旧值 | 新值 |
|---|---|---|---|---|

**等用户说"确认"后才继续。不确认不改。**

### Step 5: 执行

用户确认后，按状态机流程继续推进到 L2 执行，输出到 `output/{任务名}/`。

**完成标准**：修改已输出，CHANGES.md 已生成。
