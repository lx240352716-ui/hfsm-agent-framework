# -*- coding: utf-8 -*-
"""
Prompt 构建器 — 把 Agent 知识文件组装成 LLM system prompt。

每个 Agent 的每个状态都有特定的知识文件列表。
此模块负责：
1. 加载 MD 知识文件
2. 按角色+状态组装结构化的 system prompt
3. 注入上下文数据（如当前任务、中间结果等）

Usage:
    from prompt_builder import build_system_prompt
    prompt = build_system_prompt('numerical_memory', 'fill', context={...})
"""

import os
import json

from constants import AGENTS_DIR, agent_paths


# ── Agent 角色定义 ──

AGENT_ROLES = {
    'coordinator_memory': {
        'name': '主策划',
        'layer': 'L0 决策层',
        'description': '你是主策划，负责理解用户需求、拆分功能模块、分派给下游策划。',
    },
    'combat_memory': {
        'name': '战斗策划',
        'layer': 'L1 设计层',
        'description': '你是战斗策划，负责将自然语言需求翻译为配表字段结构化设计方案。',
    },
    'numerical_memory': {
        'name': '数值策划',
        'layer': 'L1 设计层',
        'description': '你是数值策划，负责定位配表、查参考数据、确定数值参数。',
    },
    'executor_memory': {
        'name': '执行策划',
        'layer': 'L2 执行层',
        'description': '你是执行策划，负责接收设计方案、对齐 Excel 行、填充字段值、分配 ID、写入配表。',
    },
    'qa_memory': {
        'name': 'QA',
        'layer': 'L3 自动化层',
        'description': '你是 QA 校验员，负责检查填表结果的正确性。',
    },
}


def load_knowledge_files(agent_name: str, state: str = None) -> list[dict]:
    """加载 Agent 的知识文件。

    Args:
        agent_name: Agent 名（如 'numerical_memory'）
        state: 当前状态名（如 'fill'），None 时只加载 Agent 级知识

    Returns:
        list[dict]: [{"filename": "xxx.md", "content": "..."}, ...]
    """
    paths = agent_paths(agent_name)
    knowledge_dir = paths['knowledge_dir']
    files = []

    if not os.path.isdir(knowledge_dir):
        return files

    # 1. Agent 级知识（knowledge/*.md）
    for f in sorted(os.listdir(knowledge_dir)):
        fpath = os.path.join(knowledge_dir, f)
        if f.endswith('.md') and os.path.isfile(fpath):
            with open(fpath, encoding='utf-8') as fp:
                content = fp.read().strip()
            if content and len(content) > 20:  # 跳过空模板
                files.append({"filename": f, "content": content})

    # 2. 状态级知识（knowledge/{state}/*.md）
    if state:
        state_dir = os.path.join(knowledge_dir, state)
        if os.path.isdir(state_dir):
            for f in sorted(os.listdir(state_dir)):
                fpath = os.path.join(state_dir, f)
                if f.endswith('.md') and os.path.isfile(fpath):
                    with open(fpath, encoding='utf-8') as fp:
                        content = fp.read().strip()
                    if content and len(content) > 20:
                        files.append({
                            "filename": f"{state}/{f}",
                            "content": content,
                        })

    return files


def build_system_prompt(agent_name: str, state: str = None,
                        context: dict = None,
                        extra_instructions: str = None) -> str:
    """构建完整的 system prompt。

    Args:
        agent_name: Agent 名
        state: 当前状态名
        context: 上下文数据（如当前任务信息、中间结果）
        extra_instructions: 额外指令

    Returns:
        str: 完整的 system prompt
    """
    role = AGENT_ROLES.get(agent_name, {})
    parts = []

    # ── 角色定义 ──
    parts.append(f"# 角色：{role.get('name', agent_name)}")
    parts.append(f"> 层级：{role.get('layer', '未知')}")
    parts.append(role.get('description', ''))
    if state:
        parts.append(f"\n**当前步骤**：`{state}`")

    # ── 知识库 ──
    knowledge = load_knowledge_files(agent_name, state)
    if knowledge:
        parts.append("\n---\n# 知识库\n")
        for item in knowledge:
            parts.append(f"## 📚 {item['filename']}\n")
            parts.append(item['content'])
            parts.append("")

    # ── 上下文数据 ──
    if context:
        parts.append("\n---\n# 当前上下文\n")
        parts.append("```json")
        parts.append(json.dumps(context, ensure_ascii=False, indent=2))
        parts.append("```")

    # ── 额外指令 ──
    if extra_instructions:
        parts.append(f"\n---\n# 补充指令\n\n{extra_instructions}")

    return "\n".join(parts)


def build_user_message(requirement: str, data: dict = None) -> str:
    """构建用户消息。

    Args:
        requirement: 用户需求描述
        data: 附带的结构化数据（如前一阶段的输出）

    Returns:
        str: 格式化的用户消息
    """
    parts = [requirement]

    if data:
        parts.append("\n\n**附带数据**：")
        parts.append("```json")
        parts.append(json.dumps(data, ensure_ascii=False, indent=2))
        parts.append("```")

    return "\n".join(parts)
