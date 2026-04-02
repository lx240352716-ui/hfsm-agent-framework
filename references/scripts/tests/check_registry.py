# -*- coding: utf-8 -*-
import json, os
r = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'configs', 'table_registry.json'), 'r', encoding='utf-8'))
print(f"总表数: {len(r)}")
print(f"_DropGroup in registry: {'_DropGroup' in r}")
print(f"_ShopItem in registry: {'_ShopItem' in r}")
drop_keys = [k for k in r if 'drop' in k.lower()]
shop_keys = [k for k in r if 'shop' in k.lower()]
print(f"含drop的表: {drop_keys}")
print(f"含shop的表: {shop_keys}")
