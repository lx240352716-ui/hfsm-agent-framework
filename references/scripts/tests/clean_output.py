# -*- coding: utf-8 -*-
"""用 get_columns()['en'] 重新清洗 numerical output.json，只保留 Row6 字段"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from table_reader import get_columns

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'numerical_memory', 'data', 'output.json')

with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
    output = json.load(f)

print("清洗前:")
for tbl, rows in output['tables'].items():
    if rows:
        keys = list(rows[0].keys())
        info = get_columns(tbl)
        row6_set = set(info['en'])
        
        in_row6 = [k for k in keys if k in row6_set]
        not_in_row6 = [k for k in keys if k not in row6_set]
        
        print(f"  {tbl}: {len(keys)} 字段 ({len(in_row6)} Row6 + {len(not_in_row6)} 非Row6)")
        if not_in_row6:
            print(f"    要移除: {not_in_row6}")

# 清洗：只保留 Row6 有的字段
for tbl, rows in output['tables'].items():
    info = get_columns(tbl)
    row6_set = set(info['en'])
    for i, row in enumerate(rows):
        cleaned = {k: v for k, v in row.items() if k in row6_set}
        rows[i] = cleaned

print("\n清洗后:")
for tbl, rows in output['tables'].items():
    if rows:
        print(f"  {tbl}: {len(rows[0])} 字段 (全部 Row6)")
        for k, v in list(rows[0].items())[:5]:
            print(f"    {k}: {v}")

# 保存
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n已保存到 {OUTPUT_PATH}")
