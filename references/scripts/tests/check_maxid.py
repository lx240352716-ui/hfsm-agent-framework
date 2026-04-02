# -*- coding: utf-8 -*-
"""验证 max_id 到底能不能用英文列名查"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from table_reader import max_id

for tbl, pk_cn, pk_en in [
    ('Item', '物品id', 'itemId'),
    ('_DropGroup', '掉落组ID', 'groupId'),
    ('_ShopItem', '货物index', 'goodIndex'),
]:
    m_cn = max_id(tbl, pk_cn)
    m_en = max_id(tbl, pk_en)
    print(f"{tbl}: max_id(CN '{pk_cn}')={m_cn} | max_id(EN '{pk_en}')={m_en}")
