# -*- coding: utf-8 -*-
"""测试 execute → align 两步"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'executor_memory', 'process'))
import executor_hooks as hooks

print("=" * 60)
print("测试：execute → align")
print("=" * 60)

# Step 1: execute（只读上游）
print("\n▶ on_enter_execute")
r1 = hooks.on_enter_execute()
print(f"  status: {r1['status']}")
print(f"  tables: {r1['tables']}")
print(f"  requirement: {r1['requirement']}")

# Step 2: align（读 Row6 + 对比）
print("\n▶ on_enter_align")
r2 = hooks.on_enter_align()
print(f"  status: {r2['status']}")
if r2.get('errors'):
    for e in r2['errors']:
        print(f"  ❌ {e}")

for tbl, report in r2.get('align_report', {}).items():
    print(f"\n  [{tbl}]  Row6={report['row6_total']} 个字段")
    print(f"    已填: {report['filled']}")
    print(f"    待填: {report['unfilled']}")
    print(f"    多余: {report['extra']}")
    if report.get('unfilled_fields'):
        print(f"    待填字段: {report['unfilled_fields']}")

print("\n" + "=" * 60)
