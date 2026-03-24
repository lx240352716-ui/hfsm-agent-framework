# -*- coding: utf-8 -*-
"""精确查沙·鳄鱼"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
from table_reader import query_db

print("=== 沙·鳄鱼 Item ===")
rows = query_db("SELECT * FROM [Item] WHERE [名字] LIKE ?", ('%沙%鳄鱼%',))
for r in rows:
    clean = {k:v for k,v in r.items() if v not in (None, 'None', '', 'nan') and not k.startswith('EmptyKey')}
    print(json.dumps(clean, ensure_ascii=False, indent=2))
    drop_id = r.get('功能扩展字段')
    item_id = r.get('物品id')

if rows and drop_id:
    print(f"\n=== 掉落组 {drop_id} ===")
    drops = query_db("SELECT * FROM [_DropGroup] WHERE [掉落组ID] = ?", (str(drop_id),))
    for d in drops:
        clean = {k:v for k,v in d.items() if v not in (None, 'None', '') and not k.startswith('EmptyKey') and not k.startswith('Unnamed')}
        print(json.dumps(clean, ensure_ascii=False, indent=2))
