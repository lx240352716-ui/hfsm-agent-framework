# -*- coding: utf-8 -*-
"""L2 执行策划 + L3 QA — 真实运行"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'executor_memory', 'process'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'qa_memory', 'process'))
from table_reader import max_id, get_columns
import executor_hooks as l2
from qa_hooks import on_enter_qa, on_enter_merge, on_enter_done

t0 = time.time()

# ── L2 ──
print("=" * 60)
print("  L2 执行策划")
print("=" * 60)

print("\n[L2-1/5] execute")
r = l2.on_enter_execute()
print(f"  status={r['status']}, tables={r.get('tables')}")

print("\n[L2-2/5] align")
r = l2.on_enter_align()
print(f"  status={r['status']}")
# 看 align_report
ar = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'executor_memory', 'data', 'align_result.json'), encoding='utf-8'))
for tbl, rpt in ar.get('align_report', {}).items():
    print(f"  {tbl}: filled={len(rpt.get('filled',[]))}, unfilled={len(rpt.get('unfilled',[]))}")

print("\n[L2-3/5] fill")
r = l2.on_enter_fill()
for tbl, how in r.get('match_info', {}).items():
    print(f"  {tbl}: {how}")

print("\n[L2-4/5] fill_confirm")
r = l2.on_enter_fill_confirm()
print(f"  uncertain={r.get('uncertain_count', 0)}")
# 看 filled_result.json 里的 _ShopItem 数据，确认 overrides 是否生效
fr = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'executor_memory', 'data', 'filled_result.json'), encoding='utf-8'))
for tbl, rows in fr.get('tables', {}).items():
    if rows:
        # 只打印关键字段
        print(f"\n  {tbl} 新行关键字段:")
        for key in list(rows[0].keys())[:5]:
            print(f"    {key} = {rows[0][key]}")
        if tbl == '_ShopItem':
            for key in ['currencyInfo', 'limitData', 'itemInfo']:
                if key in rows[0]:
                    print(f"    {key} = {rows[0][key]}")

print("\n[L2-5/5] write")
t_w = time.time()
r = l2.on_enter_write()
print(f"  status={r['status']}, time={time.time()-t_w:.2f}s")
print(f"  output_dir={r.get('output_dir')}")
for tbl, cnt in r.get('results', {}).items():
    print(f"  {tbl}: {cnt} rows")

# ── L3 ──
print("\n" + "=" * 60)
print("  L3 QA Agent（黑盒）")
print("=" * 60)

print("\n[L3-1/3] qa")
t_qa = time.time()
r_qa = on_enter_qa()
print(f"\n  status={r_qa['status']}, time={time.time()-t_qa:.2f}s")

if r_qa['status'] == 'QA_FAILED':
    print(f"\n  ❌ QA 不通过！")
    print(f"  {r_qa.get('error_log', '')[:500]}")
    sys.exit(1)

print("\n[L3-2/3] merge")
t_m = time.time()
r_merge = on_enter_merge()
print(f"\n  status={r_merge['status']}, time={time.time()-t_m:.2f}s")
for tbl, info in r_merge.get('merge', {}).items():
    print(f"  {tbl}: {info['status']}, merged={info.get('rows_merged')}")

print("\n[L3-3/3] done")
r_done = on_enter_done()

print("\n" + "=" * 60)
print("  最终验证")
print("=" * 60)
for tbl in ['Item', '_DropGroup', '_ShopItem']:
    col_info = get_columns(tbl)
    mid = max_id(tbl, col_info['cn'][0])
    print(f"  {tbl}: max_id = {mid}")

print(f"\n  总耗时: {time.time()-t0:.2f}s")
print("  🎉 L2→L3 真实执行完成！")
