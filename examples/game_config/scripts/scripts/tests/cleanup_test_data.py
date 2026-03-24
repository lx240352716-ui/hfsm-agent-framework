# -*- coding: utf-8 -*-
"""按 '引用了 76000xxx 的就删' 逻辑清除所有测试数据"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
from table_reader import query_db, get_columns, _get_table_path, refresh_index, max_id, get_com_excel, open_workbook, close_com_excel

# ── 1. 查找要删的行 ──
print("=" * 60)
print("  查找引用 76000xxx 的测试行")
print("=" * 60)

# Item: ID >= 76000013
item_rows = query_db("SELECT [物品id],[名字] FROM [Item] WHERE CAST([物品id] AS INTEGER) >= 76000013")
print(f"\nItem: {len(item_rows)} 行")
for r in item_rows:
    vals = list(r.values())
    print(f"  {vals[0]}  |  {vals[1]}")
item_pks = {str(int(float(str(list(r.values())[0])))) for r in item_rows}

# _DropGroup: 任意列包含 76000
dg_col_info = get_columns('_DropGroup')
dg_cn = dg_col_info['cn']
dg_where = ' OR '.join([f"CAST([{c}] AS TEXT) LIKE '%76000%'" for c in dg_cn])
dg_rows = query_db(f"SELECT [{dg_cn[0]}] FROM [_DropGroup] WHERE {dg_where}")
print(f"\n_DropGroup: {len(dg_rows)} 行引用 76000xxx")
dg_pks = {str(int(float(str(list(r.values())[0])))) for r in dg_rows}
for pk in dg_pks:
    print(f"  {pk}")

# _ShopItem: 任意列包含 76000
si_col_info = get_columns('_ShopItem')
si_cn = si_col_info['cn']
si_where = ' OR '.join([f"CAST([{c}] AS TEXT) LIKE '%76000%'" for c in si_cn])
si_rows = query_db(f"SELECT [{si_cn[0]}] FROM [_ShopItem] WHERE {si_where}")
print(f"\n_ShopItem: {len(si_rows)} 行引用 76000xxx")
si_pks = {str(int(float(str(list(r.values())[0])))) for r in si_rows}
for pk in si_pks:
    print(f"  {pk}")

total = len(item_pks) + len(dg_pks) + len(si_pks)
print(f"\n  共 {total} 行待删除")

if total == 0:
    print("  已是干净状态 ✅")
    sys.exit(0)

# ── 2. COM Excel 删除 ──
# 策略：PK 永远是第一列（col 1），从底部往上扫
print("\n" + "=" * 60)
print("  删除测试行")
print("=" * 60)

excel = get_com_excel()

for tbl, pk_vals in [("Item", item_pks), ("_DropGroup", dg_pks), ("_ShopItem", si_pks)]:
    if not pk_vals:
        continue

    wb, ws = open_workbook(tbl, read_only=False)
    max_row = ws.UsedRange.Rows.Count

    # PK = 第一列，从底部往上扫
    rows_to_delete = []
    for r in range(max_row, 6, -1):
        cell_val = ws.Cells(r, 1).Value
        if cell_val is not None:
            # 转成整数字符串来比较
            try:
                cell_str = str(int(float(cell_val)))
            except (ValueError, TypeError):
                cell_str = str(cell_val).strip()
            if cell_str in pk_vals:
                rows_to_delete.append(r)

    rows_to_delete.sort(reverse=True)
    for r in rows_to_delete:
        ws.Rows(r).Delete()
        print(f"  [{tbl}] 删除 row {r}")

    wb.Save()
    wb.Close(False)
    refresh_index(_get_table_path(tbl), tbl)

close_com_excel()

# ── 3. 验证 ──
print("\n" + "=" * 60)
print("  清除后验证")
print("=" * 60)

for tbl in ['Item', '_DropGroup', '_ShopItem']:
    col_info = get_columns(tbl)
    pk_cn = col_info['cn'][0]
    mid = max_id(tbl, pk_cn)
    print(f"  {tbl}: max_id = {mid}")

# 确认无残留
remain_item = query_db("SELECT COUNT(*) as c FROM [Item] WHERE CAST([物品id] AS INTEGER) >= 76000013")
dg_remain = query_db(f"SELECT COUNT(*) as c FROM [_DropGroup] WHERE {dg_where}")
si_remain = query_db(f"SELECT COUNT(*) as c FROM [_ShopItem] WHERE {si_where}")
print(f"\n  Item 76000xxx 残留: {remain_item[0]['c']}")
print(f"  _DropGroup 引用 76000xxx: {dg_remain[0]['c']}")
print(f"  _ShopItem 引用 76000xxx: {si_remain[0]['c']}")
print("\n  ✅ 清除完成" if remain_item[0]['c'] + dg_remain[0]['c'] + si_remain[0]['c'] == 0 else "\n  ❌ 仍有残留")
