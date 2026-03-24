# -*- coding: utf-8 -*-
"""
HFSM Agent Framework

分层状态机 + Hook 驱动的多 Agent 框架。
核心设计：LLM 会出错，工程侧必须兜底。
"""

from .machine import State, Transition, Machine

__version__ = "0.1.0"
__all__ = ["State", "Transition", "Machine"]
