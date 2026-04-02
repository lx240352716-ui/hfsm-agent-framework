# -*- coding: utf-8 -*-
"""查 Item 表前6行数据，找英文字段名在哪一行"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from table_reader import query_db

print("=== Item 表前6行 ===\n")
for i in range(6):
    row = query_db(f"SELECT * FROM [Item] LIMIT 1 OFFSET {i}")
    if row:
        vals = list(row[0].values())[:8]
        print(f"  OFFSET {i} (Excel Row{i+2}): {vals}")
    else:
        print(f"  OFFSET {i}: (无数据)")

print("\n=== _DropGroup 表前6行对比 ===\n")
for i in range(6):
    row = query_db(f"SELECT * FROM [_DropGroup] LIMIT 1 OFFSET {i}")
    if row:
        vals = list(row[0].values())[:6]
        print(f"  OFFSET {i} (Excel Row{i+2}): {vals}")
