# -*- coding: utf-8 -*-
"""清除残留测试数据 → 真实执行 L2+L3 全链路"""
import sys, os, time, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'qa_memory', 'process'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'executor_memory', 'process'))
from table_reader import max_id, get_columns, _get_table_path, refresh_index, get_com_excel, open_workbook, close_com_excel

original_ids = {"Item": 76000016, "_DropGroup": 300110, "_ShopItem": 214005}

# ══════════════════════════════════════════════
#  Step 0: 清除残留数据
# ══════════════════════════════════════════════
print("=" * 60)
print("  Step 0: 清除残留数据")
print("=" * 60)

for tbl, expected in original_ids.items():
    col_info = get_columns(tbl)
    pk_cn = col_info['cn'][0]
    current = max_id(tbl, pk_cn)
    print(f"  {tbl}: max_id={current} (原始={expected})")

excel = get_com_excel()

for tbl, expected in original_ids.items():
    col_info = get_columns(tbl)
    pk_cn = col_info['cn'][0]
    current = max_id(tbl, pk_cn)
    while current > expected:
        wb, ws = open_workbook(tbl, read_only=False)
        last = ws.UsedRange.Rows.Count
        ws.Rows(last).Delete()
        wb.Save()
        wb.Close(False)
        print(f"  [{tbl}] 删除 row {last}")
        # 删完后刷索引
        refresh_index(_get_table_path(tbl), tbl)
        current = max_id(tbl, pk_cn)

close_com_excel()

print("\n  清除后:")
for tbl, expected in original_ids.items():
    col_info = get_columns(tbl)
    current = max_id(tbl, col_info['cn'][0])
    status = "✅" if current == expected else "❌"
    print(f"  {tbl}: max_id={current} {status}")

# ══════════════════════════════════════════════
#  Step 1: L2 执行策划
# ══════════════════════════════════════════════
import executor_hooks as l2

print("\n" + "=" * 60)
print("  Step 1: L2 执行策划")
print("=" * 60)

t0 = time.time()

print("\n[L2-1/5] execute")
r = l2.on_enter_execute()
print(f"  status={r['status']}, tables={r.get('tables')}")

print("\n[L2-2/5] align")
r = l2.on_enter_align()
print(f"  status={r['status']}")

print("\n[L2-3/5] fill")
r = l2.on_enter_fill()
print(f"  ref_rows: {list(r.get('reference_rows', {}).keys())}")

print("\n[L2-4/5] fill_confirm")
r = l2.on_enter_fill_confirm()
print(f"  uncertain_count={r.get('uncertain_count', 0)}")

print("\n[L2-5/5] write")
t5 = time.time()
r = l2.on_enter_write()
print(f"  status={r['status']}, time={time.time()-t5:.2f}s")
print(f"  output_dir={r.get('output_dir')}")
for tbl, cnt in r.get('results', {}).items():
    print(f"  {tbl}: {cnt} rows")

# ══════════════════════════════════════════════
#  Step 2: L3 QA Agent
# ══════════════════════════════════════════════
from qa_hooks import on_enter_qa, on_enter_merge, on_enter_done

print("\n" + "=" * 60)
print("  Step 2: L3 QA Agent")
print("=" * 60)

print("\n[L3-1/3] qa (黑盒: 读 xlsx)")
t_qa = time.time()
r_qa = on_enter_qa()
print(f"\n  status={r_qa['status']}, time={time.time()-t_qa:.2f}s")

if r_qa['status'] == 'QA_FAILED':
    print(f"\n  ❌ QA 不通过！")
    print(f"  {r_qa.get('error_log', '')[:300]}")
    sys.exit(1)

print("\n[L3-2/3] merge")
t_m = time.time()
r_merge = on_enter_merge()
print(f"\n  status={r_merge['status']}, time={time.time()-t_m:.2f}s")
for tbl, info in r_merge.get('merge', {}).items():
    print(f"  {tbl}: {info['status']}, merged={info.get('rows_merged')}")

print("\n[L3-3/3] done")
r_done = on_enter_done()
print(f"\n  status={r_done['status']}")

# ══════════════════════════════════════════════
#  Step 3: 验证
# ══════════════════════════════════════════════
print("\n" + "=" * 60)
print("  Step 3: 验证")
print("=" * 60)

all_ok = True
for tbl, expected in original_ids.items():
    col_info = get_columns(tbl)
    current = max_id(tbl, col_info['cn'][0])
    status = "✅" if current == expected + 1 else "❌"
    if current != expected + 1:
        all_ok = False
    print(f"  {tbl}: {expected} → {current} {status}")

print(f"\n  总耗时: {time.time()-t0:.2f}s")
if all_ok:
    print("  🎉 全链路真实执行成功！数据已写入源表。")
else:
    print("  ⚠️ 有表不符合预期")
