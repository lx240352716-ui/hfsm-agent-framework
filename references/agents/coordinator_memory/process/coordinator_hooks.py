# -*- coding: utf-8 -*-
"""
主策划 Hooks — 每个状态的具体执行逻辑。

由状态机的 on_enter / on_exit 回调触发。
workflow.py 管"什么状态、什么顺序"，本文件管"每个状态做什么"。

数据传递方式：LLM 写文件 → hooks 从文件读。
"""

import json
import os
import sys
from datetime import datetime


# ── 路径常量 ──

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'references', 'scripts', 'core'
))

from constants import REFERENCES_DIR, AGENTS_DIR, OUTPUT_DIR, agent_paths
from hook_utils import load_md_batch, init_pending, append_pending

_p = agent_paths('coordinator_memory')
AGENT_DIR = _p['agent_dir']
KNOWLEDGE_DIR = _p['knowledge_dir']
DATA_DIR = _p['data_dir']


# ── on_enter: parse ──

def on_enter_parse():
    """
    进入 parse 状态时调用。
    加载 coordinator_rules.md，返回 LLM 上下文。

    Returns:
        dict: {"knowledge": [...], "instruction": str}
    """
    knowledge = load_md_batch(KNOWLEDGE_DIR, ['coordinator_rules.md'])

    # 初始化 pending（覆盖写，清除上一次残留）
    init_pending(DATA_DIR)

    return {
        "knowledge": knowledge,
        "instruction": (
            "你现在是主策划。请阅读知识库，然后理解用户的需求：\n"
            "1. 判断需求类型（新角色/被动技能/UR装备/新阵法/纯数值调整）\n"
            "2. 用一句话总结需求"
        ),
    }


# ── on_enter: split_modules ──

def on_enter_split_modules():
    """
    进入 split_modules 状态时调用。
    加载 rules + examples，返回 LLM 上下文。

    Returns:
        dict: {"knowledge": [...], "instruction": str}
    """
    knowledge = load_md_batch(KNOWLEDGE_DIR, [
        'coordinator_rules.md',
        'coordinator_examples.md',
    ])

    return {
        "knowledge": knowledge,
        "instruction": (
            "根据知识库的拆分模板和历史案例，将需求拆分为模块：\n"
            "1. 列出每个模块名称\n"
            "2. 标注由谁负责（系统策划 / 战斗策划 / 数值策划）\n"
            "3. 将清单展示给用户确认\n"
            "注意：\n"
            "- 新系统/新功能优先派给系统策划\n"
            "- 系统策划会自行委托数值/战斗部分，不需要重复分配\n"
            "- 纯数值/纯战斗需求可直接分给对应策划\n"
            "- 不要分配给执行策划，执行策划由上游产出自动驱动。"
        ),
    }


# ── on_exit: user_confirm ──

def on_exit_user_confirm():
    """
    用户确认后调用。
    从 data/confirmed.json 读取 LLM 写入的确认数据，追加到 examples.md。

    前置条件：LLM 已将确认数据写入 data/confirmed.json
    格式：{"requirement": "...", "requirement_type": "...", "modules": {"combat": [...], ...}}
    """
    confirmed_path = os.path.join(DATA_DIR, 'confirmed.json')
    if not os.path.exists(confirmed_path):
        return {"error": "confirmed.json 不存在，LLM 需要先写入确认数据"}

    with open(confirmed_path, 'r', encoding='utf-8') as f:
        confirmed_data = json.load(f)

    # 格式化新案例
    now = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n\n### {confirmed_data.get('requirement', '未命名需求')} ({now})\n\n"
    entry += f"- 需求类型: {confirmed_data.get('requirement_type', '未知')}\n"
    entry += "- 模块分配:\n"

    modules = confirmed_data.get('modules', {})
    for role, module_list in modules.items():
        entry += f"  - {role}: {', '.join(module_list)}\n"

    # 追加到 pending（不直接写 examples.md）
    append_pending(DATA_DIR, "coordinator_examples.md", entry)

    return {"saved_to": "pending_examples.json", "entry": entry.strip()}


# ── on_enter: dispatch ──

def on_enter_dispatch():
    """
    进入 dispatch 状态时调用。
    从 data/confirmed.json 读取确认数据，生成 output.json 给下游 Agent。

    前置条件：data/confirmed.json 已存在
    产出：data/output.json
    """
    confirmed_path = os.path.join(DATA_DIR, 'confirmed.json')
    if not os.path.exists(confirmed_path):
        return {"error": "confirmed.json 不存在"}

    with open(confirmed_path, 'r', encoding='utf-8') as f:
        confirmed_data = json.load(f)

    modules = confirmed_data.get('modules', {})
    requirement = confirmed_data.get('requirement', '')

    # 构建输出：每个角色收到需求描述 + 模块列表
    output = {
        "_schema": "coordinator_output",
        "task_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "requirement": requirement,
        "requirement_type": confirmed_data.get('requirement_type', ''),
        "dispatch": {}
    }

    for role, module_list in modules.items():
        output["dispatch"][role] = {
            "requirement": requirement,
            "modules": module_list,
        }

    # 写入 output.json
    output_path = os.path.join(DATA_DIR, 'output.json')
    with open(output_path, 'w', encoding='utf-8') as out_f:
        json.dump(output, out_f, ensure_ascii=False, indent=2)

    return {
        "dispatch": output["dispatch"],
        "output_file": output_path,
    }


# ── on_enter: review ──

def on_enter_review():
    """
    回顾任务结果 + 归档案例 + 异常检测。
    读 l3_done.json + lineage_trace.json，生成回顾报告。
    """
    import glob

    QA_DIR = agent_paths('qa_memory')['agent_dir']
    # OUTPUT_DIR 已从 constants 导入

    # ── 1. 读取 L3 结果 ──
    l3_done_path = os.path.join(QA_DIR, 'l3_done.json')
    l3_done = {}
    if os.path.exists(l3_done_path):
        with open(l3_done_path, 'r', encoding='utf-8') as f:
            l3_done = json.load(f)

    task_name = l3_done.get('task_name', '')
    lineage_path = os.path.join(OUTPUT_DIR, task_name, 'lineage_trace.json')
    lineage = {}
    if os.path.exists(lineage_path):
        with open(lineage_path, 'r', encoding='utf-8') as f:
            lineage = json.load(f)

    if not l3_done:
        return {"status": "SKIP", "reason": "l3_done.json not found"}

    # ── 2. 生成回顾报告 ──
    requirement = l3_done.get('requirement', '未知需求')
    qa_status = l3_done.get('qa', 'unknown')
    merge_info = l3_done.get('merge', {})
    allocated_ids = l3_done.get('allocated_ids', {})
    id_replacements = lineage.get('id_replacements', {})

    report_lines = [
        f"## 任务回顾 — {requirement}",
        f"",
        f"**时间**: {l3_done.get('timestamp', '?')}",
        f"**QA**: {'[OK] 通过' if qa_status == 'pass' else '[ERR] 未通过'}",
        f"**状态**: {l3_done.get('status', '?')}",
        f"",
        f"### 变更摘要",
        f"",
        f"| 表 | 行数 | 新 ID | 参考 ID |",
        f"|---|---|---|---|",
    ]

    for table_name, merge in merge_info.items():
        rows = merge.get('rows_merged', 0)
        ids = allocated_ids.get(table_name, {})
        new_id = ids.get('new_id', '?')
        old_id = ids.get('old_id', '?')
        if isinstance(new_id, list):
            new_id = ', '.join(str(i) for i in new_id)
        if isinstance(old_id, list):
            old_id = ', '.join(str(i) for i in old_id)
        report_lines.append(f"| {table_name} | {rows} | {new_id} | {old_id} |")

    if id_replacements:
        report_lines.append(f"")
        report_lines.append(f"### ID 替换映射")
        for old, new in id_replacements.items():
            report_lines.append(f"- {old} → {new}")

    # ── 3. 异常检测 ──
    anomalies = []
    tables_data = lineage.get('tables', {})

    # 检查跨表引用完整性（Item.params 是否包含所有 DropGroup ID）
    if 'Item' in tables_data and '_DropGroup' in tables_data:
        item_rows = tables_data['Item'].get('data', [])
        dg_rows = tables_data['_DropGroup'].get('data', [])
        dg_ids = [str(r.get('groupId', '')) for r in dg_rows]
        for item_row in item_rows:
            params = str(item_row.get('params', ''))
            missing = [gid for gid in dg_ids if gid not in params]
            if missing and len(dg_ids) > 1:
                anomalies.append(
                    f"[WARN] Item.params={params} 未包含所有 _DropGroup ID: 缺 {', '.join(missing)}"
                )

    # 检查名字是否仍为参考行原名
    for old_id, new_id in id_replacements.items():
        for tbl, tbl_data in tables_data.items():
            for row in tbl_data.get('data', []):
                name = row.get('名字', '') or row.get('nameIndex', '')
                if name and old_id in name and str(new_id) != str(old_id):
                    pass  # 名字包含旧ID不一定是问题

    if anomalies:
        report_lines.append(f"")
        report_lines.append(f"### [WARN] 异常检测")
        for a in anomalies:
            report_lines.append(f"- {a}")

    report = '\n'.join(report_lines)

    # ── 4. 从各 Agent 的 pending 提交案例 ──
    committed = []
    for agent_name in ['coordinator_memory', 'numerical_memory', 'combat_memory', 'system_memory']:
        ap = agent_paths(agent_name)
        pending_path = os.path.join(ap['data_dir'], 'pending_examples.json')
        if not os.path.exists(pending_path):
            continue
        with open(pending_path, 'r', encoding='utf-8') as f:
            pending = json.load(f)
        for entry in pending.get('entries', []):
            target = os.path.join(ap['knowledge_dir'], entry['target'])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'a', encoding='utf-8') as f:
                f.write(entry['content'])
            committed.append(f"{agent_name}/{entry['target']}")

    # ── 5. 保存回顾报告 ──
    review_path = os.path.join(DATA_DIR, 'review_report.md')
    with open(review_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return {
        "status": "OK",
        "report": report,
        "anomalies": anomalies,
        "committed": committed,
    }

# ── on_enter: done ──

def on_enter_done():
    """
    任务完成：清理所有 agent 的中间数据 JSON 文件。
    保留 output/ 目录和已归档案例。
    """
    import glob

    # 各 agent 需要清理的目录
    cleanup_dirs = [
        agent_paths('numerical_memory')['data_dir'],
        agent_paths('system_memory')['data_dir'],
        agent_paths('executor_memory')['data_dir'],
        agent_paths('coordinator_memory')['data_dir'],
    ]
    # QA 的 JSON 在根目录
    qa_dir = agent_paths('qa_memory')['agent_dir']

    deleted = []

    for d in cleanup_dirs:
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, '*.json')):
            try:
                os.remove(f)
                deleted.append(os.path.relpath(f, AGENTS_DIR))
            except Exception:
                pass

    # QA 根目录的 JSON
    for f in glob.glob(os.path.join(qa_dir, '*.json')):
        try:
            os.remove(f)
            deleted.append(os.path.relpath(f, AGENTS_DIR))
        except Exception:
            pass

    return {
        "status": "TASK_COMPLETE",
        "deleted": deleted,
        "message": "任务完成。所有中间数据已清理，案例已归档。建议开新对话处理下一个需求。",
    }

