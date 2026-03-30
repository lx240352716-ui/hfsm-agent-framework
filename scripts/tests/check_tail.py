# -*- coding: utf-8 -*-
"""找测试数据的边界"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from table_reader import query_db, get_columns

# Item: 76000013 之前是什么？
print("Item: ID > 16000000 的行（找 76000xxx 系列有几行）:")
rows = query_db("SELECT [物品id], [名字] FROM [Item] WHERE CAST([物品id] AS INTEGER) > 16010011 ORDER BY CAST([物品id] AS INTEGER)")
for r in rows:
    vals = list(r.values())
    print(f"  {vals[0]}  |  {vals[1]}")
print(f"  共 {len(rows)} 行")

# _DropGroup: 300100 之前是什么？
print("\n_DropGroup: 找 300xxx 系列之前的数据:")
rows = query_db("SELECT [掉落组ID] FROM [_DropGroup] ORDER BY CAST([掉落组ID] AS INTEGER) DESC LIMIT 20")
for r in rows:
    print(f"  {list(r.values())[0]}")

# _DropGroup: 300101 之前一行
rows = query_db("SELECT [掉落组ID] FROM [_DropGroup] WHERE CAST([掉落组ID] AS INTEGER) < 300100 ORDER BY CAST([掉落组ID] AS INTEGER) DESC LIMIT 3")
print("\n_DropGroup: 300100 之前的行:")
for r in rows:
    print(f"  {list(r.values())[0]}")
