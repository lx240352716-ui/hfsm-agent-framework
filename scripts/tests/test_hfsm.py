# -*- coding: utf-8 -*-
"""HFSM 测试 — 数据驱动 design router + 多角色队列"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from constants import AGENTS_DIR

COORDINATOR_DATA = os.path.join(AGENTS_DIR, 'coordinator_memory', 'data')


def _write_output(dispatch):
    """模拟 coordinator 写 output.json"""
    with open(os.path.join(COORDINATOR_DATA, 'output.json'), 'w', encoding='utf-8') as f:
        json.dump({"_schema": "coordinator_output", "requirement": "test", "dispatch": dispatch}, f)


def test_combat_then_numerical():
    """两个 Agent：dispatch → combat → agent_done → router → numerical → agent_done → router → executor"""
    from hfsm_registry import build_hfsm
    model = build_hfsm()
    model.parse_done(); model.split_done(); model.user_confirmed()

    _write_output({
        "combat": {"modules": ["技能"]},
        "numerical": {"modules": ["属性"]},
    })
    model.dispatched_tasks = True
    model.dispatch()
    # auto: router → combat
    assert 'design_combat' in model.state
    print("  ✅ 自动路由 → combat")

    # combat 做完
    model.split_done(); model.categorize_done(); model.translate_done()
    # agent_done → router → _route_next → numerical
    model.agent_done()
    assert 'design_numerical' in model.state
    print("  ✅ agent_done → router → numerical")

    # numerical 做完
    model.match_done(); model.split_done(); model.confirmed(); model.locate_done(); model.fill_done()
    # agent_done → router → _route_next → 队列空 → design_complete → executor
    model.agent_done()
    assert 'executor' in model.state
    print("  ✅ agent_done → router → 队列空 → executor")


def test_numerical_only():
    """只有 numerical：dispatch → numerical → agent_done → executor"""
    from hfsm_registry import build_hfsm
    model = build_hfsm()
    model.parse_done(); model.split_done(); model.user_confirmed()

    _write_output({"numerical": {"modules": ["定价"]}})
    model.dispatched_tasks = True
    model.dispatch()
    assert 'design_numerical' in model.state
    print("  ✅ 跳过 combat → numerical")

    model.match_done(); model.split_done(); model.confirmed(); model.locate_done(); model.fill_done()
    model.agent_done()
    assert 'executor' in model.state
    print("  ✅ agent_done → executor")


def test_combat_only():
    """只有 combat：dispatch → combat → agent_done → executor"""
    from hfsm_registry import build_hfsm
    model = build_hfsm()
    model.parse_done(); model.split_done(); model.user_confirmed()

    _write_output({"combat": {"modules": ["被动技能"]}})
    model.dispatched_tasks = True
    model.dispatch()
    assert 'design_combat' in model.state
    print("  ✅ 只有 combat")

    model.split_done(); model.categorize_done(); model.translate_done()
    model.agent_done()
    assert 'executor' in model.state
    print("  ✅ agent_done → executor (无 numerical)")


def test_guard_blocks():
    """Guard 阻止无数据跳转"""
    from hfsm_registry import build_hfsm
    model = build_hfsm()
    model.parse_done(); model.split_done(); model.user_confirmed()
    model.dispatch()
    assert model.state == 'coordinator_dispatch'
    print("  ✅ Guard 阻止成功")


if __name__ == "__main__":
    print("=" * 50)
    print("HFSM 测试（数据驱动多角色路由）")
    print("=" * 50)
    test_combat_then_numerical()
    print()
    test_numerical_only()
    print()
    test_combat_only()
    print()
    test_guard_blocks()
    print("=" * 50)
    print("全部通过 ✅")
