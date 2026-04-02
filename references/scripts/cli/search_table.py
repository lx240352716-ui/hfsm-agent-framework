# -*- coding: utf-8 -*-
"""
搜索配表目录 — 根据关键词查找表名和字段

用法：
  python search_table.py 礼包
  python search_table.py DropGroup
  python search_table.py shop --fields    （同时显示字段）
"""
import sys, os, json, re

REGISTRY_PATH = os.path.join(r'G:\op_design', 'references', 'scripts', 'configs', 'table_registry.json')

def search(keyword, show_fields=False, show_sample=False):
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    matches = [(name, path) for name, path in registry.items() if pattern.search(name)]

    if not matches:
        print(f"未找到含 '{keyword}' 的表")
        return

    print(f"找到 {len(matches)} 张含 '{keyword}' 的表:\n")
    for name, path in sorted(matches):
        print(f"  {name:40s} ← {path}")

    if show_fields and matches:
        # 尝试从 SQLite 取字段
        sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'core'))
        from table_reader import get_columns
        print()
        for name, _ in sorted(matches):
            try:
                col_info = get_columns(name)
                cols_cn = col_info['cn']
                cols_en = col_info['en']
                print(f"  === {name} ({len(cols_cn)} 字段) ===")
                for cn in cols_cn:
                    en = col_info['cn_en'].get(cn, '(无英文)')
                    print(f"    {cn:20s} | {en}")
                print()
            except Exception as e:
                print(f"  === {name}: 无法取字段 ({e}) ===\n")

    if show_sample and matches:
        sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'core'))
        from table_reader import query_db
        print()
        for name, _ in sorted(matches):
            try:
                rows = query_db(f"SELECT * FROM [{name}] LIMIT 3")
                print(f"  === {name} 样本数据 ({len(rows)} 行) ===")
                for r in rows:
                    clean = {k: v for k, v in list(r.items())[:8]
                             if not k.startswith('EmptyKey')}
                    print(f"    {clean}")
                print()
            except Exception as e:
                print(f"  === {name}: 无法查数据 ({e}) ===\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python search_table.py <关键词> [--fields] [--sample]")
        sys.exit(1)

    kw = sys.argv[1]
    fields = '--fields' in sys.argv
    sample = '--sample' in sys.argv
    search(kw, show_fields=fields, show_sample=sample)
