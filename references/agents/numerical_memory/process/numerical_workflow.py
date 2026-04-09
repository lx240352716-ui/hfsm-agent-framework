# -*- coding: utf-8 -*-
"""
数值策划 Workflow 定义

状态流程：match → split → confirm → locate → fill → output
"""

# ── 基本信息 ──
name = "numerical"
description = "数值策划：匹配案例 → 拆解模块 → 确认 → 定位表字段 → 填值 → 输出"

# ── 初始状态 ──
initial = "match"

# ── 状态列表 ──
states = [
    {"name": "match",   "type": "llm",   "description": "读上游需求，查 examples 找同类案例"},
    {"name": "split",   "type": "llm",   "description": "按系统知识拆解为独立模块"},
    {"name": "confirm", "type": "pause", "description": "用户确认模块拆分"},
    {"name": "locate",  "type": "llm",   "description": "查 table_directory 定位真实表名+字段，查参考数据过滤"},
    {"name": "fill",    "type": "pause", "description": "展示字段清单，用户填值"},
    {"name": "output",  "type": "llm",   "description": "组装标准 output.json 交给下游"},
]

# ── 状态转移 ──
transitions = [
    ["match_done",    "match",   "split"],
    ["split_done",    "split",   "confirm"],
    ["confirmed",     "confirm", "locate"],
    ["locate_done",   "locate",  "fill"],
    ["fill_done",     "fill",    "output"],
    ["retry_locate",  "fill",    "locate"],   # not_found → 回退 locate 重新搜索
]

# ── 知识库映射 ──
knowledge = {
    "match":  ["numerical_rules.md", "systems_index.md", "numerical_examples.md", "__manifest__"],
    "split":  ["numerical_rules.md", "requirement_structures.md"],    # + 动态加载 system_*.md
    "locate": ["table_directory.md", "numerical_rules.md", "requirement_structures.md", "__manifest__"],
    "output": ["numerical_rules.md"],
}

# ── 脚本映射 ──
hooks = {
    "on_enter_match":    "numerical_hooks.on_enter_match",
    "on_enter_split":    "numerical_hooks.on_enter_split",
    "on_exit_confirm":   "numerical_hooks.on_exit_confirm",
    "on_enter_locate":   "numerical_hooks.on_enter_locate",
    "on_exit_locate":    "numerical_hooks.on_exit_locate",
    "on_enter_fill":     "numerical_hooks.on_enter_fill",
    "on_enter_output":   "numerical_hooks.on_enter_output",
    "on_exit_output":    "numerical_hooks.on_exit_output",
}
