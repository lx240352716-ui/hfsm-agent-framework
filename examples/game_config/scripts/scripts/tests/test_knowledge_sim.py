# -*- coding: utf-8 -*-
"""
验证 L1 数值策划知识库重构：
1. 每个状态的 hook 能正确加载 requirement_structures.md
2. 加载的知识文件内容包含关键信息（树形结构、铁规等）
3. 模拟清明节礼包完整流程 6 状态自循环

运行: python scripts/tests/test_knowledge_sim.py
"""
import sys, os, json

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, 'scripts', 'core'))
sys.path.insert(0, os.path.join(BASE, 'agents', 'numerical_memory', 'process'))

import numerical_hooks as hooks

DATA_DIR = os.path.join(BASE, 'agents', 'numerical_memory', 'data')
COORD_DATA = os.path.join(BASE, 'agents', 'coordinator_memory', 'data')
KNOWLEDGE_DIR = os.path.join(BASE, 'agents', 'numerical_memory', 'knowledge')

errors = []
passed = 0

def check(name, condition, detail=""):
    global passed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        msg = f"  ❌ {name}" + (f" — {detail}" if detail else "")
        print(msg)
        errors.append(name)

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(COORD_DATA, exist_ok=True)

# ────────────────────────────────────────────
# 预检: requirement_structures.md 存在且内容正确
# ────────────────────────────────────────────
print("=" * 60)
print("预检: requirement_structures.md")
print("=" * 60)

rs_path = os.path.join(KNOWLEDGE_DIR, 'requirement_structures.md')
check("文件存在", os.path.exists(rs_path))

with open(rs_path, 'r', encoding='utf-8') as f:
    rs_content = f.read()

check("包含礼包结构", "礼包类" in rs_content)
check("包含 Item → DropGroup 关联", "Item" in rs_content and "_DropGroup" in rs_content)
check("包含 resourceDes 字段关联", "resourceDes" in rs_content)
check("包含树形确认模板", "📦" in rs_content)
check("包含叶子节点状态标记", "✓已存在" in rs_content)

# ────────────────────────────────────────────
# 预检: fill/rules.md 铁规
# ────────────────────────────────────────────
print("\n" + "=" * 60)
print("预检: fill/rules.md 铁规")
print("=" * 60)

with open(os.path.join(KNOWLEDGE_DIR, 'fill', 'rules.md'), 'r', encoding='utf-8') as f:
    fill_rules = f.read()

check("包含树形隶属格式铁规", "树形隶属格式" in fill_rules)
check("包含叶子节点展示名字铁规", "叶子节点展示名字" in fill_rules)
check("包含数量必须可见铁规", "数量必须可见" in fill_rules)
check("包含 _ref_id 必须铁规", "每行必须有" in fill_rules and "_ref_id" in fill_rules)
check("引用 requirement_structures.md", "requirement_structures.md" in fill_rules)

# ────────────────────────────────────────────
# 预检: locate/rules.md 铁规
# ────────────────────────────────────────────
print("\n" + "=" * 60)
print("预检: locate/rules.md 铁规")
print("=" * 60)

with open(os.path.join(KNOWLEDGE_DIR, 'locate', 'rules.md'), 'r', encoding='utf-8') as f:
    locate_rules = f.read()

check("包含 _ref_id 必须铁规", "不支持从零建行" in locate_rules)

# ────────────────────────────────────────────
# 预检: fill/examples.md 无具体 ID
# ────────────────────────────────────────────
print("\n" + "=" * 60)
print("预检: fill/examples.md 清理")
print("=" * 60)

with open(os.path.join(KNOWLEDGE_DIR, 'fill', 'examples.md'), 'r', encoding='utf-8') as f:
    fill_examples = f.read()

check("无具体 ID 619021", "619021" not in fill_examples)
check("无具体 ID 220010", "220010" not in fill_examples)
check("包含树形结构展示", "📦" in fill_examples)

# ────────────────────────────────────────────
# 预检: system_activity.md 包含礼包
# ────────────────────────────────────────────
print("\n" + "=" * 60)
print("预检: system_activity.md")
print("=" * 60)

with open(os.path.join(KNOWLEDGE_DIR, 'system_activity.md'), 'r', encoding='utf-8') as f:
    activity = f.read()

check("包含礼包描述", "礼包" in activity)
check("引用 requirement_structures.md", "requirement_structures.md" in activity)

# ────────────────────────────────────────────
# 预检: workflow 知识映射
# ────────────────────────────────────────────
print("\n" + "=" * 60)
print("预检: numerical_workflow.py 知识映射")
print("=" * 60)

import numerical_workflow as wf
check("split 知识含 requirement_structures.md",
      "requirement_structures.md" in wf.knowledge.get("split", []))
check("locate 知识含 requirement_structures.md",
      "requirement_structures.md" in wf.knowledge.get("locate", []))

# ────────────────────────────────────────────
# 模拟 6 状态流程
# ────────────────────────────────────────────
ensure_data_dir()

# 备份 examples.md（hooks 会追加测试数据，结束后恢复）
_examples_path = os.path.join(KNOWLEDGE_DIR, 'numerical_examples.md')
_examples_backup = open(_examples_path, 'r', encoding='utf-8').read() if os.path.exists(_examples_path) else None

print("\n" + "=" * 60)
print("模拟 6 状态流程: 清明节礼包")
print("=" * 60)

# ── Step 0: coordinator output ──
with open(os.path.join(COORD_DATA, 'output.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "_schema": "coordinator_output",
        "task_id": "test_knowledge",
        "requirement": "上架清明节礼包，含3种觉醒徽章，售价100蓝钻，限购5次",
        "dispatch": {
            "numerical": {
                "requirement": "上架清明节礼包，含3种觉醒徽章，售价100蓝钻，限购5次",
                "modules": ["道具注册", "掉落配置", "商城上架"],
            }
        }
    }, f, ensure_ascii=False, indent=2)

# ── Step 1: match ──
print("\n【1. match】")
r = hooks.on_enter_match()
knowledge_files = [k.get('file', '') for k in r.get('knowledge', [])]
check("match 返回 knowledge", len(knowledge_files) > 0)
check("match 有上游需求", r.get('upstream') is not None)
# 验证 pending 初始化
pending = json.load(open(os.path.join(DATA_DIR, 'pending_examples.json'), encoding='utf-8'))
check("match 初始化 pending（entries 为空）", pending.get('entries') == [])
print(f"  知识文件: {knowledge_files}")

# 模拟 LLM 写 match_result
with open(os.path.join(DATA_DIR, 'match_result.json'), 'w', encoding='utf-8') as f:
    json.dump({"systems": ["activity"], "reference_case": "清明节礼包"}, f, ensure_ascii=False)

# ── Step 2: split ──
print("\n【2. split】")
r = hooks.on_enter_split()
knowledge_files = [k.get('file', '') for k in r.get('knowledge', [])]
check("split 返回 knowledge", len(knowledge_files) > 0)
# 注意: split hook 通过 _load_md 动态加载，knowledge_files 来自 hook 返回
print(f"  知识文件: {knowledge_files}")

# 模拟 LLM 拆模块
with open(os.path.join(DATA_DIR, 'split_result.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "requirement": "上架清明节礼包，含3种觉醒徽章，售价100蓝钻，限购5次",
        "modules": [
            {"name": "道具注册", "system": "activity", "description": "礼包 Item"},
            {"name": "掉落配置", "system": "activity", "description": "3个掉落组"},
            {"name": "商城上架", "system": "activity", "description": "商城售卖配置"},
        ]
    }, f, ensure_ascii=False, indent=2)

# ── Step 3: confirm ──
print("\n【3. confirm】")
r = hooks.on_exit_confirm()
check("confirm 保存成功", r.get('status') == 'OK')
check("confirmed_split.json 存在",
      os.path.exists(os.path.join(DATA_DIR, 'confirmed_split.json')))
# 验证 pending 被追加、examples.md 未被修改
pending = json.load(open(os.path.join(DATA_DIR, 'pending_examples.json'), encoding='utf-8'))
check("confirm 追加了 pending entry", len(pending.get('entries', [])) == 1)
current_examples = open(os.path.join(KNOWLEDGE_DIR, 'numerical_examples.md'), 'r', encoding='utf-8').read()
check("confirm 未修改 examples.md", current_examples == _examples_backup)

# ── Step 4: locate ──
print("\n【4. locate】")
r = hooks.on_enter_locate()
knowledge_files = [k.get('file', '') for k in r.get('knowledge', [])]
check("locate 返回 knowledge", len(knowledge_files) > 0)
check("locate 知识含 requirement_structures.md",
      any('requirement_structures' in f for f in knowledge_files),
      f"实际: {knowledge_files}")
check("locate 有候选表", len(r.get('candidates', {})) > 0)
print(f"  知识文件: {knowledge_files}")
print(f"  候选表: {r.get('candidates', {})}")

# 模拟 LLM 写 locate_result（带 _ref_id + search_keywords）
with open(os.path.join(DATA_DIR, 'locate_result.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "modules": [
            {
                "name": "道具注册", "table": "Item",
                "search_keywords": ["觉醒徽章", "礼盒"],
                "fields": [
                    {"cn": "道具ID", "en": "id", "type": "auto"},
                    {"cn": "道具名称", "en": "name", "type": "input"},
                    {"cn": "resourceDes", "en": "resourceDes", "type": "input"},
                ]
            },
            {
                "name": "掉落配置1", "table": "_DropGroup",
                "_ref_id": "220010",
                "fields": [
                    {"cn": "ID", "en": "id", "type": "auto"},
                    {"cn": "掉落物", "en": "param", "type": "input"},
                ]
            },
            {
                "name": "掉落配置2", "table": "_DropGroup",
                "_ref_id": "220011",
                "fields": []
            },
            {
                "name": "掉落配置3", "table": "_DropGroup",
                "_ref_id": "220012",
                "fields": []
            },
            {
                "name": "商城上架", "table": "_ShopItem",
                "_ref_id": "78",
                "fields": [
                    {"cn": "商品ID", "en": "id", "type": "auto"},
                    {"cn": "售价", "en": "currencyInfo", "type": "input"},
                    {"cn": "限购", "en": "limitData", "type": "input"},
                ]
            },
        ]
    }, f, ensure_ascii=False, indent=2)

# on_exit_locate — 修改文件而非返回值
hooks.on_exit_locate()
updated = json.load(open(os.path.join(DATA_DIR, 'locate_result.json'), encoding='utf-8'))
has_ref_status = all(m.get('ref_status') for m in updated.get('modules', []))
check("on_exit_locate 更新了 ref_status", has_ref_status)
# 有 _ref_id 的模块应标 found
dg_modules = [m for m in updated['modules'] if m.get('_ref_id')]
check("有 _ref_id 的模块标 found",
      all(m.get('ref_status') == 'found' for m in dg_modules))
print(f"  ref_status: {[(m['name'], m.get('ref_status')) for m in updated['modules']]}")

# ── Step 5: fill ──
print("\n【5. fill】")
r = hooks.on_enter_fill()
knowledge_files = [k.get('file', '') for k in r.get('knowledge', [])]
check("fill 返回 knowledge", len(knowledge_files) > 0)
check("fill 知识含 requirement_structures.md",
      any('requirement_structures' in f for f in knowledge_files),
      f"实际: {knowledge_files}")
check("fill 有 locate_result", r.get('locate_result') is not None)
# 树形规则在 fill/rules.md 知识里，不需要重复在 instruction 里
knowledge_content = ' '.join(k.get('content', '') for k in r.get('knowledge', []))
check("fill 知识内容含树形铁规", "树形隶属格式" in knowledge_content)
print(f"  知识文件: {knowledge_files}")

# 模拟用户确认后写 filled.json
with open(os.path.join(DATA_DIR, 'filled.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "requirement": "上架清明节礼包",
        "tables": {
            "Item": [{
                "_ref_id": "619021",
                "_note": "复制619021，改名为清明节礼包，resourceDes指向新DropGroup",
                "_overrides": {}
            }],
            "_DropGroup": [
                {"_ref_id": "220010", "_note": "掉落沙鳄鱼觉醒徽章"},
                {"_ref_id": "220011", "_note": "掉落艾斯觉醒徽章"},
                {"_ref_id": "220012", "_note": "掉落艾尼路觉醒徽章"},
            ],
            "_ShopItem": [{
                "_ref_id": "78",
                "_note": "商城售卖清明节礼包",
                "_overrides": {"currencyInfo": "1,0,100", "limitData": "2,5,0,0,0"}
            }]
        }
    }, f, ensure_ascii=False, indent=2)

# ── Step 6: output ──
print("\n【6. output】")
r = hooks.on_enter_output()
knowledge_files = [k.get('file', '') for k in r.get('knowledge', [])]
check("output 返回 knowledge", len(knowledge_files) > 0)
check("output 有 filled_data", r.get('filled_data') is not None)
check("output 有 allocated_ids", r.get('allocated_ids') is not None)
check("output 有 cn_en_maps", r.get('cn_en_maps') is not None)
print(f"  allocated_ids: {json.dumps(r.get('allocated_ids', {}), ensure_ascii=False, indent=2)}")

# 模拟写 output.json
with open(os.path.join(DATA_DIR, 'output.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "_schema": "numerical_output",
        "task_id": "test_knowledge",
        "requirement": "上架清明节礼包",
        "tables": r['filled_data']['tables']
    }, f, ensure_ascii=False, indent=2)

r_exit = hooks.on_exit_output()
check("on_exit_output 成功", r_exit.get('status') == 'OK')
print(f"  验证: {r_exit}")

# ────────────────────────────────────────────
# 清理测试数据
# ────────────────────────────────────────────
print("\n" + "=" * 60)
print("清理测试中间数据...")
for f in ['match_result.json', 'split_result.json', 'confirmed_split.json',
           'locate_result.json', 'filled.json', 'output.json', 'pending_examples.json']:
    p = os.path.join(DATA_DIR, f)
    if os.path.exists(p):
        os.remove(p)
        print(f"  删除 {f}")

coord_out = os.path.join(COORD_DATA, 'output.json')
if os.path.exists(coord_out):
    os.remove(coord_out)
    print("  删除 coordinator output.json")

# 恢复 numerical_examples.md（on_exit_confirm + on_exit_output 会追加测试数据）
if _examples_backup is not None:
    with open(os.path.join(KNOWLEDGE_DIR, 'numerical_examples.md'), 'w', encoding='utf-8') as f:
        f.write(_examples_backup)
    print("  恢复 numerical_examples.md（清除测试追加的数据）")

# ────────────────────────────────────────────
# 汇总
# ────────────────────────────────────────────
print("\n" + "=" * 60)
total = passed + len(errors)
print(f"结果: {passed}/{total} 通过")
if errors:
    print(f"失败: {errors}")
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)
