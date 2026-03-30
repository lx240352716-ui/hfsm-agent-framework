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

# 路径设置 — 从脚本自身位置推算
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REFERENCES_DIR = os.path.normpath(os.path.join(_THIS_DIR, '..', '..'))
SCRIPTS_DIR = os.path.join(REFERENCES_DIR, 'scripts')
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, 'output')
STATE_FILE = os.path.join(OUTPUT_DIR, 'task_state.json')

sys.path.insert(0, CORE_DIR)
from constants import AGENTS_DIR
from hfsm_registry import build_hfsm

# Agent → 知识库目录映射（key = model.state 的顶层前缀）
KNOWLEDGE_MAP = {
    "coordinator": os.path.join(AGENTS_DIR, 'coordinator_memory', 'knowledge'),
    "design_combat": os.path.join(AGENTS_DIR, 'combat_memory'),
    "design_numerical": os.path.join(AGENTS_DIR, 'numerical_memory'),
    "executor": os.path.join(AGENTS_DIR, 'executor_memory'),
    "pipeline": os.path.join(AGENTS_DIR, 'qa_memory'),
}


def get_knowledge_files(state_str):
    """根据当前状态返回应加载的知识库 MD 文件列表"""
    if not state_str:
        return []

    # 匹配最长前缀
    matched_dir = None
    for prefix in sorted(KNOWLEDGE_MAP.keys(), key=len, reverse=True):
        if state_str.startswith(prefix):
            matched_dir = KNOWLEDGE_MAP[prefix]
            break

    if not matched_dir or not os.path.exists(matched_dir):
        return []

    md_files = []
    for root_dir, _dirs, files in os.walk(matched_dir):
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root_dir, f))
    return md_files


def get_current_agent_info(root):
    """从 pytransitions 的 model.state 解析当前层级信息

    model.state 形如 'coordinator_parse' 或 'design_combat_match'
    """
    state = root.state
    if not state:
        return {"layer": None, "agent": None, "step": None}

    parts = state.split('_')

    if parts[0] == 'coordinator':
        return {
            "layer": "coordinator",
            "agent": "coordinator",
            "step": '_'.join(parts[1:]) if len(parts) > 1 else None,
        }
    elif parts[0] == 'design':
        if len(parts) >= 3:
            return {
                "layer": "design",
                "agent": parts[1],  # combat / numerical
                "step": '_'.join(parts[2:]),
            }
        elif len(parts) == 2:
            return {
                "layer": "design",
                "agent": parts[1],
                "step": None,
            }
        return {"layer": "design", "agent": None, "step": None}
    elif parts[0] == 'executor':
        return {
            "layer": "executor",
            "agent": "executor",
            "step": '_'.join(parts[1:]) if len(parts) > 1 else None,
        }
    elif parts[0] == 'pipeline':
        return {
            "layer": "pipeline",
            "agent": "qa",
            "step": '_'.join(parts[1:]) if len(parts) > 1 else None,
        }
    elif state == 'completed':
        return {"layer": "completed", "agent": None, "step": None}
    else:
        return {"layer": state, "agent": None, "step": None}


def _save_state(root):
    """保存当前状态到 JSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = {"state": root.state}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def bootstrap():
    """启动或恢复 HFSM"""
    root = build_hfsm()

    if os.path.exists(STATE_FILE):
        # ── 恢复模式 ──
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        saved_state = saved.get('state')
        if saved_state:
            root.machine.set_state(saved_state, root)
        mode = "恢复"
    else:
        # ── 首次启动（machine 已自动进入 initial 状态） ──
        _save_state(root)
        mode = "首次启动"

    # 获取当前状态信息
    agent_info = get_current_agent_info(root)
    state_str = root.state or ''
    knowledge = get_knowledge_files(state_str)

    # 输出状态报告
    report = {
        "mode": mode,
        "state": agent_info,
        "raw_state": root.state,
        "knowledge_files": [os.path.basename(f) for f in knowledge],
        "knowledge_paths": knowledge,
    }

    print("=" * 50)
    print(f"HFSM {mode}")
    print("=" * 50)
    print(f"  当前状态: {root.state}")
    print(f"  当前层级: {agent_info['layer']}")
    print(f"  当前 Agent: {agent_info.get('agent', '-')}")
    print(f"  当前步骤: {agent_info.get('step', '-')}")
    print(f"  知识库: {report['knowledge_files']}")
    print("=" * 50)

    return report


if __name__ == "__main__":
    bootstrap()

