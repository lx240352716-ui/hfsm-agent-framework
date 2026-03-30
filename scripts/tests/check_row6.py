# -*- coding: utf-8 -*-
"""检查各表的 Row6 到底是什么"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from table_reader import get_columns, query_db

for tbl in ['Item', '_DropGroup', '_ShopItem']:
    cn = get_columns(tbl)[:5]
    en = get_columns(tbl, english=True)[:5]
    # 也查前5行数据看看
    rows = query_db(f"SELECT * FROM [{tbl}] LIMIT 1 OFFSET 0")
    first_vals = list(rows[0].values())[:5] if rows else []
    
    print(f"=== {tbl} ===")
    print(f"  Row2(中文): {cn}")
    print(f"  Row6(英文): {en}")
    print(f"  数据第1行:  {first_vals}")
    
    # 判断 Row6 是否等于中文列名（说明没有英文名）
    same = sum(1 for a, b in zip(cn, en) if a == b)
    print(f"  中英相同数: {same}/{len(cn)}")
    print()
