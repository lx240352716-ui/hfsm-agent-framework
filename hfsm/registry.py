# -*- coding: utf-8 -*-
"""
HFSM 注册器 — 从配置文件自动组装分层状态机

读取 agents.json 配置，动态加载各 Agent 的 workflow.py，
自动注册状态、转移、Hook 绑定。

使用方式：
    from hfsm.config import Config
    from hfsm.registry import build_hfsm

    Config.init("/path/to/project")
    machine, model = build_hfsm()
    machine.send("start")
"""

import os
import sys
import importlib.util

from .config import Config

def load_workflow(name, path):
    """动态加载一个 Agent 的 workflow.py，返回模块对象"""
    spec = importlib.util.spec_from_file_location(f"workflow_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def workflow_to_states(mod):
    """把 workflow 模块的 states 列表转为状态名列表"""
    return [s['name'] for s in getattr(mod, 'states', [])]

def build_hfsm(agents_config=None):
    """从配置自动组装完整 HFSM。

    Args:
        agents_config: agents 配置 dict。默认从 agents.json 加载。

    Returns:
        (machine, model): pytransitions Machine 和 model 对象
    """
    if agents_config is None:
        agents_config = Config.load_agents_config()

    # 确保 scripts 目录在 path 中
    project_dir = str(Config.get_root())
    scripts_core = os.path.join(project_dir, 'scripts', 'core')
    if os.path.exists(scripts_core) and scripts_core not in sys.path:
        sys.path.insert(0, scripts_core)

    # 加载所有 Agent workflow
    workflows = {}
    for agent_name, agent_cfg in agents_config.get('agents', {}).items():
        wf_path = agent_cfg.get('workflow', '')
        if not os.path.isabs(wf_path):
            wf_path = os.path.join(project_dir, wf_path)
        if os.path.exists(wf_path):
            workflows[agent_name] = load_workflow(agent_name, wf_path)

    return workflows

def bind_hooks(model, state_prefix, workflow_mod, agent_name=None):
    """从 workflow 模块的 hooks 映射中读取函数引用，绑定到回调。

    支持扁平格式：
        hooks = {"on_enter_execute": "executor_hooks.on_enter_execute"}

    Args:
        model: model 对象
        state_prefix: 状态名前缀
        workflow_mod: workflow 模块对象
        agent_name: agent 名称，用于注入 HookContext
    """
    hooks = getattr(workflow_mod, 'hooks', {})
    mod_dir = os.path.dirname(workflow_mod.__file__)

    for callback_name, func_ref in hooks.items():
        if '.' in func_ref:
            mod_name, fn_name = func_ref.rsplit('.', 1)
            # 动态导入 hook 模块
            hook_path = os.path.join(mod_dir, f'{mod_name}.py')
            if os.path.exists(hook_path):
                spec = importlib.util.spec_from_file_location(
                    f"{state_prefix}_{mod_name}", hook_path
                )
                hook_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(hook_mod)
                fn = getattr(hook_mod, fn_name, None)
                if fn:
                    # 如果提供了 agent_name，则自动使用 HookContext 包装，精简业务代码
                    if agent_name:
                        from .runner import wrap_hook
                        fn = wrap_hook(fn, agent_name)
                    # 绑定到 model
                    full_name = f"{callback_name}"
                    setattr(model, full_name, fn)
