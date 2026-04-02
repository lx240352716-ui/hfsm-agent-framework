# -*- coding: utf-8 -*-
"""
全量扫描 excel/ 目录，重建 table_registry.json
所有 .xlsx 文件都收录，表名 = 去掉扩展名的文件名
"""
import os, json

EXCEL_DIR = os.path.join(r'G:\op_design', 'excel')
OUTPUT = os.path.join(r'G:\op_design', 'references', 'scripts', 'configs', 'table_registry.json')

registry = {}

for root, dirs, files in os.walk(EXCEL_DIR):
    for f in files:
        if not f.endswith('.xlsx') or f.startswith('~$'):
            continue
        table_name = os.path.splitext(f)[0]
        rel_path = os.path.relpath(os.path.join(root, f), EXCEL_DIR)
        
        if table_name in registry:
            print(f"  [WARN] 重名: {table_name} → {registry[table_name]} vs {rel_path}")
        registry[table_name] = rel_path

# 按表名排序
registry = dict(sorted(registry.items()))

# 读旧的做对比
old_count = 0
if os.path.exists(OUTPUT):
    with open(OUTPUT, 'r', encoding='utf-8') as f:
        old_count = len(json.load(f))

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(registry, f, ensure_ascii=False, indent=2)

print(f"\n旧 registry: {old_count} 张表")
print(f"新 registry: {len(registry)} 张表")
print(f"新增: {len(registry) - old_count} 张表")
print(f"输出: {OUTPUT}")
