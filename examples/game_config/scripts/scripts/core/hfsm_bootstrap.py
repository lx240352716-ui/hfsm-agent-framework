# -*- coding: utf-8 -*-
"""
HFSM 启动/恢复脚本 — 由 /design skill 调用。

功能：
    - 首次启动：构建 HFSM，进入 L0，保存状态
    - 恢复：从 task_state.json 加载上次的状态
    - 输出当前状态信息，供 LLM 读取
"""

import os
import sys
import json

# 路径设置
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts')
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, 'output')
STATE_FILE = os.path.join(OUTPUT_DIR, 'task_state.json')
AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')

sys.path.insert(0, CORE_DIR)
from hfsm_registry import build_hfsm

# Agent → 知识库目录映射
KNOWLEDGE_MAP = {
    "L0": os.path.join(AGENTS_DIR, 'coordinator_memory', 'knowledge'),
    "L1.combat": os.path.join(AGENTS_DIR, 'combat_memory'),
    "L1.numerical": os.path.join(AGENTS_DIR, 'numerical_memory'),
    "L2": os.path.join(AGENTS_DIR, 'executor_memory'),
}


def get_knowledge_files(state):
    """根据当前状态返回应加载的知识库 MD 文件列表"""
    knowledge_dir = KNOWLEDGE_MAP.get(state)
    if not knowledge_dir or not os.path.exists(knowledge_dir):
        return []

    md_files = []
    for f in os.listdir(knowledge_dir):
        if f.endswith('.md'):
            md_files.append(os.path.join(knowledge_dir, f))
    return md_files


def get_current_agent_info(root):
    """获取当前 Agent 的详细信息"""
    layer = root.current
    if layer is None:
        return {"layer": None, "agent": None, "step": None}

    info = {"layer": layer}

    # 获取子状态机的当前步骤
    if layer in root._children:
        child = root._children[layer]
        info["agent"] = child.name
        info["step"] = child.current

        # L1 有二级嵌套
        if child.current in child._children:
            grandchild = child._children[child.current]
            info["sub_agent"] = grandchild.name
            info["sub_step"] = grandchild.current

    return info


def bootstrap():
    """启动或恢复 HFSM"""
    root = build_hfsm()

    if os.path.exists(STATE_FILE):
        # ── 恢复模式 ──
        root.load(STATE_FILE)
        mode = "恢复"
    else:
        # ── 首次启动 ──
        root.start()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        root.save(STATE_FILE)
        mode = "首次启动"

    # 获取当前状态信息
    agent_info = get_current_agent_info(root)
    knowledge = get_knowledge_files(agent_info["layer"])

    # 输出状态报告
    report = {
        "mode": mode,
        "state": agent_info,
        "knowledge_files": [os.path.basename(f) for f in knowledge],
        "knowledge_paths": knowledge,
    }

    print("=" * 50)
    print(f"HFSM {mode}")
    print("=" * 50)
    print(f"  当前层级: {agent_info['layer']}")
    print(f"  当前 Agent: {agent_info.get('agent', '-')}")
    print(f"  当前步骤: {agent_info.get('step', '-')}")
    if agent_info.get('sub_agent'):
        print(f"  子 Agent: {agent_info['sub_agent']}")
        print(f"  子步骤: {agent_info['sub_step']}")
    print(f"  知识库: {report['knowledge_files']}")
    print("=" * 50)

    return report


if __name__ == "__main__":
    bootstrap()
