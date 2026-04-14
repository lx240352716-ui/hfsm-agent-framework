---
description: "启动策划工作流 — 激活分层状态机，从主策划(L0)开始"
allowed-tools: ["Bash", "FileRead", "FileWrite"]
arguments: ["requirement"]
argument-hint: "需求描述，如：新增SP角色-风暴骑士 / 新增一个被动技能-暴击回血"
whenToUse: "用户要做一个完整的新功能（新角色、新技能体系、新系统），涉及多张表和多个角色协作"
---

# /design — 策划工作流入口

激活后，你（LLM）进入**状态机驱动**模式。状态机管流程，hooks 管每步做什么。

用户的需求：${requirement}

## 核心机制

```
状态机转移 → on_enter hook 触发 → hook 返回 {instruction, knowledge}
  → 你按 instruction 工作 → 完成后用 --trigger 推进 → 下一个 hook 触发
```

**你不需要自己判断"下一步做什么"，hook 会告诉你。**

## 启动

// turbo

```shell
python scripts/core/hfsm_bootstrap.py
```

读取输出中的：

- **当前状态**和**当前步骤**：确认你在哪
- **知识库**：加载列出的 MD 文件
- **可用触发器**：完成当前步骤后用哪个

## 工作循环

每个状态的工作流程都是一样的：

1. **状态机进入新状态** → on_enter hook 返回 instruction 和 knowledge
2. **你加载 knowledge**（hook 指定的 MD 文件）
3. **你按 instruction 执行**（hook 告诉你这步具体做什么）
4. **完成后推进状态**：

```shell
# 查看当前可用的触发器
python scripts/core/hfsm_bootstrap.py --list-triggers

# 用对应触发器推进
python scripts/core/hfsm_bootstrap.py --trigger <trigger_name>
```

1. **状态机转移** → 新的 on_enter hook 触发 → 回到步骤 1

## 用户确认（pause 类型状态）

当进入 `user_confirm` 等 pause 类型状态时：

- **暂停并展示结果给用户**
- **等用户说"确认"后**才能 `--trigger user_confirmed`
- 铁规：不确认不往下走

## 常用命令速查

```shell
# 启动/恢复状态机
python scripts/core/hfsm_bootstrap.py

# 查看当前可用触发器（含目标状态和 Guard 条件）
python scripts/core/hfsm_bootstrap.py --list-triggers

# 推进状态
python scripts/core/hfsm_bootstrap.py --trigger parse_done
python scripts/core/hfsm_bootstrap.py --trigger split_done
python scripts/core/hfsm_bootstrap.py --trigger user_confirmed
python scripts/core/hfsm_bootstrap.py --trigger dispatched

# 快速模式（跳过 L0 直接进 L1）
python scripts/core/hfsm_bootstrap.py --start-at L1.combat
```

## 注意事项

- **听 hook 的指令**：不要自作主张，hook 说做什么就做什么
- **每步必 trigger**：完成工作后必须 `--trigger` 推进，否则状态机不动
- **不可跳步**：Guard 会拦截违规操作
- **不确定就问**：不确定的内容向用户确认，不要猜
