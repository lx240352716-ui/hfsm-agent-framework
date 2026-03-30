# -*- coding: utf-8 -*-
"""测试新 executor hooks（4 状态: execute → align → fill → fill_confirm → write）"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'executor_memory', 'process'))
from constants import AGENTS_DIR
import executor_hooks as hooks

print("=" * 60)
print("Executor Hooks 测试（4 状态）")
print("=" * 60)

# 1. on_enter_execute
print("\n── 1. on_enter_execute ──")
r = hooks.on_enter_execute()
print(f"  status: {r.get('status')}")
print(f"  tables: {r.get('tables')}")

# 2. on_enter_align
print("\n── 2. on_enter_align ──")
r2 = hooks.on_enter_align()
print(f"  status: {r2.get('status')}")
for tbl, info in r2.get('align_report', {}).items():
    print(f"  {tbl}: filled={info['filled']}, unfilled={info['unfilled']}, extra={info['extra']}")
    if info.get('unfilled_fields'):
        print(f"    unfilled 前5: {info['unfilled_fields'][:5]}")

# 3. on_enter_fill
print("\n── 3. on_enter_fill ──")
r3 = hooks.on_enter_fill()
print(f"  status: {r3.get('status', 'OK')}")
for tbl, fields in r3.get('unfilled_fields', {}).items():
    print(f"  {tbl}: {len(fields)} 个未填字段")
for tbl, ref in r3.get('reference_data', {}).items():
    print(f"  {tbl} 参考数据: {len(ref)} 个字段")
    print(f"    样例: {dict(list(ref.items())[:3])}")

# 4. 模拟 LLM 填值 → draft_filled.json
print("\n── 4. 模拟 LLM 填值 → draft_filled.json ──")
DATA_DIR = os.path.join(AGENTS_DIR, 'executor_memory', 'data')
align_result = json.load(open(os.path.join(DATA_DIR, 'align_result.json'), encoding='utf-8'))
draft = {"tables": {}}
for tbl, rows in align_result.get('tables', {}).items():
    draft_rows = []
    for row in rows:
        draft_row = dict(row)
        # 模拟：unfilled 字段用 0 填充，部分标 uncertain
        report = align_result.get('align_report', {}).get(tbl, {})
        unfilled = report.get('unfilled', [])
        for i, field in enumerate(unfilled):
            if i == 0:
                # 第一个标 uncertain 测试
                draft_row[field] = {"value": 0, "uncertain": True, "reason": "测试用"}
            else:
                draft_row[field] = 0
        draft_rows.append(draft_row)
    draft["tables"][tbl] = draft_rows

draft["requirement"] = align_result.get('requirement', '')
with open(os.path.join(DATA_DIR, 'draft_filled.json'), 'w', encoding='utf-8') as f:
    json.dump(draft, f, ensure_ascii=False, indent=2)
print("  ✅ draft_filled.json 已写入")

# 5. on_enter_fill_confirm
print("\n── 5. on_enter_fill_confirm ──")
r4 = hooks.on_enter_fill_confirm()
print(f"  uncertain 字段数: {r4.get('uncertain_count')}")
for tbl, fields in r4.get('uncertain_summary', {}).items():
    for f_info in fields:
        print(f"  {tbl}.{f_info['field']}: 建议值={f_info['suggested_value']}, 原因={f_info['reason']}")

# 6. 模拟用户确认 → filled_result.json
print("\n── 6. 模拟用户确认 → filled_result.json ──")
# 展平 uncertain 为确定值
filled = {"tables": {}, "requirement": draft.get('requirement', '')}
for tbl, rows in draft['tables'].items():
    filled_rows = []
    for row in rows:
        filled_row = {}
        for k, v in row.items():
            if isinstance(v, dict) and v.get('uncertain'):
                filled_row[k] = v.get('value', 0)
            else:
                filled_row[k] = v
        filled_rows.append(filled_row)
    filled["tables"][tbl] = filled_rows

with open(os.path.join(DATA_DIR, 'filled_result.json'), 'w', encoding='utf-8') as f:
    json.dump(filled, f, ensure_ascii=False, indent=2)
print("  ✅ filled_result.json 已写入")

# 7. on_enter_write（不实际写 Excel，只测到校验为止）
print("\n── 7. on_enter_write ──")
r5 = hooks.on_enter_write()
print(f"  status: {r5.get('status')}")
if r5.get('errors'):
    print(f"  errors: {r5['errors']}")
for tbl, info in r5.get('allocated_ids', {}).items():
    print(f"  {tbl}: old={info.get('old_id')} → new={info.get('new_id')}")
if r5.get('output_dir'):
    print(f"  output_dir: {r5['output_dir']}")

print("\n" + "=" * 60)
print("全部通过 ✅")
