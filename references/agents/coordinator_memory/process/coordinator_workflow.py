# -*- coding: utf-8 -*-
"""
主策划 Workflow 定义

声明式配置：状态、转移、知识库、hooks。
由 hfsm_registry.py 读取并自动组装到 HFSM 中。
"""

# ── 基本信息 ──
name = "coordinator"
description = "主策划：理解需求 → 拆模块 → 确认 → 派发 → 等待执行 → 回顾 → 完成"

# ── 初始状态 ──
initial = "parse"

# ── 状态列表 ──
states = [
    {"name": "parse",         "type": "llm",    "description": "理解用户需求"},
    {"name": "split_modules", "type": "llm",    "description": "拆分功能模块"},
    {"name": "user_confirm",  "type": "pause",  "description": "等用户确认模块清单"},
    {"name": "dispatch",      "type": "script", "description": "根据确认结果派发给下游"},
    {"name": "wait_sub",      "type": "pause",  "description": "等待 L1→L2→L3 完成"},
    {"name": "review",        "type": "script", "description": "回顾任务结果、归档案例、异常检测"},
    {"name": "done",          "type": "script", "description": "清理中间数据、标记任务完成"},
]

# ── 状态转移 ──
transitions = [
    ["parse_done",     "parse",         "split_modules"],
    ["split_done",     "split_modules", "user_confirm"],
    ["user_confirmed", "user_confirm",  "dispatch"],
    ["dispatched",     "dispatch",      "wait_sub"],
    ["sub_done",       "wait_sub",      "review"],
    ["reviewed",       "review",        "done"],
]

# ── 知识库映射（LLM 状态需要加载的 MD） ──
# rules.md 包含拆分规则+铁规+踩坑记录
# examples.md 包含历史案例（自动积累）
knowledge = {
    "parse":         ["coordinator_rules.md"],
    "split_modules": ["coordinator_rules.md", "coordinator_examples.md"],
}

# ── hooks 映射（扁平格式，与 numerical/executor/combat 一致） ──
hooks = {
    "on_enter_parse":          "coordinator_hooks.on_enter_parse",
    "on_enter_split_modules":  "coordinator_hooks.on_enter_split_modules",
    "on_exit_user_confirm":    "coordinator_hooks.on_exit_user_confirm",
    "on_enter_dispatch":       "coordinator_hooks.on_enter_dispatch",
    "on_enter_review":         "coordinator_hooks.on_enter_review",
    "on_enter_done":           "coordinator_hooks.on_enter_done",
}
