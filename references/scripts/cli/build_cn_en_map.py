# -*- coding: utf-8 -*-
"""
CN-EN 映射构建脚本 -- 提取 table_registry 分组并输出翻译指令。

功能：
  1. 从 table_registry.json 提取英文分组名
  2. 检查现有 cn_en_map.json 是否已覆盖所有分组
  3. 输出未翻译的分组列表，格式化为 IDE AI 可直接执行的指令

用法：
  python references/scripts/cli/build_cn_en_map.py
"""

import os
import sys
import json
import hashlib
from collections import defaultdict
import re

# 路径设置
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
sys.path.insert(0, CORE_DIR)

from constants import BASE_DIR, CONFIGS_DIR, KNOWLEDGE_DIR

WIKI_DIR = os.path.join(KNOWLEDGE_DIR, 'wiki')
CN_EN_MAP_PATH = os.path.join(WIKI_DIR, 'cn_en_map.json')
REGISTRY_PATH = os.path.join(CONFIGS_DIR, 'table_registry.json')


def extract_groups():
    """从 table_registry.json 提取文件夹/前缀分组。

    Returns:
        tuple: (groups, registry_hash)
            groups: {folder_or_prefix: [table_name, ...]}
            registry_hash: str
    """
    if not os.path.exists(REGISTRY_PATH):
        print("[WARN] table_registry.json not found, run init_project.py first")
        return {}, ''

    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    sorted_names = sorted(registry.keys())
    registry_hash = hashlib.sha256('|'.join(sorted_names).encode()).hexdigest()[:16]

    # 按文件夹分组
    folder_groups = defaultdict(list)
    root_tables = []

    for table_name, rel_path in registry.items():
        parts = rel_path.replace('/', '\\').split('\\')
        if len(parts) > 1:
            folder = parts[0]
            folder_groups[folder].append(table_name)
        else:
            root_tables.append(table_name)

    # 散表按 PascalCase 前缀聚合
    prefix_groups = defaultdict(list)
    for table in root_tables:
        parts = re.findall(r'[A-Z_][a-z0-9]*', table)
        prefix = parts[0] if parts else table
        if len(prefix) >= 2:
            prefix_groups[prefix].append(table)

    groups = dict(folder_groups)
    for prefix, tables in prefix_groups.items():
        if len(tables) >= 2 and prefix not in groups:
            groups[prefix] = tables

    return groups, registry_hash


def check_existing(groups, registry_hash):
    """检查现有 cn_en_map.json 的覆盖情况。

    Returns:
        tuple: (existing_mapping, new_groups)
    """
    existing_mapping = {}
    if os.path.exists(CN_EN_MAP_PATH):
        try:
            with open(CN_EN_MAP_PATH, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            existing_mapping = cached.get('mapping', {})
            if cached.get('registry_hash') == registry_hash:
                return existing_mapping, []
        except Exception:
            pass

    translated_en = set(existing_mapping.values())
    new_groups = [g for g in sorted(groups.keys()) if g not in translated_en]
    return existing_mapping, new_groups


def main():
    groups, registry_hash = extract_groups()
    if not groups:
        return

    print(f"[i] table_registry.json: {len(groups)} groups, hash={registry_hash}")

    existing_mapping, new_groups = check_existing(groups, registry_hash)

    if not new_groups:
        print(f"[OK] cn_en_map.json already complete ({len(existing_mapping)} terms)")
        return

    # 输出结构化翻译指令，让 IDE AI 执行
    print(f"\n[ACTION] cn_en_map.json needs update: {len(new_groups)} new groups to translate")
    print(f"[ACTION] Target file: {CN_EN_MAP_PATH}")
    print(f"[ACTION] Registry hash: {registry_hash}")
    print(f"\n--- Groups needing Chinese translation ---")
    for g in new_groups:
        table_count = len(groups.get(g, []))
        samples = ', '.join(groups.get(g, [])[:3])
        print(f"  {g} ({table_count} tables, e.g. {samples})")

    print(f"\n--- Required action ---")
    print(f"Please translate each English group name above to a Chinese game term,")
    print(f"then write to: {CN_EN_MAP_PATH}")
    print(f"Format: {{\"registry_hash\": \"{registry_hash}\", \"mapping\": {{\"<chinese>\": \"<english>\", ...}}}}")

    if existing_mapping:
        print(f"\n[i] Keep existing {len(existing_mapping)} translations, add new ones")


if __name__ == '__main__':
    main()
