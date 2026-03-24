# -*- coding: utf-8 -*-
"""测试新 hooks 功能：locate 自动搜表 + fill + output max_id"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'numerical_memory', 'process'))
import numerical_hooks as hooks

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents', 'numerical_memory', 'data')

print("=" * 60)
print("测试新 hooks 功能")
print("=" * 60)

# 1. 测试 _search_table
print("\n── _search_table ──")
for kw in ['Item', 'DropGroup', 'ShopItem', 'Buff']:
    results = hooks._search_table(kw)
    print(f"  搜 '{kw}': {len(results)} 个 → {[r[0] for r in results[:3]]}...")

# 2. 测试 _extract_table_keywords
print("\n── _extract_table_keywords ──")
for name in ['道具注册', '掉落配置', '商城上架', '装备精炼', '抽卡配置']:
    keywords = hooks._extract_table_keywords(name)
    print(f"  '{name}' → {keywords}")

# 3. 测试 on_enter_locate 自动搜索候选表
print("\n── on_enter_locate (candidates 自动搜索) ──")
# 准备 confirmed_split.json
with open(os.path.join(DATA, 'confirmed_split.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "requirement": "清明节礼包",
        "modules": [
            {"name": "道具注册", "system": "activity"},
            {"name": "掉落配置", "system": "activity"},
            {"name": "商城上架", "system": "activity"},
        ]
    }, f, ensure_ascii=False, indent=2)

r = hooks.on_enter_locate()
for mod_name, cands in r['candidates'].items():
    names = [c['table'] for c in cands[:5]]
    print(f"  {mod_name}: {names}")

# 4. 测试 on_enter_fill
print("\n── on_enter_fill ──")
with open(os.path.join(DATA, 'locate_result.json'), 'w', encoding='utf-8') as f:
    json.dump({"modules": [{"name": "道具注册", "table": "Item", "fields": ["id", "name"]}]}, f)
r = hooks.on_enter_fill()
print(f"  status: {r.get('status', 'OK')}")
print(f"  modules: {len(r['locate_result']['modules'])}")

# 5. 测试 on_enter_output max_id
print("\n── on_enter_output (max_id 自动分配) ──")
with open(os.path.join(DATA, 'filled.json'), 'w', encoding='utf-8') as f:
    json.dump({"tables": {"Item": [], "_DropGroup": [], "_ShopItem": []}}, f)
r = hooks.on_enter_output()
for tbl, info in r['allocated_ids'].items():
    print(f"  {tbl}: max={info.get('max_id')}, next={info.get('next_id')}")

print("\n" + "=" * 60)
print("全部通过 ✅")
