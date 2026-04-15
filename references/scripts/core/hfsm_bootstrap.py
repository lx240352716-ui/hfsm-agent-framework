# -*- coding: utf-8 -*-
"""
HFSM 启动/恢复脚本 — 由 /design 和 /quick skill 调用。

功能：
    - 首次启动：构建 HFSM，进入 L0，保存状态
    - 恢复：从 task_state.json 加载上次的状态
    - 快速模式（--start-at）：跳过 L0，直接从 L1 开始
    - 输出当前状态信息，供 LLM 读取
"""

import os
import sys
import json

# 路径设置
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
OUTPUT_DIR = os.path.join(SCRIPTS_DIR, 'output')
STATE_FILE = os.path.join(OUTPUT_DIR, 'task_state.json')
AGENTS_DIR = os.path.join(os.path.dirname(SCRIPTS_DIR), 'agents')

sys.path.insert(0, CORE_DIR)
from hfsm_registry import build_hfsm

# Agent → 知识库目录映射
KNOWLEDGE_MAP = {
    "L0": os.path.join(AGENTS_DIR, 'coordinator_memory', 'knowledge'),
    "L1.combat": os.path.join(AGENTS_DIR, 'combat_memory', 'knowledge'),
    "L1.numerical": os.path.join(AGENTS_DIR, 'numerical_memory', 'knowledge'),
    "L1.system": os.path.join(AGENTS_DIR, 'system_memory', 'knowledge'),
    "L2": os.path.join(AGENTS_DIR, 'executor_memory'),
}

# --start-at 参数 → pytransitions 状态名 映射
START_MAP = {
    "L1.combat": "design_combat",
    "L1.numerical": "design_numerical",
    "L1.system": "design_system",
    "L2": "executor",
}


def _state_to_layer(state_str):
    """从 pytransitions 状态名解析出层级 key（对应 KNOWLEDGE_MAP）"""
    if not state_str:
        return None
    if state_str.startswith('coordinator'):
        return "L0"
    elif state_str.startswith('design_combat'):
        return "L1.combat"
    elif state_str.startswith('design_numerical'):
        return "L1.numerical"
    elif state_str.startswith('design_system'):
        return "L1.system"
    elif state_str.startswith('executor'):
        return "L2"
    return None


def get_knowledge_files(state_str):
    """根据当前 pytransitions 状态返回应加载的知识库 MD 文件列表"""
    layer = _state_to_layer(state_str)
    knowledge_dir = KNOWLEDGE_MAP.get(layer)
    if not knowledge_dir or not os.path.exists(knowledge_dir):
        return []

    md_files = []
    for f in os.listdir(knowledge_dir):
        if f.endswith('.md'):
            md_files.append(os.path.join(knowledge_dir, f))
    return md_files


def get_current_agent_info(model):
    """获取当前 Agent 的详细信息"""
    state = model.state
    if not state:
        return {"layer": None, "agent": None, "step": None}

    layer = _state_to_layer(state)
    parts = state.split('_')

    if state.startswith('coordinator'):
        return {"layer": layer, "agent": "主策划", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state.startswith('design_combat'):
        return {"layer": layer, "agent": "战斗策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('design_numerical'):
        return {"layer": layer, "agent": "数值策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('design_system'):
        return {"layer": layer, "agent": "系统策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('executor'):
        return {"layer": layer, "agent": "执行策划", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state.startswith('pipeline'):
        return {"layer": "L3", "agent": "QA", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state == 'completed':
        return {"layer": "completed", "agent": None, "step": None}
    else:
        return {"layer": state, "agent": None, "step": None}


def _invoke_current_hook(model):
    """根据当前状态，查找并调用对应的 on_enter hook。

    pytransitions 的 set_state() 不触发回调，所以需要手动调用。
    hook 返回的 dict 包含 instruction/knowledge 供 LLM 使用。

    查找顺序：
        1. on_enter_<current_state>（精确匹配）
        2. on_enter_<current_state>_<initial>（父状态 → 初始子状态）

    Returns:
        dict or None: hook 的返回值，或 None（无 hook）
    """
    state = model.state
    if not state:
        return None

    # 尝试 1：精确匹配当前状态
    hook_method = f"on_enter_{state}"
    fn = getattr(model, hook_method, None)

    # 尝试 2：当前状态是父状态，查初始子状态
    if not (fn and callable(fn)):
        # 从 workflows 获取对应 agent 的 initial state
        workflows = getattr(model, 'workflows', {})
        for wf_name, wf_mod in workflows.items():
            prefix = f"design_{wf_name}" if wf_name not in ('coordinator', 'executor', 'qa') else wf_name
            if state == prefix:
                initial = getattr(wf_mod, 'initial', None)
                if initial:
                    hook_method = f"on_enter_{prefix}_{initial}"
                    fn = getattr(model, hook_method, None)
                    if fn and callable(fn):
                        # 同时更新 task_state.json 为精确子状态
                        precise_state = f"{prefix}_{initial}"
                        model.machine.set_state(precise_state, model)
                        _save_state(model.state)
                        break

    if fn and callable(fn):
        try:
            result = fn()
            return result if isinstance(result, dict) else None
        except Exception as e:
            print(f"  [ERR] hook {hook_method} failed: {e}")
            return {"error": str(e)}
    return None


def _save_state(state_str):
    """保存状态到 task_state.json"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"state": state_str}, f, ensure_ascii=False, indent=2)


def bootstrap(start_at=None):
    """启动或恢复 HFSM

    Args:
        start_at: 可选，直接从指定层级开始（如 'L1.combat'），跳过 L0。
                  用于 S_Express 快速模式。
    """
    model = build_hfsm()

    if start_at:
        # ── 快速模式：跳到指定层级 ──
        if start_at not in START_MAP:
            print(f"错误：未知的目标状态 '{start_at}'")
            print(f"可选值：{list(START_MAP.keys())}")
            return None
        target_state = START_MAP[start_at]
        model.machine.set_state(target_state, model)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"state": model.state}, f, ensure_ascii=False, indent=2)
        mode = f"快速模式（从 {start_at} 开始）"
    elif os.path.exists(STATE_FILE):
        # ── 恢复模式 ──
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        saved_state = saved.get('state')
        if saved_state:
            model.machine.set_state(saved_state, model)
        mode = "恢复"
    else:
        # ── 首次启动（自动进入 coordinator 初始状态） ──
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"state": model.state}, f, ensure_ascii=False, indent=2)
        mode = "首次启动"

    # 获取当前状态信息
    agent_info = get_current_agent_info(model)
    knowledge = get_knowledge_files(model.state)

    # 自动调用当前步骤的 on_enter hook
    hook_result = _invoke_current_hook(model)

    # 输出状态报告
    print("=" * 50)
    print(f"HFSM {mode}")
    print("=" * 50)
    print(f"  当前状态: {model.state}")
    print(f"  当前层级: {agent_info['layer']}")
    print(f"  当前 Agent: {agent_info.get('agent', '-')}")
    print(f"  当前步骤: {agent_info.get('step', '-')}")
    print(f"  知识库: {[os.path.basename(f) for f in knowledge]}")
    if hook_result:
        if hook_result.get('instruction'):
            print(f"\n  [instruction]")
            for line in hook_result['instruction'].split('\n'):
                print(f"  {line}")
        if hook_result.get('trigger'):
            print(f"\n  [trigger] {hook_result['trigger']}")
    else:
        print(f"\n  [WARN] 未找到当前步骤的 hook，LLM 需自行判断任务")
    print("=" * 50)

    result = {
        "mode": mode,
        "state": agent_info,
        "raw_state": model.state,
        "knowledge_files": [os.path.basename(f) for f in knowledge],
        "knowledge_paths": knowledge,
    }
    if hook_result:
        result["hook_result"] = hook_result
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='HFSM 启动/恢复脚本')
    parser.add_argument('--start-at', type=str, default=None,
                        help='直接从指定层级开始，跳过 L0（如 L1.combat, L1.numerical）')
    args = parser.parse_args()
    bootstrap(start_at=args.start_at)
