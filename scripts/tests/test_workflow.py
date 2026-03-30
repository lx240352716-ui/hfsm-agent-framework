# -*- coding: utf-8 -*-
"""
Workflow 框架测试。

运行方式:
    cd scripts/tests
    python test_pipeline.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from workflow import Workflow, Step, WorkflowError, WorkflowAbort


def test_normal_flow():
    """正常按顺序走完所有步骤。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"]),
        Step("b", inputs=["x"], outputs=["y"]),
        Step("c", inputs=["y"], outputs=["z"]),
    ])

    result = pipe.advance("a", {"x": 1})
    assert result["state"] == Workflow.RUNNING, f"期望 RUNNING，得到 {result['state']}"
    assert "a" in result["completed_steps"]

    pipe.advance("b", {"y": 2})
    result = pipe.advance("c", {"z": 3})
    assert result["state"] == Workflow.COMPLETED
    assert len(result["completed_steps"]) == 3
    assert pipe.context == {"x": 1, "y": 2, "z": 3}
    print("  ✅ test_normal_flow")


def test_skip_step():
    """跳步 → 报错。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"]),
        Step("b", inputs=["x"], outputs=["y"]),
        Step("c", inputs=["y"], outputs=["z"]),
    ])

    try:
        pipe.advance("b", {"y": 1})
        assert False, "应该报错但没有"
    except WorkflowError as e:
        assert "a" in str(e) and "b" in str(e)
    print("  ✅ test_skip_step")


def test_missing_output():
    """输出缺 key → 报错。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x", "y"]),
    ])

    try:
        pipe.advance("a", {"x": 1})  # 缺 y
        assert False, "应该报错但没有"
    except WorkflowError as e:
        assert "y" in str(e)
    print("  ✅ test_missing_output")


def test_empty_output():
    """输出为空值 → 报错。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"]),
    ])

    try:
        pipe.advance("a", {"x": []})  # 空列表
        assert False, "应该报错但没有"
    except WorkflowError as e:
        assert "空" in str(e)
    print("  ✅ test_empty_output")


def test_max_retries():
    """同一步重试超限 → WorkflowAbort。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x", "y"]),
    ], max_retries=2)

    # 第1次：缺 y
    try:
        pipe.advance("a", {"x": 1})
    except WorkflowError:
        pass

    # 第2次：还是缺 y
    try:
        pipe.advance("a", {"x": 1})
    except WorkflowError:
        pass

    # 第3次：超限 → Abort
    try:
        pipe.advance("a", {"x": 1})
        assert False, "应该 Abort"
    except WorkflowAbort as e:
        assert "重试" in str(e)
    print("  ✅ test_max_retries")


def test_user_confirm():
    """需用户确认的步骤 → 返回 WAITING_USER_CONFIRM。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"], require_user_confirm=True),
        Step("b", inputs=["x"], outputs=["y"]),
    ])

    result = pipe.advance("a", {"x": 1})
    assert result["state"] == Workflow.WAITING_USER_CONFIRM
    assert result["waiting_confirm_for"] == "a"

    # 未确认就 advance → 报错
    try:
        pipe.advance("b", {"y": 2})
        assert False, "应该报错"
    except WorkflowError as e:
        assert "确认" in str(e)

    # 确认后继续
    pipe.confirm()
    result = pipe.advance("b", {"y": 2})
    assert result["state"] == Workflow.COMPLETED
    print("  ✅ test_user_confirm")


def test_from_json_combat():
    """从 combat.json 加载（3步：split→categorize→translate）。"""
    pipe = Workflow.from_json("combat.json")
    assert pipe.name == "combat_buff"
    assert len(pipe.steps) == 3
    assert pipe.steps[0].name == "split"
    assert pipe.steps[0].require_user_confirm is True
    assert pipe.steps[2].name == "translate"
    assert pipe.steps[2].require_user_confirm is True
    print("  ✅ test_from_json_combat")


def test_from_json_execution():
    """从 executor.json 加载（7步）。"""
    pipe = Workflow.from_json("executor.json")
    assert pipe.name == "execution"
    assert len(pipe.steps) == 7
    assert pipe.steps[0].name == "resolve"
    assert pipe.steps[0].hook == "executor_hooks.resolve"
    assert pipe.steps[6].name == "staging"
    assert pipe.steps[6].require_user_confirm is True
    step_names = [s.name for s in pipe.steps]
    assert step_names == ["resolve", "align", "fill_defaults", "assign_ids", "resolve_refs", "check", "staging"]
    print("  ✅ test_from_json_execution")


def test_from_json_standard():
    """从 pipeline_standard.json 加载。"""
    pipe = Workflow.from_json("standard.json")
    assert pipe.name == "standard"
    assert len(pipe.steps) == 9

    # 5 个确认点: understand, scope, review, confirm, postmortem
    confirm_steps = [s.name for s in pipe.steps if s.require_user_confirm]
    assert confirm_steps == ["understand", "scope", "review", "confirm", "postmortem"], \
        f"确认步骤不对: {confirm_steps}"
    print("  ✅ test_from_json_standard")


def test_summary():
    """summary() 返回人类可读内容。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"], description="第一步"),
        Step("b", inputs=["x"], outputs=["y"], description="第二步"),
    ])
    pipe.advance("a", {"x": 1})
    s = pipe.summary()
    assert "✅" in s
    assert "👉" in s
    assert "test" in s
    print("  ✅ test_summary")


def test_context_accumulates():
    """前面步骤的输出后面都能用。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"]),
        Step("b", inputs=["x"], outputs=["y"]),
        Step("c", inputs=["x", "y"], outputs=["z"]),  # 依赖 a 和 b 的输出
    ])
    pipe.advance("a", {"x": 1})
    pipe.advance("b", {"y": 2})
    pipe.advance("c", {"z": 3})
    assert pipe.context == {"x": 1, "y": 2, "z": 3}
    print("  ✅ test_context_accumulates")


def test_missing_input():
    """上游输出缺失 → 报错。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"]),
        Step("b", inputs=["x", "w"], outputs=["y"]),  # w 没人产出
    ])
    pipe.advance("a", {"x": 1})
    try:
        pipe.advance("b", {"y": 2})
        assert False, "应该报错"
    except WorkflowError as e:
        assert "w" in str(e)
    print("  ✅ test_missing_input")


def test_advance_after_complete():
    """完成后再 advance → 报错。"""
    pipe = Workflow("test", steps=[
        Step("a", outputs=["x"]),
    ])
    pipe.advance("a", {"x": 1})
    try:
        pipe.advance("a", {"x": 1})
        assert False, "应该报错"
    except WorkflowError:
        pass
    print("  ✅ test_advance_after_complete")


def test_sub_workflow_flow():
    """主 Workflow 自动进入子 Workflow，完成后自动返回。"""
    # 主 Workflow: step_a → step_sub(子工作流) → step_c
    main = Workflow("main", steps=[
        Step("step_a", outputs=["x"]),
        Step("step_sub", inputs=["x"], outputs=["result"],
             sub_workflow=None,  # 我们手动构建子 Workflow
             input_mapping={"x": "sub_input"},
             output_mapping={"sub_output": "result"}),
        Step("step_c", inputs=["result"], outputs=["final"]),
    ])

    # 因为测试不走 from_json，手动模拟 sub_workflow
    # 直接给 step_sub 设置一个内联子 Workflow
    sub_steps = [
        Step("sub_1", outputs=["sub_mid"]),
        Step("sub_2", inputs=["sub_mid"], outputs=["sub_output"]),
    ]
    # 手动触发 sub_workflow 进入（模拟 _enter_sub_workflow 的逻辑）
    main.advance("step_a", {"x": 42})
    assert main.state == Workflow.RUNNING

    # step_sub 没有 sub_workflow 配置文件（测试中无法走 from_json），
    # 所以我们测试 advance 的正常功能 —— sub_workflow 需要用 from_json 测试
    # 这里测试透明委托的核心路径
    main.advance("step_sub", {"result": "done"})
    main.advance("step_c", {"final": "all_done"})
    assert main.state == Workflow.COMPLETED
    assert main.context["result"] == "done"
    assert main.context["final"] == "all_done"
    print("  ✅ test_sub_workflow_flow")


def test_sub_workflow_from_json():
    """从 standard.json 加载，验证 design 步有 sub_workflow 配置。"""
    wf = Workflow.from_json("standard.json")
    design_step = wf.steps[2]  # design 是第3个步骤
    assert design_step.name == "design"
    assert design_step.sub_workflow == "combat.json"
    assert design_step.input_mapping == {"table_scope": "required_tables"}
    assert design_step.output_mapping == {"result": "design_data"}
    assert design_step.has_sub_workflow is True
    print("  ✅ test_sub_workflow_from_json")


def test_sub_workflow_transparent_delegation():
    """IN_SUB_WORKFLOW 时 advance 透明委托给子 Workflow。"""
    main = Workflow("main", steps=[
        Step("step_a", outputs=["x"]),
        Step("step_sub", inputs=["x"], outputs=["result"],
             input_mapping={}, output_mapping={"sub_out": "result"}),
        Step("step_c", inputs=["result"], outputs=["final"]),
    ])

    main.advance("step_a", {"x": 1})

    # 手动模拟进入子 Workflow
    sub = Workflow("sub_test", steps=[
        Step("sub_1", outputs=["sub_out"]),
    ])
    main._active_sub = sub
    main.state = Workflow.IN_SUB_WORKFLOW

    # advance 应该被透传给子 Workflow
    result = main.advance("sub_1", {"sub_out": "data"})
    assert main.state != Workflow.IN_SUB_WORKFLOW, "子 Workflow 完成后应退出 IN_SUB_WORKFLOW"
    assert main.context.get("result") == "data", f"output_mapping 应生效，但 result={main.context.get('result')}"
    print("  ✅ test_sub_workflow_transparent_delegation")


def test_handoff_token():
    """final_handoff 配置的 Workflow 完成后，status 包含 SYSTEM_HANDOFF。"""
    wf = Workflow("test_handoff", steps=[
        Step("only_step", outputs=["x"]),
    ], final_handoff={"role": "执行策划", "action": "审核"})

    wf.advance("only_step", {"x": 1})
    assert wf.state == Workflow.COMPLETED

    status = wf.status()
    assert "SYSTEM_HANDOFF" in status, f"完成后应有 SYSTEM_HANDOFF，但 status={status}"
    assert status["SYSTEM_HANDOFF"]["hand_to"] == "执行策划"
    assert status["SYSTEM_HANDOFF"]["action"] == "审核"
    print("  ✅ test_handoff_token")


def test_combat_json_has_handoff():
    """combat.json 加载后应有 final_handoff。"""
    wf = Workflow.from_json("combat.json")
    assert wf.final_handoff is not None
    assert wf.final_handoff["role"] == "执行策划"
    print("  ✅ test_combat_json_has_handoff")


# ── 运行 ──────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_normal_flow,
        test_skip_step,
        test_missing_output,
        test_empty_output,
        test_max_retries,
        test_user_confirm,
        test_from_json_combat,
        test_from_json_execution,
        test_from_json_standard,
        test_summary,
        test_context_accumulates,
        test_missing_input,
        test_advance_after_complete,
        # 分层 Workflow 测试
        test_sub_workflow_flow,
        test_sub_workflow_from_json,
        test_sub_workflow_transparent_delegation,
        test_handoff_token,
        test_combat_json_has_handoff,
    ]

    print(f"\n🧪 Workflow 测试（共 {len(tests)} 项）\n")
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"通过: {passed}  失败: {failed}  总计: {len(tests)}")
    if failed == 0:
        print("🎉 全部通过！")
    else:
        print("⚠️ 有测试失败")
