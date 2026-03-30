# -*- coding: utf-8 -*-
"""
从 table_registry.json + SQLite 生成增强版 table_directory.md

- 所有表：表名 + 文件路径（按目录分组）
- 已索引的表：额外输出中英文字段对照表
"""
import json, os, sys, sqlite3
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from constants import AGENTS_DIR, CONFIGS_DIR, CORE_DIR

REGISTRY_PATH = os.path.join(CONFIGS_DIR, 'table_registry.json')
DB_PATH = os.path.join(CORE_DIR, 'table_index.db')
OUTPUT_PATH = os.path.join(AGENTS_DIR, 'numerical_memory', 'knowledge', 'table_directory.md')

with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
    registry = json.load(f)

# 查已索引的表 + 拿字段
indexed_columns = {}
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    # 拿所有已索引的表名
    indexed_tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for tbl in indexed_tables:
        if tbl not in registry:
            continue
        try:
            from table_reader import get_columns
            col_info = get_columns(tbl)
            cols_cn = col_info['cn']
            # 使用 cn_en 构建中英对照
            pairs = [(cn, col_info['cn_en'].get(cn, cn)) for cn in cols_cn]
            indexed_columns[tbl] = pairs
        except Exception:
            pass
    conn.close()

print(f"已索引表: {len(indexed_columns)} / {len(registry)} 总表")

# 按目录分组
groups = defaultdict(list)
for table_name, path in registry.items():
    parts = path.replace('\\\\', '\\').split('\\')
    group = parts[0] if len(parts) > 1 else '_root'
    groups[group].append((table_name, path))

# 生成 MD
lines = []
lines.append("# 配表目录索引")
lines.append("")
lines.append("> locate 阶段使用：根据模块名找到对应的真实表名和字段。")
lines.append(f"> 共 {len(registry)} 张表，{len(indexed_columns)} 张已含字段详情。")
lines.append("")

for group in sorted(groups.keys()):
    tables = sorted(groups[group], key=lambda x: x[0])
    lines.append(f"## {group}/ ({len(tables)}张)")
    lines.append("")
    lines.append("| 表名 | 文件 |")
    lines.append("|------|------|")
    for name, path in tables:
        has_cols = "📋" if name in indexed_columns else ""
        lines.append(f"| {name} {has_cols} | {path} |")
    lines.append("")

    # 已索引的表输出字段详情
    for name, _ in tables:
        if name in indexed_columns:
            pairs = indexed_columns[name]
            lines.append(f"### {name} 字段 ({len(pairs)}列)")
            lines.append("")
            lines.append("| 中文 | 英文 |")
            lines.append("|------|------|")
            for cn, en in pairs:
                lines.append(f"| {cn} | {en} |")
            lines.append("")

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"输出: {OUTPUT_PATH}")
print(f"总行数: {len(lines)}")
