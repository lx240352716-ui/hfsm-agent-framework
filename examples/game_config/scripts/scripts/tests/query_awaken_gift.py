# -*- coding: utf-8 -*-
"""查 觉醒徽章礼盒（沙·鳄鱼） 的完整配置链"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
from table_reader import query_db

# 1. Item 表找这个礼包
print("=== 1. Item 表: 觉醒徽章礼盒 ===\n")
rows = query_db("SELECT * FROM [Item] WHERE [名字] LIKE ?", ('%觉醒徽章礼盒%',))
for r in rows:
    # 只显示有值的字段
    clean = {k:v for k,v in r.items() if v not in (None, 'None', '', 'nan') and not k.startswith('EmptyKey')}
    print(json.dumps(clean, ensure_ascii=False, indent=2))
    drop_id = r.get('功能扩展字段')
    item_id = r.get('物品id')
    print(f"\n  → 道具ID: {item_id}")
    print(f"  → 关联掉落组: {drop_id}")

# 2. _DropGroup 表查关联的掉落组
if rows and drop_id and drop_id != 'None':
    print(f"\n=== 2. _DropGroup: 掉落组 {drop_id} ===\n")
    drops = query_db("SELECT * FROM [_DropGroup] WHERE [掉落组ID] = ?", (str(drop_id),))
    for d in drops:
        clean = {k:v for k,v in d.items() if v not in (None, 'None', '') and not k.startswith('EmptyKey') and not k.startswith('Unnamed')}
        print(json.dumps(clean, ensure_ascii=False, indent=2))

# 3. _ShopItem 表查商城配置
if rows and item_id and item_id != 'None':
    print(f"\n=== 3. _ShopItem: 商品含道具 {item_id} ===\n")
    shops = query_db("SELECT * FROM [_ShopItem] WHERE [货物info] LIKE ?", (f'%{item_id}%',))
    if shops:
        for s in shops:
            clean = {k:v for k,v in s.items() if v not in (None, 'None', '') and not k.startswith('EmptyKey') and not k.startswith('Unnamed')}
            print(json.dumps(clean, ensure_ascii=False, indent=2))
    else:
        print("  未找到关联商品（可能不在商城卖）")
