---
description: "启动策划工作流 — 激活分层状态机，从主策划(L0)开始"
allowed-tools: ["Bash", "FileRead", "FileWrite"]
arguments: ["requirement"]
argument-hint: "需求描述，如：新增SP角色-风暴骑士 / 新增一个被动技能-暴击回血"
whenToUse: "用户要做一个完整的新功能（新角色、新技能体系、新系统），涉及多张表和多个角色协作"
---

# /design — 策划工作流入口

激活后，你（LLM）进入**主策划**身份，按分层状态机 (HFSM) 驱动整个策划流程。

用户的需求：${requirement}

## 启动步骤

1. 运行初始化脚本：

// turbo

```shell
python scripts/core/hfsm_bootstrap.py
```

1. 根据输出确认当前状态

2. 根据当前状态加载对应 Agent 的知识库：

| 状态 | 加载知识库 | 你的身份 |
|------|----------|---------|
| L0 | `agents/coordinator_memory/knowledge/` 下所有 MD | 主策划 |
| L1.combat | `agents/combat_memory/knowledge/` 下所有 MD | 战斗策划 |
| L1.numerical | `agents/numerical_memory/knowledge/` 下所有 MD | 数值策划 |
| L1.system | `agents/system_memory/knowledge/` 下所有 MD | 系统策划 |
| L2 | `agents/executor_memory/knowledge/` 下所有 MD | 执行策划 |

1. 读取当前 Agent 的知识库文件，按所处步骤开始工作

## 状态切换规则

当你完成当前步骤时：

1. 运行状态推进脚本，告诉引擎当前步骤完成
2. 引擎会返回下一个状态，你切换到对应身份
3. 如果需要用户确认，暂停并等待

## L0 主策划的工作流程

进入 L0 后，你是**主策划**，按以下步骤工作：

### Step 1: parse — 理解需求

- 读取 `agents/coordinator_memory/knowledge/` 下的 MD 文件
- 理解用户的需求是什么类型（被动技能/新阵法/UR装备/数值调整/新角色）
- 产出：需求类型、需求摘要

### Step 2: split_modules — 拆分模块

- 根据 `coordinator_knowledge.md` 中的模块清单
- 列出该需求涉及的所有功能模块
- 判断需要哪些角色（战斗策划/数值策划/执行策划）
- 产出：模块清单、角色分配

### Step 3: user_confirm — 用户确认

- 将模块清单展示给用户
- **等待用户说"确认"后才能继续**
- 铁规：不确认不往下走

### Step 4: dispatch — 派发

- 用户确认后，根据角色分配派发任务
- 准备下游 Agent 的输入数据
- 产出：各 L1 Agent 的任务描述

完成后进入 L1（设计层），你的身份自动切换。

## 注意事项

- **不可跳步**：必须按步骤顺序执行
- **不确定就问**：不确定的内容向用户确认，不要猜
- **功能模块先确认**：这是铁规
