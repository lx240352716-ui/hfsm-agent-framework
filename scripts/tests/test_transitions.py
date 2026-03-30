# -*- coding: utf-8 -*-
"""校验所有 transitions.json 格式合法性 + 目标 Agent 存在性"""

import json
import os
import sys

BASE_DIR = REFERENCES_DIR

# 所有 transitions.json 文件路径
TRANSITION_FILES = {
    'coordinator': os.path.join(BASE_DIR, 'agents', 'coordinator_memory', 'transitions.json'),
    'combat':      os.path.join(BASE_DIR, 'agents', 'combat_memory', 'combat_transitions.json'),
    'numerical':   os.path.join(BASE_DIR, 'agents', 'numerical_memory', 'numerical_transitions.json'),
    'executor':    os.path.join(BASE_DIR, 'agents', 'executor_memory', 'executor_transitions.json'),
    'l3':          os.path.join(BASE_DIR, 'scripts', 'configs', 'l3_transitions.json'),
}

# 合法的 Agent 标识（transitions.json 中 target/source 的合法值）
VALID_AGENTS = {'coordinator', 'combat', 'numerical', 'executor', 'l3_qa', 'l3_merge', 'l3_automation'}

# 合法的层级
VALID_LAYERS = {'L0', 'L1', 'L2', 'L3'}


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_file_exists(agent_name, path):
    """检查文件是否存在"""
    if not os.path.exists(path):
        return [f'[{agent_name}] 文件不存在: {path}']
    return []


def check_required_fields(agent_name, data, required_fields):
    """检查必填字段"""
    errors = []
    for field in required_fields:
        if field not in data:
            errors.append(f'[{agent_name}] 缺少必填字段: {field}')
    return errors


def check_transition_targets(agent_name, data):
    """检查所有 target/source 引用的 Agent 是否合法"""
    errors = []

    # 检查 can_handoff_to
    for item in data.get('can_handoff_to', []):
        target = item.get('target', '')
        if target not in VALID_AGENTS:
            errors.append(f'[{agent_name}] can_handoff_to 中目标 "{target}" 不在合法 Agent 列表中')
        if 'condition' not in item:
            errors.append(f'[{agent_name}] can_handoff_to → {target} 缺少 condition 字段')

    # 检查 can_escalate_to
    for item in data.get('can_escalate_to', []):
        target = item.get('target', '')
        if target not in VALID_AGENTS:
            errors.append(f'[{agent_name}] can_escalate_to 中目标 "{target}" 不在合法 Agent 列表中')

    # 检查 can_receive_rejection_from / can_receive_escalation_from
    for key in ['can_receive_rejection_from', 'can_receive_escalation_from']:
        for item in data.get(key, []):
            source = item.get('source', '')
            if source not in VALID_AGENTS:
                errors.append(f'[{agent_name}] {key} 中来源 "{source}" 不在合法 Agent 列表中')
            if 'payload' not in item:
                errors.append(f'[{agent_name}] {key} → {source} 缺少 payload 字段')

    # 检查 can_reject_to
    for item in data.get('can_reject_to', []):
        target = item.get('target', '')
        if target not in VALID_AGENTS:
            errors.append(f'[{agent_name}] can_reject_to 中目标 "{target}" 不在合法 Agent 列表中')

    return errors


def check_layer_valid(agent_name, data):
    """检查层级是否合法"""
    layer = data.get('layer', '')
    if layer and layer not in VALID_LAYERS:
        return [f'[{agent_name}] 层级 "{layer}" 不合法，应为 {VALID_LAYERS}']
    return []


def check_l3_pipeline(data):
    """检查 L3 的 pipeline 格式"""
    errors = []
    pipeline = data.get('pipeline', [])

    if not pipeline:
        errors.append('[l3] pipeline 为空')
        return errors

    for i, step in enumerate(pipeline):
        if 'step' not in step:
            errors.append(f'[l3] pipeline[{i}] 缺少 step 字段')
        if 'script' not in step:
            errors.append(f'[l3] pipeline[{i}] 缺少 script 字段')
        if 'on_pass' not in step:
            errors.append(f'[l3] pipeline[{i}] 缺少 on_pass 字段')
        if 'on_fail' not in step:
            errors.append(f'[l3] pipeline[{i}] 缺少 on_fail 字段')

    return errors


def run_all_checks():
    """运行全部校验"""
    total_errors = []
    total_pass = 0

    print('=' * 60)
    print('Transitions.json 校验报告')
    print('=' * 60)

    for agent_name, path in TRANSITION_FILES.items():
        print(f'\n--- {agent_name} ---')

        # 1. 文件存在性
        errs = check_file_exists(agent_name, path)
        if errs:
            total_errors.extend(errs)
            print(f'  ❌ 文件不存在')
            continue

        # 2. JSON 解析
        try:
            data = load_json(path)
        except json.JSONDecodeError as e:
            total_errors.append(f'[{agent_name}] JSON 解析失败: {e}')
            print(f'  ❌ JSON 解析失败')
            continue

        # 3. L3 特殊处理（pipeline 格式）
        if agent_name == 'l3':
            errs = check_l3_pipeline(data)
            total_errors.extend(errs)
            if not errs:
                total_pass += 1
                print(f'  ✅ pipeline 格式合法 ({len(data.get("pipeline", []))} 个步骤)')
            else:
                for e in errs:
                    print(f'  ❌ {e}')
            continue

        # 4. 常规 Agent 校验
        agent_errors = []

        # 必填字段
        agent_errors.extend(check_required_fields(agent_name, data, ['agent', 'layer']))

        # 层级合法性
        agent_errors.extend(check_layer_valid(agent_name, data))

        # 目标引用合法性
        agent_errors.extend(check_transition_targets(agent_name, data))

        total_errors.extend(agent_errors)

        if not agent_errors:
            total_pass += 1
            handoff_count = len(data.get('can_handoff_to', []))
            escalate_count = len(data.get('can_escalate_to', []))
            reject_count = len(data.get('can_reject_to', []) + data.get('can_receive_rejection_from', []) + data.get('can_receive_escalation_from', []))
            print(f'  ✅ 格式合法 (handoff:{handoff_count}, escalate:{escalate_count}, reject/receive:{reject_count})')
        else:
            for e in agent_errors:
                print(f'  ❌ {e}')

    # 汇总
    print(f'\n{"=" * 60}')
    total = len(TRANSITION_FILES)
    print(f'结果: {total_pass}/{total} 通过, {len(total_errors)} 个错误')
    print(f'{"=" * 60}')

    return total_errors


if __name__ == '__main__':
    errors = run_all_checks()
    sys.exit(1 if errors else 0)
