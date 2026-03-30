# -*- coding: utf-8 -*-
"""真实数据测试：直接调 L3 QA hooks（不用测试脚本）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'qa_memory', 'process'))

from qa_hooks import on_enter_qa, on_enter_merge, on_enter_done
import json

print("=" * 60)
print("  L3 QA Agent — 真实数据测试")
print("  数据来源: executor_done.json（上轮 L2 产出）")
print("=" * 60)

# Step 1: QA
print("\n[L3-1/3] on_enter_qa()")
r_qa = on_enter_qa()
print(f"\n  返回: status={r_qa['status']}, qa_result={r_qa.get('qa_result')}")

if r_qa['status'] == 'QA_FAILED':
    print(f"\n  ❌ QA 不通过！")
    print(f"  error_log: {r_qa.get('error_log', '')[:200]}")
    print(f"  rollback_path: {r_qa.get('rollback_path')}")
    print(f"\n  真实流程中这里会通知用户，由用户决定打回还是忽略。")
    print(f"  本次测试跳过 merge/done。")
elif r_qa['status'] == 'OK':
    print(f"\n  ✅ QA 通过！继续 merge...")

    # Step 2: Merge
    print("\n[L3-2/3] on_enter_merge()")
    r_merge = on_enter_merge()
    print(f"\n  返回: status={r_merge['status']}")
    for tbl, info in r_merge.get('merge', {}).items():
        print(f"  {tbl}: {info}")

    # Step 3: Done
    print("\n[L3-3/3] on_enter_done()")
    r_done = on_enter_done()
    print(f"\n  返回: status={r_done['status']}")
else:
    print(f"\n  ⚠️ 异常: {json.dumps(r_qa, ensure_ascii=False, indent=2)}")
