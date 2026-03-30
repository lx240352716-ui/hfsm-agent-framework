# -*- coding: utf-8 -*-
"""角色间交接数据 — 通用读写/校验机制（业务无关）"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from file_ops import get_task_output_dir


def save_handoff(task_name, from_role, data):
    """角色输出结构化交接数据

    Args:
        task_name: 任务名
        from_role: 来源角色 (combat/numerical/coordinator/senior)
        data: 交接数据字典，格式: {"tables": {...}, "design_check": {...}, ...}
              tables 为必需，其余字段透传到 JSON
    Returns:
        str: JSON文件路径
    """
    task_dir = get_task_output_dir(task_name)
    filepath = os.path.join(task_dir, f"handoff_{from_role}.json")

    envelope = {
        "task": task_name,
        "from": from_role,
        "to": "executor",
        "timestamp": datetime.now().isoformat(),
    }
    for k, v in data.items():
        envelope[k] = v

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)

    print(f"  [HANDOFF] {from_role} → {filepath}")
    return filepath


def load_handoff(task_name, from_role):
    """读取交接数据

    Args:
        task_name: 任务名
        from_role: 来源角色
    Returns:
        dict: 交接数据，None=文件不存在
    """
    task_dir = get_task_output_dir(task_name)
    filepath = os.path.join(task_dir, f"handoff_{from_role}.json")

    if not os.path.exists(filepath):
        print(f"  [ERROR] 交接文件不存在: {filepath}")
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"  [LOAD] {from_role} 交接数据: {len(data.get('tables', {}))} 张表")
    return data


def validate_handoff(task_name, from_role):
    """校验交接数据格式（通用，不含业务逻辑）

    Returns:
        list: 错误列表，空=全部通过
    """
    data = load_handoff(task_name, from_role)
    if data is None:
        return ["交接文件不存在"]

    errors = []

    for field in ["task", "from", "to", "tables"]:
        if field not in data:
            errors.append(f"缺少必要字段: {field}")

    tables = data.get("tables", {})
    if not tables:
        errors.append("tables为空，没有交接数据")

    for table_name, rows in tables.items():
        if not isinstance(rows, list):
            errors.append(f"表{table_name}的值不是列表")
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"表{table_name}第{i}行不是字典")

    if errors:
        print(f"  [VALIDATE FAIL] {len(errors)} 个错误")
    else:
        print(f"  [VALIDATE OK] {from_role} 交接数据格式正确")

    return errors
