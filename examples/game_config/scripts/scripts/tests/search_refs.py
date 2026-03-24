import sys, os
sys.path.insert(0, os.path.join('scripts', 'core'))
from table_reader import query_db, get_columns

# Item: 觉醒徽章
print("=== Item 觉醒徽章 ===")
rows = query_db("SELECT * FROM [Item] WHERE [名字] LIKE '%觉醒徽章%' LIMIT 10")
for r in (rows or []):
    pid = r.get('物品ID', '?')
    name = r.get('名字', '?')
    print(f"  id={pid} | {name}")

# _DropGroup columns
cols = get_columns('_DropGroup')
pk = cols['cn'][0]
print(f"\n_DropGroup pk={pk}")
rows = query_db(f"SELECT * FROM [_DropGroup] WHERE [{pk}] BETWEEN 220008 AND 220025")
for r in (rows or []):
    gid = r.get(pk, '?')
    print(f"  {gid} | keys={list(r.keys())[:5]}")

# _ShopItem around 78
cols2 = get_columns('_ShopItem')
pk2 = cols2['cn'][0]
print(f"\n_ShopItem pk={pk2}")
rows2 = query_db(f"SELECT * FROM [_ShopItem] WHERE [{pk2}] BETWEEN 75 AND 85")
for r in (rows2 or []):
    print(f"  {r.get(pk2, '?')}")
