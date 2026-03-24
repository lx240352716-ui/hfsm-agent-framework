# -*- coding: utf-8 -*-
"""
主状态机 Hooks — 层间跳转的执行逻辑。

管理 coordinator → design → executor → pipeline 之间的衔接。
每个 Agent 有自己的 hooks（管内部状态），本文件管层与层之间。
"""

import json
import os


# ── 路径常量 ──

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')
COORDINATOR_DATA = os.path.join(AGENTS_DIR, 'coordinator_memory', 'data')
COMBAT_DATA = os.path.join(AGENTS_DIR, 'combat_memory', 'data')
NUMERICAL_DATA = os.path.join(AGENTS_DIR, 'numerical_memory', 'data')
EXECUTOR_DATA = os.path.join(AGENTS_DIR, 'executor_memory', 'data')


# ── on_enter: design ──

def on_enter_design(model):
    """
    coordinator → design 时调用。
    读 coordinator 的 output.json，把 dispatch 数据存到 model 上。
    """
    output_path = os.path.join(COORDINATOR_DATA, 'output.json')
    if not os.path.exists(output_path):
        return {"error": "coordinator output.json 不存在"}

    with open(output_path, 'r', encoding='utf-8') as f:
        output = json.load(f)

    dispatch = output.get('dispatch', {})

    # 存到 model 上，供 router 和 Guard 使用
    model.design_roles = list(dispatch.keys())
    model.design_dispatch = dispatch

    return {"roles": model.design_roles}


def on_enter_design_router(model):
    """
    进入 design_router 后自动调用。
    如果 design_dispatch 还没设置（on_enter_design 未生效），自己读 output.json。
    然后根据 dispatch 数据触发路由事件。
    """
    # 确保 dispatch 数据存在
    if not getattr(model, 'design_dispatch', None):
        output_path = os.path.join(COORDINATOR_DATA, 'output.json')
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                output = json.load(f)
            model.design_dispatch = output.get('dispatch', {})
            model.design_roles = list(model.design_dispatch.keys())

    dispatch = getattr(model, 'design_dispatch', {})

    if 'combat' in dispatch:
        model.route_to_combat()
    else:
        model.route_to_numerical()


# ── on_enter: executor ──

def on_enter_executor(model):
    """
    design → executor 时调用。
    读设计层的产出，确定要填哪些表。
    """
    # 读 combat 和 numerical 的产出
    design_outputs = {}

    for name, data_dir in [("combat", COMBAT_DATA), ("numerical", NUMERICAL_DATA)]:
        output_path = os.path.join(data_dir, 'output.json')
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                design_outputs[name] = json.load(f)

    model.design_outputs = design_outputs

    return {"design_outputs": list(design_outputs.keys())}


# ── on_enter: pipeline ──

def on_enter_pipeline(model):
    """
    executor → pipeline 时调用。
    准备 QA 检查清单。
    """
    # 读 executor 的 staging 产出
    staging_path = os.path.join(EXECUTOR_DATA, 'output.json')
    if os.path.exists(staging_path):
        with open(staging_path, 'r', encoding='utf-8') as f:
            model.staging_data = json.load(f)

    return {"ready": True}
