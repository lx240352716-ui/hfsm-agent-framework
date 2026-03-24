# -*- coding: utf-8 -*-
"""
Hook 工具函数

所有 Agent 的 hooks 共用的 JSON/MD 读写 + pending 操作。
框架级通用函数，不含业务逻辑。
"""

import os
import json


def load_json(filepath):
    """安全读取 JSON 文件"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_json(filepath, data):
    """安全写入 JSON 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_md(knowledge_dir, filename):
    """加载知识库 MD 文件

    先在 knowledge_dir 下找（含子目录），找不到返回空字符串。
    """
    # 直接路径
    path = os.path.join(knowledge_dir, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    # 搜子目录
    for root, dirs, files in os.walk(knowledge_dir):
        if filename in files:
            with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                return f.read()
    return ''


def load_md_batch(knowledge_dir, filenames):
    """批量加载 MD 文件，返回拼接后的字符串"""
    parts = []
    for fn in filenames:
        content = load_md(knowledge_dir, fn)
        if content:
            parts.append(content)
    return '\n\n---\n\n'.join(parts)


def init_pending(data_dir, task_id='', requirement=''):
    """覆盖写 pending_examples.json（初始化，清除上一次残留）"""
    os.makedirs(data_dir, exist_ok=True)
    save_json(os.path.join(data_dir, 'pending_examples.json'), {
        "task_id": task_id,
        "requirement": requirement,
        "entries": [],
    })


def append_pending(data_dir, target, content):
    """追加一条 entry 到 pending_examples.json。

    Args:
        data_dir: Agent 的 data 目录
        target: 目标文件名（如 "numerical_examples.md"）
        content: 要追加的内容字符串
    """
    pending_path = os.path.join(data_dir, 'pending_examples.json')
    pending = load_json(pending_path) or {"entries": []}
    if "entries" not in pending:
        pending["entries"] = []
    pending["entries"].append({
        "target": target,
        "content": content,
    })
    save_json(pending_path, pending)


def commit_pending(agents_dir, agent_names):
    """提交所有 Agent 的 pending 到正式知识库。

    遍历每个 Agent 的 data/pending_examples.json，
    将 entries 追加到对应的 knowledge/ 目标文件。

    Args:
        agents_dir: agents 根目录
        agent_names: Agent 名称列表
    Returns:
        dict: {agent_name: committed_count}
    """
    results = {}
    for agent_name in agent_names:
        data_dir = os.path.join(agents_dir, agent_name, 'data')
        knowledge_dir = os.path.join(agents_dir, agent_name, 'knowledge')
        pending_path = os.path.join(data_dir, 'pending_examples.json')

        if not os.path.exists(pending_path):
            results[agent_name] = 0
            continue

        pending = load_json(pending_path)
        count = 0
        for entry in pending.get('entries', []):
            target = entry.get('target', '')
            content = entry.get('content', '')
            if target and content:
                target_path = os.path.join(knowledge_dir, target)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + content)
                count += 1

        # 清空 pending
        save_json(pending_path, {"entries": []})
        results[agent_name] = count

    return results
