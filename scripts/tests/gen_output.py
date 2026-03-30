# -*- coding: utf-8 -*-
"""output 阶段: 自动分配ID + 组装最终 output.json"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from constants import AGENTS_DIR
from table_reader import query_db, max_id

DATA_DIR = os.path.join(AGENTS_DIR, 'numerical_memory', 'data')

# 1. 分配 ID
item_next = (max_id('Item', '物品id') or 0) + 1
drop_next = (max_id('_DropGroup', '掉落组ID') or 0) + 1
shop_next = (max_id('_ShopItem', '货物index') or 0) + 1

print(f"分配 ID:")
print(f"  Item: {item_next}")
print(f"  _DropGroup: {drop_next}")
print(f"  _ShopItem: {shop_next}")

# 2. 组装 output.json
output = {
    "_schema": "numerical_output",
    "task_id": "20260318_qingming",
    "requirement": "清明节礼包（仿觉醒徽章礼盒·沙鳄鱼）",
    "reference": "觉醒徽章礼盒（沙·鳄鱼）619021 → 掉落组220010",
    "tables": {
        "Item": [{
            "物品id": str(item_next),
            "物品大类型": "1001",
            "物品子类型": "6",
            "背包类型": "1001",
            "名字": "清明节礼包",
            "名字文本": "清明节礼包",
            "描述文本": "开启后可获得清明节活动道具。",
            "图标": "item_250136",
            "物品使用等级": "1",
            "物品品质": "5",
            "类别": "2",
            "堆叠数量": "999",
            "使用CD（秒）": "0",
            "功能": "1017",
            "功能扩展字段": str(drop_next),
            "是否可以回收": "1",
            "回收货币类型": "5",
            "回收价格": "100",
            "绑定类型": "1",
            "是否可移仓库": "1",
            "是否通过邮件拾取": "1",
            "是否为贵重物品": "0",
            "是否可以交易": "0",
            "回购货币类型": "5",
            "回购价格": "100",
            "排序权重": "110",
            "药品自动使用": "0",
            "可使用物品的展示类型": "4",
            "使用结果展示": "2",
            "公共CD(秒)": "1",
            "是否显示绑定按钮": "1",
            "名字-AP2": "清明节礼包",
            "防盖表经典怀旧判断": "1",
        }],
        "_DropGroup": [{
            "掉落组ID": str(drop_next),
            "掉落组类型": "1",
            "随机次数": "1",
            "是否是绑定道具": "1",
            "最大随机数量": "1",
            "参数": f"1001,{item_next},1,100",
            "描述": "清明节礼包掉落",
        }],
        "_ShopItem": [{
            "货物index": str(shop_next),
            "商店类型": "0",
            "货币info": "1,0,100",
            "货物info": f"1001,{item_next},1",
            "限购数据": "0,0,3,5,0",
            "所属分页": "1",
        }],
    }
}

# 保存
os.makedirs(DATA_DIR, exist_ok=True)
output_path = os.path.join(DATA_DIR, 'output.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n输出: {output_path}")
print(json.dumps(output, ensure_ascii=False, indent=2))
