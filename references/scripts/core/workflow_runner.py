# -*- coding: utf-8 -*-
"""
工作流启动/恢复脚本 — 所有 Skill 的统一入口。

功能：
    - 首次启动：构建工作流状态机，进入初始状态，保存状态
    - 恢复：从 task_state.json 加载上次的状态
    - 快速模式（--start-at）：跳过 L0，直接从 L1 开始
    - --check：仅做 preflight 校验，不启动状态机
    - --skill：指定 Skill（doc, excel, design）
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


# ── Preflight 启动检查 ──────────────────────────────

def preflight_check():
    """启动前校验项目完整性。

    检查所有核心脚本、workflow、hooks 文件和 Python 依赖是否存在。
    任何缺失都会打印具体项并返回 False，阻止状态机启动。
    """
    errors = []

    # 1. 核心脚本（新旧文件都检查，至少有一个存在即可）
    core_files = [
        'workflow_engine.py', 'machine.py', 'machine_hooks.py',
        'hook_utils.py', 'constants.py', 'table_reader.py',
        'knowledge_search.py', 'knowledge_index.py',
    ]
    for f in core_files:
        if not os.path.exists(os.path.join(CORE_DIR, f)):
            errors.append(f"[MISSING] core/{f}")

    # 2. Workflow + Hooks 文件
    workflow_checks = {
        'coordinator': ('coordinator_workflow.py', 'coordinator_hooks.py'),
        'combat':      ('combat_workflow.py',      'combat_hooks.py'),
        'numerical':   ('numerical_workflow.py',   'numerical_hooks.py'),
        'system':      ('system_workflow.py',      'system_hooks.py'),
        'executor':    ('executor_workflow.py',    'executor_hooks.py'),
        'qa':          ('qa_workflow.py',          None),
    }
    for agent, (wf, hooks) in workflow_checks.items():
        process_dir = os.path.join(AGENTS_DIR, f'{agent}_memory', 'process')
        if not os.path.exists(os.path.join(process_dir, wf)):
            errors.append(f"[MISSING] agents/{agent}_memory/process/{wf}")
        if hooks and not os.path.exists(os.path.join(process_dir, hooks)):
            errors.append(f"[MISSING] agents/{agent}_memory/process/{hooks}")

    # 3. Python 依赖
    try:
        import transitions
    except ImportError:
        errors.append("[MISSING] pip package 'transitions' (run: pip install transitions>=0.9)")

    # 结果
    if errors:
        print("=" * 50)
        print("  [ERR] Preflight FAILED")
        print("=" * 50)
        for e in errors:
            print(f"  {e}")
        print(f"\n  共 {len(errors)} 项缺失。请先运行 /init 或检查 git 仓库完整性。")
        print("=" * 50)
        return False

    return True


# ── 导入引擎 ────────────────────────────────────────

from workflow_engine import build_workflow

# Agent -> 知识库目录映射
KNOWLEDGE_MAP = {
    "L0": os.path.join(AGENTS_DIR, 'coordinator_memory', 'knowledge'),
    "L1.combat": os.path.join(AGENTS_DIR, 'combat_memory', 'knowledge'),
    "L1.numerical": os.path.join(AGENTS_DIR, 'numerical_memory', 'knowledge'),
    "L1.system": os.path.join(AGENTS_DIR, 'system_memory', 'knowledge'),
    "L2": os.path.join(AGENTS_DIR, 'executor_memory'),
}

# --start-at 参数 -> pytransitions 状态名映射
START_MAP = {
    "L1.combat": "design_combat",
    "L1.numerical": "design_numerical",
    "L1.system": "design_system",
    "L2": "executor",
}


def _state_to_layer(state_str):
    """从 pytransitions 状态名解析出层级 key"""
    if not state_str:
        return None
    if state_str.startswith('coordinator'):
        return "L0"
    elif state_str.startswith('design_combat') or state_str.startswith('docwork_combat') or state_str.startswith('excelwork_combat'):
        return "L1.combat"
    elif state_str.startswith('design_numerical') or state_str.startswith('docwork_numerical') or state_str.startswith('excelwork_numerical'):
        return "L1.numerical"
    elif state_str.startswith('design_system') or state_str.startswith('docwork_system'):
        return "L1.system"
    elif state_str.startswith('executor'):
        return "L2"
    elif state_str in ('deliver', 'completed'):
        return state_str
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
    # /design 的 L1
    elif state.startswith('design_combat'):
        return {"layer": layer, "agent": "战斗策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('design_numerical'):
        return {"layer": layer, "agent": "数值策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('design_system'):
        return {"layer": layer, "agent": "系统策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    # /doc 的 L1
    elif state.startswith('docwork_system'):
        return {"layer": layer, "agent": "系统策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('docwork_numerical'):
        return {"layer": layer, "agent": "数值策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('docwork_combat'):
        return {"layer": layer, "agent": "战斗策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('docwork_router'):
        return {"layer": "L1", "agent": "路由", "step": "router"}
    # /excel 的 L1
    elif state.startswith('excelwork_numerical'):
        return {"layer": layer, "agent": "数值策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('excelwork_combat'):
        return {"layer": layer, "agent": "战斗策划", "step": '_'.join(parts[2:]) if len(parts) > 2 else None}
    elif state.startswith('excelwork_router'):
        return {"layer": "L1", "agent": "路由", "step": "router"}
    # 其他
    elif state.startswith('executor'):
        return {"layer": layer, "agent": "执行策划", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state.startswith('pipeline'):
        return {"layer": "L3", "agent": "QA", "step": '_'.join(parts[1:]) if len(parts) > 1 else None}
    elif state == 'deliver':
        return {"layer": "deliver", "agent": "主策划", "step": "deliver"}
    elif state == 'completed':
        return {"layer": "completed", "agent": None, "step": None}
    else:
        return {"layer": state, "agent": None, "step": None}


def _invoke_current_hook(model):
    """根据当前状态，查找并调用对应的 on_enter hook。"""
    state = model.state
    if not state:
        return None

    hook_method = f"on_enter_{state}"
    fn = getattr(model, hook_method, None)

    if not (fn and callable(fn)):
        workflows = getattr(model, 'workflows', {})
        for wf_name, wf_mod in workflows.items():
            prefix = f"design_{wf_name}" if wf_name not in ('coordinator', 'executor', 'qa') else wf_name
            if state == prefix:
                initial = getattr(wf_mod, 'initial', None)
                if initial:
                    hook_method = f"on_enter_{prefix}_{initial}"
                    fn = getattr(model, hook_method, None)
                    if fn and callable(fn):
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


def _save_state(state_str, skill_name=None):
    """保存状态到 task_state.json"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = {"state": state_str}
    if skill_name:
        data["skill"] = skill_name
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def bootstrap(skill="design", start_at=None):
    """启动或恢复工作流

    Args:
        skill: Skill 名称（"design", "doc", "excel"）
        start_at: 可选，直接从指定层级开始（如 'L1.combat'），跳过 L0。
    """
    # 启动前校验
    if not preflight_check():
        return None

    model = build_workflow(skill)

    if start_at:
        # 快速模式
        if start_at not in START_MAP:
            print(f"  [ERR] 未知的目标状态 '{start_at}'")
            print(f"  可选值: {list(START_MAP.keys())}")
            return None
        target_state = START_MAP[start_at]
        model.machine.set_state(target_state, model)
        _save_state(model.state, skill)
        mode = f"快速模式（从 {start_at} 开始）"
    elif os.path.exists(STATE_FILE):
        # 恢复模式
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        saved_state = saved.get('state')
        if saved_state:
            model.machine.set_state(saved_state, model)
        mode = "恢复"
    else:
        # 首次启动
        _save_state(model.state, skill)
        mode = "首次启动"

    # 获取当前状态信息
    agent_info = get_current_agent_info(model)
    knowledge = get_knowledge_files(model.state)

    # 自动调用当前步骤的 on_enter hook
    hook_result = _invoke_current_hook(model)

    # 输出状态报告
    skill_label = f"[{skill}] " if skill != "design" else ""
    print("=" * 50)
    print(f"{skill_label}Workflow {mode}")
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
        "skill": skill,
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
    parser = argparse.ArgumentParser(description='工作流启动/恢复脚本')
    parser.add_argument('--skill', type=str, default='excel',
                        help='Skill 名称: excel, doc, design (default: excel)')
    parser.add_argument('--start-at', type=str, default=None,
                        help='直接从指定层级开始，跳过 L0（如 L1.combat, L1.numerical）')
    parser.add_argument('--check', action='store_true',
                        help='仅做 preflight 检查，不启动状态机')
    args = parser.parse_args()

    if args.check:
        ok = preflight_check()
        if ok:
            print("  [OK] Preflight passed. All core files and dependencies are intact.")
        sys.exit(0 if ok else 1)
    else:
        bootstrap(skill=args.skill, start_at=args.start_at)
