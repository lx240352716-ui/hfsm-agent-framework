# -*- coding: utf-8 -*-
"""
demo_agent Workflow Definition
"""

name = "demo_agent"
description = "Auto-generated agent"

initial = "start"

states = [
    {"name": "start", "type": "script", "description": "Initial state"},
    {"name": "process", "type": "llm", "description": "Processing state"},
    {"name": "done", "type": "script", "description": "Done state"},
]

transitions = [
    ["started", "start", "process"],
    ["processed", "process", "done"],
]

hooks = {
    "on_enter_start": "demo_agent_hooks.on_enter_start",
    "on_enter_process": "demo_agent_hooks.on_enter_process",
    "on_enter_done": "demo_agent_hooks.on_enter_done",
}
