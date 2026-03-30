# -*- coding: utf-8 -*-
"""
测试状态机自动触发 executor hooks
模拟：design_complete → 进入 executor → 自动调 on_enter_execute
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from constants import AGENTS_DIR

from hfsm_registry import build_hfsm

print("=" * 60)
print("测试：状态机自动进入 executor + 自动触发 hooks")
print("=" * 60)

# 1. 构建 HFSM
model = build_hfsm()
print(f"\n初始状态: {model.state}")

# 2. 检查 executor hooks 是否被绑定
bound = []
for attr in dir(model):
    if 'executor' in attr and ('on_enter' in attr or 'on_exit' in attr):
        bound.append(attr)
print(f"\n已绑定的 executor 回调:")
for b in bound:
    print(f"  {b}")

if not bound:
    print("  ❌ 没有绑定任何回调！")
    sys.exit(1)

# 3. 模拟走到 executor
# 先模拟 coordinator 完成 → dispatch → design → numerical 完成 → executor
print(f"\n── 模拟状态转移 ──")

# 设置 dispatch 数据
model.design_dispatch = {"numerical": {"tables": ["Item"]}}
model.design_roles = ["numerical"]
model.design_queue = []

# coordinator → design（需要走 coordinator 内部状态）
# 直接设置状态到 design_router
model.state = 'design_router'
print(f"  跳到: {model.state}")

# 设置 is_design_done 条件
model._design_done = True

# design_complete → executor
print(f"\n── 触发 design_complete ──")
model.design_complete()
print(f"  当前状态: {model.state}")

# 4. 检查 on_enter_execute 是否被自动调用
# 查看 execute_result.json 是否生成
EXEC_DATA = os.path.join(AGENTS_DIR, 'executor_memory', 'data')
result_path = os.path.join(EXEC_DATA, 'execute_result.json')

if os.path.exists(result_path):
    result = json.load(open(result_path, encoding='utf-8'))
    tables = result.get('tables', {})
    unfilled = result.get('unfilled_fields', {})
    
    print(f"\n── on_enter_execute 自动触发结果 ──")
    print(f"  requirement: {result.get('requirement', '')}")
    for tbl, rows in tables.items():
        print(f"  {tbl}: {len(rows)} 行, {len(rows[0]) if rows else 0} 个字段")
        # 显示前5个字段和值
        if rows:
            for k, v in list(rows[0].items())[:5]:
                print(f"    {k}: {v}")
    print(f"\n  未填字段:")
    for tbl, fields in unfilled.items():
        print(f"    {tbl}: {len(fields)} 个 — {fields[:3]}...")
    
    print(f"\n✅ 状态机自动触发 on_enter_execute 成功！")
else:
    print(f"\n  ❌ execute_result.json 未生成，hooks 没有被自动调用")

print(f"\n最终状态: {model.state}")
