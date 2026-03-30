# -*- coding: utf-8 -*-
"""
模拟执行策划阶段

execute (7步管道) → review (用户确认)

读 numerical output.json → resolve → align → fill_defaults → assign_ids → resolve_refs → check → staging
"""
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'numerical_memory', 'process'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'executor_memory'))
from constants import AGENTS_DIR

from table_reader import get_columns, query_db

NUMERICAL_OUTPUT = os.path.join(AGENTS_DIR, 'numerical_memory', 'data', 'output.json')
EXECUTOR_DATA = os.path.join(AGENTS_DIR, 'executor_memory', 'data')

print("=" * 60)
print("执行策划模拟 — 方案 C（管道式）")
print("=" * 60)

# ── Step 0: 读上游数据 ──
print("\n【0. 读上游 output.json】")
with open(NUMERICAL_OUTPUT, 'r', encoding='utf-8') as f:
    output = json.load(f)
tables = output.get('tables', {})
print(f"  需求: {output.get('requirement')}")
print(f"  涉及表: {list(tables.keys())}")
for tbl, rows in tables.items():
    print(f"  {tbl}: {len(rows)} 行, 字段数={len(rows[0]) if rows else 0}")

# ── Step 1: resolve — 验证表存在 + 读 Excel 表头 ──
print("\n【1. resolve — 验证表+读表头】")
table_headers = {}
for tbl in tables:
    try:
        headers_cn = get_columns(tbl)
        table_headers[tbl] = headers_cn
        print(f"  ✅ {tbl}: {len(headers_cn)} 列")
    except Exception as e:
        print(f"  ❌ {tbl}: {e}")

# ── Step 2: align — 检查字段对齐 ──
print("\n【2. align — 字段对齐检查】")
for tbl, rows in tables.items():
    if tbl not in table_headers:
        continue
    headers = table_headers[tbl]
    for row in rows:
        row_keys = set(row.keys())
        # 用 cn_to_en_map 反向查
        import numerical_hooks as hooks
        cn_en = hooks._cn_to_en_map(tbl)
        en_cn = {v: k for k, v in cn_en.items()}  # 英文→中文

        matched = 0
        missing = []
        extra = []
        for key in row_keys:
            # key 可能是英文或中文
            if key in headers or key in en_cn:
                matched += 1
            else:
                extra.append(key)

        print(f"  {tbl}: {matched}/{len(row_keys)} 字段命中, 未匹配={extra or '无'}")

# ── Step 3: fill_defaults — 补默认值 ──
print("\n【3. fill_defaults — 补默认值（跳过，数值策划已填完）】")
print("  数值策划 output 已包含所有字段值，无需补默认")

# ── Step 4: assign_ids — ID 已由数值策划分配 ──
print("\n【4. assign_ids — ID 检查（数值策划已分配）】")
for tbl, rows in tables.items():
    cn_en = hooks._cn_to_en_map(tbl)
    en_cn = {v: k for k, v in cn_en.items()}
    # 找第一个字段（主键）
    first_key = list(rows[0].keys())[0] if rows else '?'
    first_val = rows[0].get(first_key, '?') if rows else '?'
    print(f"  {tbl}: PK={first_key}={first_val}")

# ── Step 5: resolve_refs — 检查跨表引用 ──
print("\n【5. resolve_refs — 跨表引用检查】")
# Item.params 应该等于 _DropGroup.groupId
item_row = tables.get('Item', [{}])[0]
drop_row = tables.get('_DropGroup', [{}])[0]
shop_row = tables.get('_ShopItem', [{}])[0]

item_params = item_row.get('params', item_row.get('功能扩展字段', '?'))
drop_id = drop_row.get('groupId', drop_row.get('掉落组ID', '?'))
item_id = item_row.get('itemId', item_row.get('物品id', '?'))
shop_item_info = shop_row.get('itemInfo', shop_row.get('货物info', '?'))

print(f"  Item.params={item_params} == _DropGroup.groupId={drop_id} ? {'✅' if item_params == drop_id else '❌'}")
print(f"  _ShopItem.itemInfo 含 Item.itemId={item_id} ? {'✅' if str(item_id) in str(shop_item_info) else '❌'}")
print(f"  _DropGroup.param 含 Item.itemId={item_id} ? {'✅' if str(item_id) in str(drop_row.get('param', '')) else '❌'}")

# ── Step 6: check — 空值/格式校验 ──
print("\n【6. check — 数据校验】")
errors = []
for tbl, rows in tables.items():
    for i, row in enumerate(rows):
        empty_keys = [k for k, v in row.items() if v in (None, '', 'None')]
        if empty_keys:
            errors.append(f"  {tbl}[{i}]: 空值字段 {empty_keys}")
if errors:
    for e in errors:
        print(f"  ⚠️ {e}")
else:
    print("  ✅ 无空值，数据完整")

# ── Step 7: staging — 输出预览 ──
print("\n【7. staging — 生成预览】")
os.makedirs(EXECUTOR_DATA, exist_ok=True)

staging_report = {
    "status": "READY",
    "requirement": output.get('requirement'),
    "reference": output.get('reference'),
    "tables": {},
}
for tbl, rows in tables.items():
    staging_report["tables"][tbl] = {
        "row_count": len(rows),
        "fields": list(rows[0].keys()) if rows else [],
        "preview": rows[0] if rows else {},
    }
    print(f"  {tbl}: {len(rows)} 行 → 待写入 Excel")

staging_path = os.path.join(EXECUTOR_DATA, 'staging.json')
with open(staging_path, 'w', encoding='utf-8') as f:
    json.dump(staging_report, f, ensure_ascii=False, indent=2)
print(f"\n  输出: {staging_path}")

print("\n" + "=" * 60)
print("execute 完成 → 进入 review（等待用户确认）")
print("=" * 60)
