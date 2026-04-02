# -*- coding: utf-8 -*-
"""
执行策划 Workflow 定义

5 个状态：
  execute       → 读上游 output.json
  align         → 读 Row6 全量字段 + 对比 + 列出待填字段
  fill          → LLM 链式参考查找 + 补值，不确定项标 uncertain
  fill_confirm  → 用户审核不确定项
  write         → 实时分配 ID + 同步引用 + 校验 + 写入增量 xlsx → L2完成
"""

# ── 基本信息 ──
name = "executor"
description = "执行策划：设计意图→完整数据行→写入增量 xlsx→交给 L3 QA"

# ── 初始状态 ──
initial = "execute"

# ── 状态列表 ──
states = [
    {"name": "execute",       "type": "script", "description": "读上游 output.json"},
    {"name": "align",         "type": "script", "description": "读 Row6 全量字段→对比→列出待填"},
    {"name": "fill",          "type": "llm",    "description": "LLM 链式参考查找 + 补值"},
    {"name": "fill_confirm",  "type": "pause",  "description": "用户审核不确定项"},
    {"name": "write",         "type": "script", "description": "分配 ID→同步引用→写入增量 xlsx→L2完成"},
]

# ── 状态转移 ──
transitions = [
    ["execute_done",  "execute",       "align"],
    ["align_done",    "align",         "fill"],
    ["fill_done",     "fill",          "fill_confirm"],
    ["confirm_done",  "fill_confirm",  "write"],
]

# ── 知识库映射 ──
knowledge = {
    "fill": ["executor_fill_rules.md", "executor_rules.md", "executor_design_patterns.md"],
    "write": ["id_relations.md"],
}

# ── 脚本映射 ──
hooks = {
    "on_enter_execute":       "executor_hooks.on_enter_execute",
    "on_enter_align":         "executor_hooks.on_enter_align",
    "on_enter_fill":          "executor_hooks.on_enter_fill",
    "on_enter_fill_confirm":  "executor_hooks.on_enter_fill_confirm",
    "on_enter_write":         "executor_hooks.on_enter_write",
}
