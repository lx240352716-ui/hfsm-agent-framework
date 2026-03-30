# -*- coding: utf-8 -*-
"""查 _ShopItem goodIndex=78 参考行"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from table_reader import query_db, get_columns

si_cols = get_columns('_ShopItem')
rows = query_db(f"SELECT * FROM [_ShopItem] WHERE [{si_cols['cn'][0]}]='78'")
if rows:
    print("_ShopItem goodIndex=78:")
    for key, val in rows[0].items():
        if val is not None and str(val).strip():
            idx = si_cols['cn'].index(key) if key in si_cols['cn'] else -1
            en = si_cols['en'][idx] if 0 <= idx < len(si_cols['en']) else '?'
            print(f"  {key} ({en}) = {val}")
else:
    print("未找到 goodIndex=78")
