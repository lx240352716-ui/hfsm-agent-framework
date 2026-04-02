# -*- coding: utf-8 -*-
"""
L3 QA Agent — Workflow 定义

3 个状态：
  qa    → 自动校验（ID/外键/白名单/格式），通过→merge，不通过→打回L2
  merge → COM Excel 写入源表 + 刷新索引
  done  → 输出最终结果 + 变更日志
"""

# ── 基本信息 ──
name = "qa"
description = "L3 QA Agent：校验→合并→完成（全自动，不通过才上报）"

# ── 初始状态 ──
initial = "qa"

# ── 状态列表 ──
states = [
    {"name": "qa",    "type": "script", "description": "自动校验：ID+外键+白名单+格式"},
    {"name": "merge", "type": "script", "description": "COM Excel 写入源表+刷新索引"},
    {"name": "done",  "type": "script", "description": "输出最终结果+变更日志"},
]

# ── 状态转移 ──
transitions = [
    ["qa_passed",  "qa",    "merge"],
    ["merge_done", "merge", "done"],
]

# ── 脚本映射 ──
hooks = {
    "on_enter_qa":    "qa_hooks.on_enter_qa",
    "on_enter_merge": "qa_hooks.on_enter_merge",
    "on_enter_done":  "qa_hooks.on_enter_done",
}
