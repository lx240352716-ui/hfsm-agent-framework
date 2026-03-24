# -*- coding: utf-8 -*-
"""
测试 P11: review + done
前置条件：先 quick_cleanup + run_l2l3 确保有 l3_done.json
本脚本只跑 review → done 两步
"""
import sys, os, glob
sys.path.insert(0, os.path.join('scripts', 'core'))
sys.path.insert(0, os.path.join('agents', 'coordinator_memory', 'process'))

import coordinator_hooks

print("=" * 60)
print("  P11 测试: review → done")
print("=" * 60)

# ── 1. review ──
print("\n[1/3] L0 review")

result = coordinator_hooks.on_enter_review()
print(f"  status = {result.get('status')}")

if result.get('status') == 'SKIP':
    print(f"  ⚠️ {result.get('reason')} — 请先跑 run_l2l3.py")
    sys.exit(1)

if result.get('report'):
    print()
    print(result['report'])

if result.get('anomalies'):
    print(f"\n  异常: {len(result['anomalies'])} 项")
    for a in result['anomalies']:
        print(f"    {a}")
else:
    print("\n  ✅ 无异常")

# ── 2. done / cleanup ──
print("\n" + "=" * 60)
print("  [2/3] L0 done (cleanup)")
print("=" * 60)

done_result = coordinator_hooks.on_enter_done()
print(f"\n  status = {done_result.get('status')}")
print(f"  message = {done_result.get('message')}")
print(f"  deleted {len(done_result.get('deleted', []))} files:")
for f in done_result.get('deleted', []):
    print(f"    - {f}")

# ── 3. 验证 ──
print("\n" + "=" * 60)
print("  [3/3] 验证")
print("=" * 60)

remaining = []
for pattern in [
    'agents/numerical_memory/data/*.json',
    'agents/executor_memory/data/*.json',
    'agents/coordinator_memory/data/*.json',
    'agents/qa_memory/*.json',
]:
    remaining.extend(glob.glob(pattern))

if remaining:
    print(f"\n  ❌ 仍有 {len(remaining)} 个 JSON 未清理:")
    for f in remaining:
        print(f"    {f}")
else:
    print(f"\n  ✅ 所有中间 JSON 已清理")

output_dirs = os.listdir('output') if os.path.isdir('output') else []
print(f"  ✅ output/ 保留 {len(output_dirs)} 个任务目录")

print(f"\n  🎉 P11 测试完成！")
