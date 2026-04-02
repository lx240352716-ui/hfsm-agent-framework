# -*- coding: utf-8 -*-
"""查彩钻商场的shopType + 每周限购的limitData格式"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from table_reader import query_db

# 查 _ShopType 表看商店类型
print("=== 商店类型 ===")
try:
    types = query_db("SELECT * FROM [_ShopType] LIMIT 20")
    for t in types:
        clean = {k:v for k,v in t.items() if v not in (None, 'None', '') and not k.startswith('EmptyKey') and not k.startswith('Unnamed')}
        print(f"  {clean}")
except Exception as e:
    print(f"  _ShopType 查询失败: {e}")

# 查含"彩钻"的商品
print("\n=== 彩钻相关商品 (货币info含彩钻) ===")
# 彩钻一般是货币类型2或3，查几个看看
rows = query_db("SELECT [货物index],[商店类型],[货币info],[货物info],[限购数据],[所属分页] FROM [_ShopItem] WHERE [货物index] != 'None' AND [限购数据] NOT LIKE '%0,0,0,0,0%' LIMIT 10")
for r in rows:
    print(f"  {r}")
