# -*- coding: utf-8 -*-
"""
完整执行策划管道 — 4 状态端到端
"""
import sys, os, json
sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'core'))
sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'agents', 'executor_memory', 'process'))
import executor_hooks as hooks

DATA_DIR = os.path.join(r'G:\op_design', 'references', 'agents', 'executor_memory', 'data')

print("=" * 60)
print("执行策划 — 完整 4 状态管道")
print("=" * 60)

# ═══════════════════════════════════════════
# State 1: execute
# ═══════════════════════════════════════════
print("\n\n▶ [1/4] on_enter_execute")
print("─" * 40)
r1 = hooks.on_enter_execute()
print(f"  涉及表: {r1.get('tables')}")
unfilled = r1.get('unfilled_fields', {})
total_unfilled = sum(len(v) for v in unfilled.values())
for tbl, fields in unfilled.items():
    print(f"  {tbl}: {len(fields)} 个未填字段")
print(f"  共 {total_unfilled} 个未填字段")

# ═══════════════════════════════════════════
# State 2: fill_confirm
# ═══════════════════════════════════════════
print("\n\n▶ [2/4] on_enter_fill_confirm")
print("─" * 40)
r2 = hooks.on_enter_fill_confirm()
ref_data = r2.get('reference_data', {})
for tbl, ref in ref_data.items():
    non_none = {k: v for k, v in ref.items() if v is not None}
    print(f"  {tbl}: {len(non_none)}/{len(ref)} 个字段有参考值")

# 模拟 LLM 填值：用参考数据填，没参考的填 0 或空字符串
print("\n  [模拟 LLM] 用参考值+默认0补全...")
exec_result = json.load(open(os.path.join(DATA_DIR, 'execute_result.json'), encoding='utf-8'))
for tbl, rows in exec_result['tables'].items():
    tbl_ref = ref_data.get(tbl, {})
    for row in rows:
        for k, v in row.items():
            if v == "" or v is None:
                ref_val = tbl_ref.get(k)
                if ref_val is not None:
                    row[k] = ref_val
                else:
                    row[k] = 0

with open(os.path.join(DATA_DIR, 'filled_result.json'), 'w', encoding='utf-8') as f:
    json.dump(exec_result, f, ensure_ascii=False, indent=2)
print("  ✅ filled_result.json 已写入")

# ═══════════════════════════════════════════
# State 3: write
# ═══════════════════════════════════════════
print("\n\n▶ [3/4] on_enter_write")
print("─" * 40)
r3 = hooks.on_enter_write()
status = r3.get('status')
print(f"  status: {status}")
if r3.get('errors'):
    for e in r3['errors']:
        print(f"  ❌ {e}")
for tbl, info in r3.get('allocated_ids', {}).items():
    print(f"  {tbl}: {info['pk_field']} = {info['old_id']} → {info['new_id']}")

if status != 'READY':
    print("\n  ⚠️ 有错误，跳过写入")
    sys.exit(1)

# ═══════════════════════════════════════════
# State 4: review → write Excel
# ═══════════════════════════════════════════
print("\n\n▶ [4/4] on_exit_review → 写入 Excel")
print("─" * 40)
r4 = hooks.on_exit_review()
print(f"  status: {r4.get('status')}")
if r4.get('output_dir'):
    print(f"  📁 输出: {r4['output_dir']}")
for tbl, cnt in r4.get('results', {}).items():
    print(f"    - {tbl}: {cnt} 行")

print("\n" + "=" * 60)
print("✅ 完整管道执行完成")
print("=" * 60)
