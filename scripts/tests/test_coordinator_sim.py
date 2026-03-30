# -*- coding: utf-8 -*-
"""
模拟主策划完整流程（v3 — parameterless hooks）：
需求："新增一个新角色蜂巢岛卡普，帮我配置所有的数据"
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents', 'coordinator_memory', 'process'))
from constants import AGENTS_DIR

from hfsm_registry import build_hfsm
import coordinator_hooks as hooks

DATA_DIR = os.path.join(AGENTS_DIR, 'coordinator_memory', 'data')

print("=" * 60)
print("模拟主策划流程 v3")
print("需求: 新增一个新角色蜂巢岛卡普")
print("=" * 60)

# ── Step 0: 启动 HFSM ──
model = build_hfsm()
print(f"\n【启动】状态: {model.state}")

# ── Step 1: parse ──
print("\n" + "─" * 60)
print("【Step 1: parse — 理解用户需求】")
result = hooks.on_enter_parse()
print(f"  加载: {[k['file'] for k in result['knowledge']]}")
print(f"  LLM 输出: 需求类型=新角色")

model.parse_done()
print(f"  → {model.state}")

# ── Step 2: split_modules ──
print("\n" + "─" * 60)
print("【Step 2: split_modules — 拆分功能模块】")
result = hooks.on_enter_split_modules()
print(f"  加载: {[k['file'] for k in result['knowledge']]}")
print("  LLM 拆分: combat[技能,被动] + numerical[属性,成长,抽卡]")

model.split_done()
print(f"  → {model.state}")

# ── Step 3: user_confirm ──
print("\n" + "─" * 60)
print("【Step 3: user_confirm — 用户确认】")
print("  用户说: '确认'")

# 模拟 LLM 写 confirmed.json（实际运行时 LLM 用工具写）
confirmed_data = {
    "requirement": "新增新角色蜂巢岛卡普",
    "requirement_type": "新角色",
    "modules": {
        "combat": ["技能", "被动"],
        "numerical": ["角色属性", "数值成长", "抽卡"],
    }
}
with open(os.path.join(DATA_DIR, 'confirmed.json'), 'w', encoding='utf-8') as f:
    json.dump(confirmed_data, f, ensure_ascii=False, indent=2)
print("  ✏️  LLM 写入 confirmed.json")

# on_exit 从文件读（无参数）
save_result = hooks.on_exit_user_confirm()
print(f"  ✏️  on_exit 追加到 examples.md")

model.user_confirmed()
print(f"  → {model.state}")

# ── Step 4: dispatch ──
print("\n" + "─" * 60)
print("【Step 4: dispatch — 派发给下游】")

# on_enter 从文件读（无参数）
dispatch_result = hooks.on_enter_dispatch()

print(f"\n  派发结果:")
for role, task in dispatch_result['dispatch'].items():
    print(f"    → {role}: {task['modules']}")

model.dispatched_tasks = dispatch_result['dispatch']
model.dispatch()
print(f"\n  → {model.state}")

# ── 展示最终产出 ──
print("\n" + "=" * 60)
print("【output.json】")
print("=" * 60)
with open(dispatch_result['output_file'], 'r', encoding='utf-8') as f:
    print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
