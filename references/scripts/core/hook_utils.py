# -*- coding: utf-8 -*-
"""
Hook 公共工具函数。

所有 Agent 的 hooks 共用的 JSON/MD 读写 + pending 操作。
各 hooks 通过 `from hook_utils import ...` 引用，禁止重复定义。
"""

import os
import json


def load_json(filepath):
    """加载 JSON 文件，不存在返回 None"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_json(filepath, data):
    """保存 JSON 文件（auto makedirs, indent=2, ensure_ascii=False）"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_md(knowledge_dir, filename):
    """加载单个 MD 文件。

    查找顺序：knowledge_dir/{filename} → knowledge_dir/../{filename}（兜底）。
    返回 {"file": filename, "content": text}。
    """
    path = os.path.join(knowledge_dir, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return {"file": filename, "content": f.read()}
    # 兜底：上级目录（executor 迁移期兼容）
    fallback = os.path.join(os.path.dirname(knowledge_dir), filename)
    if os.path.exists(fallback):
        with open(fallback, 'r', encoding='utf-8') as f:
            return {"file": filename, "content": f.read()}
    return {"file": filename, "content": "（文件不存在）"}


def load_md_batch(knowledge_dir, filenames):
    """批量加载 MD 文件（跳过不存在的）。

    返回 [{"file": name, "content": text}, ...]
    """
    result = []
    for name in filenames:
        item = load_md(knowledge_dir, name)
        if item["content"] != "（文件不存在）":
            result.append(item)
    return result


def init_pending(data_dir, task_id='', requirement=''):
    """覆盖写 pending_examples.json（初始化，清除上一次残留）"""
    os.makedirs(data_dir, exist_ok=True)
    save_json(os.path.join(data_dir, 'pending_examples.json'), {
        "task_id": task_id,
        "requirement": requirement,
        "entries": []
    })


def append_pending(data_dir, target, content):
    """追加一条 entry 到 pending_examples.json。

    Args:
        data_dir: Agent 的 data/ 目录
        target: 目标文件相对于 knowledge/ 的路径，如 "numerical_examples.md"
        content: 要追加的文本内容
    """
    pending_path = os.path.join(data_dir, 'pending_examples.json')
    pending = load_json(pending_path) or {"entries": []}
    if "entries" not in pending:
        pending["entries"] = []
    pending["entries"].append({
        "target": target,
        "content": content
    })
    save_json(pending_path, pending)


def commit_pending(agent_dir):
    """从 pending_examples.json 提交所有条目到 knowledge/ 目标文件。

    提交后清空 pending。供 L0 review 和轻量 Skill 共用。

    Args:
        agent_dir: Agent 的根目录（如 agents/combat_memory/）
    Returns:
        list[str]: 已提交的目标文件列表
    """
    data_dir = os.path.join(agent_dir, 'data')
    knowledge_dir = os.path.join(agent_dir, 'knowledge')
    pending_path = os.path.join(data_dir, 'pending_examples.json')

    if not os.path.exists(pending_path):
        return []

    pending = load_json(pending_path)
    if not pending or not pending.get('entries'):
        return []

    committed = []
    for entry in pending['entries']:
        target = os.path.join(knowledge_dir, entry['target'])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'a', encoding='utf-8') as f:
            f.write(entry['content'])
        committed.append(entry['target'])

    # 清空 pending
    save_json(pending_path, {
        "task_id": pending.get("task_id", ""),
        "requirement": pending.get("requirement", ""),
        "entries": []
    })

    return committed


# ── 字段上下文公共入口 ──

def prepare_field_context(table_names):
    """为 LLM 准备标准化的字段上下文（中间层公共接口）。

    所有 hook 统一调此函数获取字段映射，禁止自行拼装。

    Args:
        table_names: list[str] — 表名列表（如 ['_Buff', 'FightBuff']）
    Returns:
        dict:
            field_maps:   {表名: {en, cn_en, en_cn, en_type, col_map}} 或 {error}
            instruction:  str — 统一的字段使用约束提示
    """
    import sys
    # 确保 table_reader 可导入
    _core = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    if _core not in sys.path:
        sys.path.insert(0, _core)
    from table_reader import get_columns

    field_maps = {}
    for tbl in table_names:
        try:
            col_info = get_columns(tbl)
            field_maps[tbl] = {
                'en':      col_info['en'],       # Row6 英文字段列表
                'cn_en':   col_info['cn_en'],     # 中文→英文
                'en_cn':   col_info['en_cn'],     # 英文→中文
                'en_type': col_info['en_type'],   # 英文→数据类型
                'col_map': col_info['col_map'],   # 英文→Excel列号
            }
        except Exception as e:
            field_maps[tbl] = {'error': str(e)}

    return {
        'field_maps': field_maps,
        'instruction': (
            "[WARN] 所有字段名必须使用 field_maps 中 en 列表里的英文名。\n"
            "禁止自行翻译中文为英文。\n"
            "中英对照参考 cn_en 映射。"
        ),
    }
