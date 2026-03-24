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
