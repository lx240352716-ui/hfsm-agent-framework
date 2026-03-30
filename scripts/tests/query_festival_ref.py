# -*- coding: utf-8 -*-
"""查节日礼包参考数据"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from table_reader import query_db

print("=== Item 表: 节日/活动礼包 ===\n")
rows = query_db("SELECT [物品id],[名字],[物品品质],[功能扩展字段] FROM [Item] WHERE [名字] LIKE ? AND [功能] = '1017' LIMIT 10", ('%节%',))
if not rows:
    rows = query_db("SELECT [物品id],[名字],[物品品质],[功能扩展字段] FROM [Item] WHERE [功能] = '1017' AND [物品品质] IN ('4','5') LIMIT 10")
for r in rows:
    print(f"  {r}")

print("\n=== _DropGroup 表: 参考掉落组 ===\n")
rows = query_db("SELECT * FROM [_DropGroup] WHERE [掉落组ID] IS NOT NULL AND [掉落组ID] != 'None' LIMIT 5")
for r in rows:
    clean = {k:v for k,v in r.items() if not k.startswith('EmptyKey') and v not in (None, 'None', '')}
    print(f"  {clean}")

print("\n=== _ShopItem 表: 参考商品配置 ===\n")
rows = query_db("SELECT [货物index],[商店类型],[货币info],[货物info],[限购数据],[所属分页] FROM [_ShopItem] WHERE [货物index] IS NOT NULL AND [货物index] != 'None' LIMIT 5")
for r in rows:
    print(f"  {r}")
