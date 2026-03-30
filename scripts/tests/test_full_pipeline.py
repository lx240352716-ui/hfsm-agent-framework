# -*- coding: utf-8 -*-
"""
真实全链路测试：L0 → L1 数值策划 → L2 执行策划 → L3 QA
需求：清明节礼包（仿觉醒徽章礼盒·沙鳄鱼）
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'numerical_memory', 'process'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'executor_memory', 'process'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'qa_memory', 'process'))
from constants import AGENTS_DIR
from table_reader import max_id, get_columns

t0 = time.time()

# ══════════════════════════════════════════════
#  初始状态
# ══════════════════════════════════════════════
print("=" * 60)
print("  初始状态（源表清洁确认）")
print("=" * 60)
for tbl in ['Item', '_DropGroup', '_ShopItem']:
    col_info = get_columns(tbl)
    mid = max_id(tbl, col_info['cn'][0])
    print(f"  {tbl}: max_id = {mid}")

# ══════════════════════════════════════════════
#  L0 主策划：parse + dispatch（模拟）
# ══════════════════════════════════════════════
print("\n" + "=" * 60)
print("  L0 主策划 — parse & dispatch")
print("=" * 60)

# 写入 coordinator output → numerical input
coordinator_output = {
    "_schema": "coordinator_output",
    "requirement": "清明节礼包（仿觉醒徽章礼盒·沙鳄鱼）",
    "requirement_type": "新礼包",
    "modules": ["道具", "掉落", "商店"],
    "reference": "觉醒徽章礼盒（沙·鳄鱼）619021 → 掉落组220010",
    "dispatch_to": "numerical",
}

coord_data_dir = os.path.join(AGENTS_DIR, 'coordinator_memory', 'data')
os.makedirs(coord_data_dir, exist_ok=True)
with open(os.path.join(coord_data_dir, 'output.json'), 'w', encoding='utf-8') as f:
    json.dump(coordinator_output, f, ensure_ascii=False, indent=2)

print(f"  需求: {coordinator_output['requirement']}")
print(f"  参考: {coordinator_output['reference']}")
print(f"  模块: {coordinator_output['modules']}")
print(f"  派发: → L1 numerical")

# ══════════════════════════════════════════════
#  L1 数值策划（6 状态）
# ══════════════════════════════════════════════
import numerical_hooks as l1

print("\n" + "=" * 60)
print("  L1 数值策划")
print("=" * 60)

# 先写入 numerical input
num_data_dir = os.path.join(AGENTS_DIR, 'numerical_memory', 'data')
os.makedirs(num_data_dir, exist_ok=True)

num_input = {
    "_schema": "numerical_input",
    "task_id": "qingming_gift_001",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "from": "coordinator",
    "requirement": {
        "raw_text": "制作清明节礼包，参考觉醒徽章礼盒（沙·鳄鱼）619021",
        "requirement_type": "新礼包",
        "related_tables": ["Item", "_DropGroup", "_ShopItem"],
        "reference_values": {"reference_item": "619021", "reference_drop": "220010"},
        "context": "清明节活动礼包，仿照觉醒徽章礼盒·沙鳄鱼的配置"
    }
}
with open(os.path.join(num_data_dir, 'input.json'), 'w', encoding='utf-8') as f:
    json.dump(num_input, f, ensure_ascii=False, indent=2)

print("\n[L1-1/6] match")
r = l1.on_enter_match()
print(f"  status={r.get('status', 'OK')}")

print("\n[L1-2/6] split")
r = l1.on_enter_split()
print(f"  modules: {list(r.get('modules', {}).keys()) if isinstance(r.get('modules'), dict) else r.get('modules', [])}")

# confirm — 自动确认
print("\n[L1-3/6] confirm (自动)")
# 写 confirmed_split.json
split_data = json.load(open(os.path.join(num_data_dir, 'split_result.json'), encoding='utf-8'))
with open(os.path.join(num_data_dir, 'confirmed_split.json'), 'w', encoding='utf-8') as f:
    json.dump(split_data, f, ensure_ascii=False, indent=2)
print("  ✅ 自动确认")

print("\n[L1-4/6] locate")
r = l1.on_enter_locate()
print(f"  candidates: {list(r.get('candidates', {}).keys())}")

# fill — 写 filled.json（从 locate_result 自动填充参考值）
print("\n[L1-5/6] fill (参考行自动填充)")
locate_data = json.load(open(os.path.join(num_data_dir, 'locate_result.json'), encoding='utf-8'))
# locate_result 里已有参考数据，直接透传
with open(os.path.join(num_data_dir, 'filled.json'), 'w', encoding='utf-8') as f:
    json.dump(locate_data, f, ensure_ascii=False, indent=2)
print("  ✅ 使用参考行数据")

print("\n[L1-6/6] output")
r = l1.on_enter_output()
print(f"  status={r.get('status', 'OK')}")
print(f"  tables: {list(r.get('output', {}).get('tables', {}).keys()) if r.get('output') else '?'}")

# ══════════════════════════════════════════════
#  L2 执行策划（5 状态）
# ══════════════════════════════════════════════
import executor_hooks as l2

print("\n" + "=" * 60)
print("  L2 执行策划")
print("=" * 60)

print("\n[L2-1/5] execute")
r = l2.on_enter_execute()
print(f"  status={r['status']}, tables={r.get('tables')}")

print("\n[L2-2/5] align")
r = l2.on_enter_align()
print(f"  status={r['status']}")

print("\n[L2-3/5] fill")
r = l2.on_enter_fill()
print(f"  ref_rows: {list(r.get('reference_rows', {}).keys())}")

print("\n[L2-4/5] fill_confirm (自动)")
r = l2.on_enter_fill_confirm()
print(f"  uncertain_count={r.get('uncertain_count', 0)}")

print("\n[L2-5/5] write")
t_w = time.time()
r = l2.on_enter_write()
print(f"  status={r['status']}, time={time.time()-t_w:.2f}s")
print(f"  output_dir={r.get('output_dir')}")
for tbl, cnt in r.get('results', {}).items():
    print(f"  {tbl}: {cnt} rows")

# ══════════════════════════════════════════════
#  L3 QA Agent（3 状态，黑盒）
# ══════════════════════════════════════════════
from qa_hooks import on_enter_qa, on_enter_merge, on_enter_done

print("\n" + "=" * 60)
print("  L3 QA Agent")
print("=" * 60)

print("\n[L3-1/3] qa")
t_qa = time.time()
r_qa = on_enter_qa()
print(f"\n  status={r_qa['status']}, time={time.time()-t_qa:.2f}s")

if r_qa['status'] == 'QA_FAILED':
    print(f"\n  ❌ QA 不通过！流程停止。")
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
#  验证
# ══════════════════════════════════════════════
print("\n" + "=" * 60)
print("  最终验证")
print("=" * 60)

for tbl in ['Item', '_DropGroup', '_ShopItem']:
    col_info = get_columns(tbl)
    mid = max_id(tbl, col_info['cn'][0])
    print(f"  {tbl}: max_id = {mid}")

print(f"\n  总耗时: {time.time()-t0:.2f}s")
print("  🎉 L0→L1→L2→L3 全链路真实执行完成！")
