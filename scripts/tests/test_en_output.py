# -*- coding: utf-8 -*-
"""验证 cn_to_en_map + 用英文字段名重新生成 output.json"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'numerical_memory', 'process'))
from constants import AGENTS_DIR
import numerical_hooks as hooks
from table_reader import max_id

DATA = os.path.join(AGENTS_DIR, 'numerical_memory', 'data')

# 1. 验证 cn_to_en_map
print("=== cn_to_en_map 验证 ===\n")
for tbl in ['Item', '_DropGroup', '_ShopItem']:
    m = hooks._cn_to_en_map(tbl)
    print(f"{tbl} ({len(m)} 字段):")
    for cn, en in list(m.items())[:5]:
        print(f"  {cn:20s} → {en}")
    print(f"  ...")

# 2. 用英文字段名重新生成 output.json
print("\n=== 重新生成 output.json (Row6 英文名) ===\n")

item_map = hooks._cn_to_en_map('Item')
drop_map = hooks._cn_to_en_map('_DropGroup')
shop_map = hooks._cn_to_en_map('_ShopItem')

item_next = (max_id('Item', '物品id') or 0) + 1
drop_next = (max_id('_DropGroup', '掉落组ID') or 0) + 1
shop_next = (max_id('_ShopItem', '货物index') or 0) + 1

# 中文数据 → 英文 key
item_cn = {
    "物品id": str(item_next),
    "物品大类型": "1001", "物品子类型": "6", "背包类型": "1001",
    "名字": "清明节礼包", "名字文本": "清明节礼包",
    "描述文本": "开启后可获得清明节活动道具。",
    "图标": "item_250136", "物品使用等级": "1", "物品品质": "5",
    "类别": "2", "堆叠数量": "999", "使用CD（秒）": "0",
    "功能": "1017", "功能扩展字段": str(drop_next),
    "是否可以回收": "1", "回收货币类型": "5", "回收价格": "100",
    "绑定类型": "1", "是否可移仓库": "1", "是否通过邮件拾取": "1",
    "是否为贵重物品": "0", "是否可以交易": "0",
    "回购货币类型": "5", "回购价格": "100", "排序权重": "110",
    "药品自动使用": "0", "可使用物品的展示类型": "4", "使用结果展示": "2",
    "公共CD(秒)": "1", "是否显示绑定按钮": "1",
    "名字-AP2": "清明节礼包", "防盖表经典怀旧判断": "1",
}
item_en = {item_map.get(k, k): v for k, v in item_cn.items()}

drop_cn = {
    "掉落组ID": str(drop_next), "掉落组类型": "1", "随机次数": "1",
    "是否是绑定道具": "1", "最大随机数量": "1",
    "参数": f"1001,{item_next},1,100", "描述": "清明节礼包掉落",
}
drop_en = {drop_map.get(k, k): v for k, v in drop_cn.items()}

shop_cn = {
    "货物index": str(shop_next), "商店类型": "0",
    "货币info": "1,0,100", "货物info": f"1001,{item_next},1",
    "限购数据": "0,0,3,5,0", "所属分页": "1",
}
shop_en = {shop_map.get(k, k): v for k, v in shop_cn.items()}

output = {
    "_schema": "numerical_output",
    "task_id": "20260318_qingming",
    "requirement": "清明节礼包（仿觉醒徽章礼盒·沙鳄鱼）",
    "reference": "觉醒徽章礼盒（沙·鳄鱼）619021 → 掉落组220010",
    "tables": {
        "Item": [item_en],
        "_DropGroup": [drop_en],
        "_ShopItem": [shop_en],
    }
}

output_path = os.path.join(DATA, 'output.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(json.dumps(output, ensure_ascii=False, indent=2))
