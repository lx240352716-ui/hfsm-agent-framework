# -*- coding: utf-8 -*-
"""
系统策划 Workflow 定义

状态流程：parse → draft → delegate → wait_sub → assemble → wireframe → review → export
"""

# -- 基本信息 --
name = "system"
description = "系统策划：理解需求 → 写文档 → 委托补充 → 整合 → 出图 → 导出"

# -- 初始状态 --
initial = "parse"

# -- 状态列表 --
states = [
    {"name": "parse",     "type": "llm",    "description": "读 wiki + manifest，理解需求上下文"},
    {"name": "draft",     "type": "llm",    "description": "按模板写策划文档框架"},
    {"name": "delegate",  "type": "script", "description": "检测是否需要 combat/numerical 补充"},
    {"name": "wait_sub",  "type": "pause",  "description": "等 combat/numerical 完成"},
    {"name": "assemble",  "type": "llm",    "description": "整合所有内容为完整文档"},
    {"name": "wireframe", "type": "script", "description": "提取界面章节 -> 调 Stitch 生成 UI"},
    {"name": "review",    "type": "pause",  "description": "用户确认"},
    {"name": "export",    "type": "script", "description": "导出 docx + 复制图片到 output/"},
]

# -- 状态转移 --
transitions = [
    ["parsed",      "parse",     "draft"],
    ["drafted",     "draft",     "delegate"],
    ["need_sub",    "delegate",  "wait_sub"],     # 需要其他 L1
    ["no_sub",      "delegate",  "assemble"],     # 不需要，直接整合
    ["sub_done",    "wait_sub",  "assemble"],
    ["assembled",   "assemble",  "wireframe"],
    ["wireframed",  "wireframe", "review"],
    ["approved",    "review",    "export"],
    ["rejected",    "review",    "draft"],         # 打回修改
]

# -- 知识库映射 --
knowledge = {
    "parse":    ["system_rules.md", "__manifest__"],
    "draft":    ["system_rules.md", "system_examples.md", "__manifest__"],
    "assemble": ["system_rules.md"],
}

# -- hooks 映射 --
hooks = {
    "on_enter_parse":     "system_hooks.on_enter_parse",
    "on_enter_draft":     "system_hooks.on_enter_draft",
    "on_enter_delegate":  "system_hooks.on_enter_delegate",
    "on_enter_assemble":  "system_hooks.on_enter_assemble",
    "on_enter_wireframe": "system_hooks.on_enter_wireframe",
    "on_enter_export":    "system_hooks.on_enter_export",
}
