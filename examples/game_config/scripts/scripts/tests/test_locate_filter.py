# -*- coding: utf-8 -*-
"""模拟 locate: 查礼包参考数据"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
from table_reader import query_db

print("=== 查 Item 表中的礼包参考数据 ===\n")
rows = query_db("SELECT * FROM [Item] WHERE [名字] LIKE ?", ('%礼包%',))
print(f"找到 {len(rows)} 条礼包记录\n")

if rows:
    # 分析字段模式
    all_keys = list(rows[0].keys())
    # 过滤 EmptyKey
    keys = [k for k in all_keys if not k.startswith('EmptyKey') and k != '_pending']
    
    fixed = []
    empty = []
    vary = []
    
    for k in keys:
        vals = [str(r.get(k, '')) for r in rows[:5]]
        unique = set(vals)
        if len(unique) == 1:
            if vals[0] in ('', 'None', '0', 'nan'):
                empty.append(k)
            else:
                fixed.append((k, vals[0]))
        else:
            vary.append(k)
    
    print("── fixed (所有礼包值相同，自动填) ──")
    for k, v in fixed:
        print(f"  {k} = {v}")
    
    print(f"\n── empty (全空/0，不展示) ── ({len(empty)}个)")
    print(f"  {empty[:10]}...")
    
    print(f"\n── input (需用户决策) ── ({len(vary)}个)")
    for k in vary:
        vals = [str(r.get(k, ''))[:20] for r in rows[:3]]
        print(f"  {k}: {vals}")
