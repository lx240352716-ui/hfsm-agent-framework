# -*- coding: utf-8 -*-
"""machine.py 引擎骨架验证测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
from machine import Machine

def test_basic():
    """基本流转：3 个状态，2 个事件"""
    m = Machine("test", initial="A", description="基本测试")
    m.add_state("A", description="状态A")
    m.add_state("B", description="状态B")
    m.add_state("C", description="状态C")
    m.add_transition("go", "A", "B")
    m.add_transition("go", "B", "C")

    m.start()
    assert m.current == "A", f"期望 A，实际 {m.current}"

    r = m.send("go")
    assert r["handled"] and m.current == "B"

    r = m.send("go")
    assert r["handled"] and m.current == "C"
    print("  ✅ 基本流转 OK")

def test_guard():
    """守卫条件：条件不满足时不跳转"""
    m = Machine("guard_test", initial="wait")
    m.add_state("wait")
    m.add_state("done")
    m.add_transition("try_finish", "wait", "done",
                     guard=lambda ctx: ctx.get("confirmed") == True)

    m.start()
    r = m.send("try_finish")  # 没 confirmed → 不跳
    assert not r["handled"]
    assert m.current == "wait"

    r = m.send("try_finish", {"confirmed": True})  # 有了 → 跳
    assert r["handled"] and m.current == "done"
    print("  ✅ 守卫条件 OK")

def test_hierarchy():
    """分层嵌套：父状态机包含子状态机"""
    # 子状态机：L0 内部
    child = Machine("L0_coordinator", initial="parse")
    child.add_state("parse")
    child.add_state("dispatch")
    child.add_transition("parse_done", "parse", "dispatch")

    # 父状态机
    parent = Machine("root", initial="L0")
    parent.add_state("L0", description="主策划层")
    parent.add_state("L1", description="设计层")
    parent.add_child("L0", child)
    parent.add_transition("L0_complete", "L0", "L1")

    parent.start()
    assert parent.current == "L0"

    # 事件下沉到子状态机
    r = parent.send("parse_done")
    assert r["handled"]
    assert child.current == "dispatch"

    # 父层转移
    r = parent.send("L0_complete")
    assert r["handled"] and parent.current == "L1"
    print("  ✅ 分层嵌套 OK")

def test_persistence():
    """持久化：保存/恢复状态"""
    m = Machine("save_test", initial="step1")
    m.add_state("step1")
    m.add_state("step2")
    m.add_transition("next", "step1", "step2")

    m.start({"task": "test_task"})
    m.send("next")
    assert m.current == "step2"

    # 保存
    path = os.path.join(os.environ.get("TEMP", "/tmp"), "test_state.json")
    m.save(path)

    # 新建一个同结构的 machine，加载状态
    m2 = Machine("save_test", initial="step1")
    m2.add_state("step1")
    m2.add_state("step2")
    m2.load(path)
    assert m2.current == "step2"
    assert m2.context["task"] == "test_task"
    print("  ✅ 持久化 OK")

    os.remove(path)

if __name__ == "__main__":
    print("=" * 50)
    print("Machine 引擎骨架测试")
    print("=" * 50)
    test_basic()
    test_guard()
    test_hierarchy()
    test_persistence()
    print("=" * 50)
    print("全部通过 ✅")
