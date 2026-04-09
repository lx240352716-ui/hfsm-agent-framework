# -*- coding: utf-8 -*-
"""
HFSM 分层注册 — 基于 pytransitions 库。

自动从各 Agent 的 workflow.py 读取定义并组装成完整 HFSM。
不再硬编码状态和转移，每个 Agent 自管自己的 workflow。

使用方式：
    from hfsm_registry import build_hfsm
    model = build_hfsm()
    model.dispatch()
    model.state
"""

import importlib.util
import os
import sys

from transitions.extensions import HierarchicalMachine


# ── 路径常量 ────────────────────────────────────────

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')

# Agent workflow.py 路径映射
WORKFLOW_PATHS = {
    "coordinator": os.path.join(AGENTS_DIR, 'coordinator_memory', 'process', 'coordinator_workflow.py'),
    "combat":      os.path.join(AGENTS_DIR, 'combat_memory',      'process', 'combat_workflow.py'),
    "numerical":   os.path.join(AGENTS_DIR, 'numerical_memory',   'process', 'numerical_workflow.py'),
    "executor":    os.path.join(AGENTS_DIR, 'executor_memory',    'process', 'executor_workflow.py'),
    "qa":          os.path.join(AGENTS_DIR, 'qa_memory',          'process', 'qa_workflow.py'),
}


# ── 知识加载 ────────────────────────────────────────

# 公有知识清单（懒加载）
_manifest_text_cache = None


def _get_manifest_text():
    """获取公有知识清单文本（带模块级缓存）。"""
    global _manifest_text_cache
    if _manifest_text_cache is None:
        try:
            from knowledge_search import get_manifest_text
            _manifest_text_cache = get_manifest_text() or ""
        except ImportError:
            _manifest_text_cache = ""
    return _manifest_text_cache


def load_state_knowledge(agent_name, state_name, workflow_mod=None):
    """加载指定 agent 状态的知识上下文。

    读取 workflow.knowledge 里配置的文件列表：
    - 普通文件名 → 从 agents/{agent}_memory/knowledge/ 读取私有知识
    - "__manifest__" → 注入公有 gamedocs 文件清单

    Args:
        agent_name: agent 名称（如 'coordinator', 'combat', 'numerical'）
        state_name: 状态名（如 'parse', 'match', 'translate'）
        workflow_mod: 已加载的 workflow 模块（优先使用，避免重复加载）

    Returns:
        str: 拼接好的知识文本，供注入 LLM prompt
    """
    # 使用传入的 workflow 模块，或从磁盘加载
    if workflow_mod is None:
        wf_path = WORKFLOW_PATHS.get(agent_name)
        if not wf_path or not os.path.exists(wf_path):
            return ""
        workflow_mod = load_workflow(agent_name, wf_path)

    knowledge_map = getattr(workflow_mod, 'knowledge', {})
    file_list = knowledge_map.get(state_name, [])
    if not file_list:
        return ""

    # 私有知识目录
    knowledge_dir = os.path.join(AGENTS_DIR, f'{agent_name}_memory', 'knowledge')

    # 逐项加载
    parts = []
    for f in file_list:
        if f == "__manifest__":
            manifest = _get_manifest_text()
            if manifest:
                parts.append(manifest)
        else:
            # 私有知识文件（支持子目录如 understand/rules.md）
            fpath = os.path.join(knowledge_dir, f)
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as fp:
                        content = fp.read().strip()
                    if content:
                        parts.append(f"# {f}\n{content}")
                except Exception:
                    pass

    return '\n\n---\n\n'.join(parts)


# ── 工具函数 ────────────────────────────────────────

def load_workflow(name, path):
    """动态加载一个 Agent 的 workflow.py，返回模块对象"""
    spec = importlib.util.spec_from_file_location(f"{name}_workflow", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def workflow_to_states(mod):
    """把 workflow 模块的 states 列表转为 pytransitions 的 state name 列表"""
    return [s["name"] if isinstance(s, dict) else s for s in mod.states]


# ── Guard 条件 ──────────────────────────────────────

class DesignWorkflow:
    """策划工作流模型 — pytransitions 的 model 对象"""

    def is_dispatch_ready(self):
        """L0→L1: 派发数据已准备好"""
        return bool(getattr(self, 'dispatched_tasks', None))

    def is_design_done(self):
        """L1→L2: 设计方案已完成"""
        return bool(getattr(self, 'design_output', None))

    def is_staging_confirmed(self):
        """L2→L3: 用户已确认 staging"""
        return getattr(self, 'staging_confirmed', False)

    def is_qa_clean(self):
        """L3→completed: QA 零错误"""
        return getattr(self, 'qa_errors', 1) == 0

    def is_out_of_scope(self):
        """L1→L0: 超出本角色能力范围"""
        return getattr(self, 'out_of_scope', False)

    def has_design_flaw(self):
        """L2→L1: 发现设计层面问题"""
        return bool(getattr(self, 'design_flaws', None))

    def has_qa_errors(self):
        """L3→L2: QA 发现错误"""
        return getattr(self, 'qa_errors', 0) > 0

    def _auto_route_design(self):
        """dispatch 完成后自动调用：读 output.json → 建队列 → 路由第一个"""
        import json
        output_path = os.path.join(
            AGENTS_DIR, 'coordinator_memory', 'data', 'output.json')
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                output = json.load(f)
            self.design_dispatch = output.get('dispatch', {})
            self.design_roles = list(self.design_dispatch.keys())

        # 建立执行队列，按 dispatch 顺序
        self.design_queue = list(getattr(self, 'design_roles', []))
        self._route_next()

    def _route_next(self):
        """跳到 design_queue 中的下一个 Agent，队列空则触发 design_complete"""
        if self.design_queue:
            next_role = self.design_queue.pop(0)
            trigger = f'route_to_{next_role}'
            getattr(self, trigger)()
        else:
            # 全部 Agent 做完，自动完成设计层
            self.design_output = True
            self.design_complete()


# ── L3 Pipeline 定义（从 qa_workflow.py 读取） ──────
# 不再硬编码，动态从 qa_workflow.py 加载


# ── 构建 HFSM ──────────────────────────────────────

def build_hfsm():
    """
    从各 Agent 的 workflow.py 读取定义，自动组装完整 HFSM。

    结构：
        coordinator (主策划)
          └── parse → split_modules → user_confirm → dispatch
        design (设计层)
          ├── combat → split → categorize → translate → review
          └── numerical → analyze → calculate → output
        executor (执行层)
          └── resolve → align → ... → staging → review
        pipeline (质检层)
          └── qa → validate → merge → track
    """

    # 加载各 Agent 的 workflow 定义
    coord_wf = load_workflow("coordinator", WORKFLOW_PATHS["coordinator"])
    combat_wf = load_workflow("combat", WORKFLOW_PATHS["combat"])
    numerical_wf = load_workflow("numerical", WORKFLOW_PATHS["numerical"])
    executor_wf = load_workflow("executor", WORKFLOW_PATHS["executor"])
    qa_wf = load_workflow("qa", WORKFLOW_PATHS["qa"])

    # ── 状态定义（自动从 workflow 读取） ──

    states = [
        {'name': 'coordinator',
         'children': workflow_to_states(coord_wf),
         'initial': coord_wf.initial},

        {'name': 'design',
         'children': [
             'router',
             {'name': 'combat',
              'children': workflow_to_states(combat_wf),
              'initial': combat_wf.initial},
             {'name': 'numerical',
              'children': workflow_to_states(numerical_wf),
              'initial': numerical_wf.initial},
         ],
         'initial': 'router'},

        {'name': 'executor',
         'children': workflow_to_states(executor_wf),
         'initial': executor_wf.initial},

        {'name': 'pipeline',
         'children': workflow_to_states(qa_wf),
         'initial': qa_wf.initial},

        'completed',
    ]

    # ── 转移定义（层内从 workflow 读取，层间手动定义） ──

    transitions = []

    # 层内转移：自动添加前缀
    for t in coord_wf.transitions:
        transitions.append([t[0], f'coordinator_{t[1]}', f'coordinator_{t[2]}'])

    for t in combat_wf.transitions:
        transitions.append([t[0], f'design_combat_{t[1]}', f'design_combat_{t[2]}'])

    for t in numerical_wf.transitions:
        transitions.append([t[0], f'design_numerical_{t[1]}', f'design_numerical_{t[2]}'])

    for t in executor_wf.transitions:
        transitions.append([t[0], f'executor_{t[1]}', f'executor_{t[2]}'])

    for t in qa_wf.transitions:
        transitions.append([t[0], f'pipeline_{t[1]}', f'pipeline_{t[2]}'])

    # 层间转移（含 Guard 条件）
    transitions.extend([
        # coordinator → design (派发 + 自动路由)
        {'trigger': 'dispatch', 'source': 'coordinator_dispatch', 'dest': 'design',
         'conditions': 'is_dispatch_ready',
         'after': '_auto_route_design'},

        # design 内部路由（数据驱动，支持任意 Agent）
        {'trigger': 'route_to_combat', 'source': 'design_router', 'dest': 'design_combat'},
        {'trigger': 'route_to_numerical', 'source': 'design_router', 'dest': 'design_numerical'},
        # 未来扩展: {'trigger': 'route_to_system', 'source': 'design_router', 'dest': 'design_system'},

        # 各 Agent 完成 → 回 router → _route_next 接下一个
        {'trigger': 'agent_done', 'source': 'design_combat_review', 'dest': 'design_router',
         'after': '_route_next'},
        {'trigger': 'agent_done', 'source': 'design_numerical_output', 'dest': 'design_router',
         'after': '_route_next'},

        # design → executor (所有 Agent 完成后由 _route_next 自动触发)
        {'trigger': 'design_complete', 'source': 'design_router', 'dest': 'executor',
         'conditions': 'is_design_done'},

        # design → coordinator (升级回主策划)
        {'trigger': 'escalate', 'source': 'design', 'dest': 'coordinator',
         'conditions': 'is_out_of_scope'},

        # executor → pipeline (L2 完成 → L3 QA)
        {'trigger': 'staging_approved', 'source': 'executor_write', 'dest': 'pipeline',
         'conditions': 'is_staging_confirmed'},

        # executor → design (设计问题打回)
        {'trigger': 'design_issue', 'source': 'executor', 'dest': 'design',
         'conditions': 'has_design_flaw'},

        # pipeline → completed (全部通过)
        {'trigger': 'all_done', 'source': 'pipeline_done', 'dest': 'completed',
         'conditions': 'is_qa_clean'},

        # pipeline → executor (QA 失败打回)
        {'trigger': 'qa_failed', 'source': 'pipeline', 'dest': 'executor',
         'conditions': 'has_qa_errors'},
    ])

    # ── 构建状态机 ──

    model = DesignWorkflow()
    machine = HierarchicalMachine(
        model=model,
        states=states,
        transitions=transitions,
        initial='coordinator',
        ignore_invalid_triggers=False,
        queued=True,
    )

    # 把 machine 和 workflow 配置挂到 model 上
    model.machine = machine
    model.workflows = {
        'coordinator': coord_wf,
        'combat': combat_wf,
        'numerical': numerical_wf,
        'executor': executor_wf,
        'qa': qa_wf,
    }

    # ── 绑定 on_enter / on_exit 回调 ──

    # Agent 级回调
    _bind_callbacks(model, 'coordinator', coord_wf)
    _bind_callbacks(model, 'design_combat', combat_wf)
    _bind_callbacks(model, 'design_numerical', numerical_wf)
    _bind_callbacks(model, 'executor', executor_wf)
    _bind_callbacks(model, 'pipeline', qa_wf)

    # 层间回调 (machine_hooks)
    from machine_hooks import on_enter_design, on_enter_design_router, on_enter_executor, on_enter_pipeline
    model.on_enter_design = lambda: on_enter_design(model)
    model.on_enter_design_router = lambda: on_enter_design_router(model)
    model.on_enter_executor = lambda: on_enter_executor(model)
    model.on_enter_pipeline = lambda: on_enter_pipeline(model)

    return model


def _bind_callbacks(model, state_prefix, workflow_mod):
    """
    从 workflow 模块的 hooks 映射中读取函数引用，
    绑定到 pytransitions 的 on_enter / on_exit 回调。

    支持扁平格式：
        hooks = {"on_enter_execute": "executor_hooks.on_enter_execute"}
        → 绑定到 on_enter_executor_execute

    Args:
        model: pytransitions model 对象
        state_prefix: 状态名前缀，如 "coordinator" 或 "design_combat"
        workflow_mod: workflow 模块对象
    """
    hooks = getattr(workflow_mod, 'hooks', {})
    if not hooks:
        return

    # hooks.py 所在目录
    wf_dir = os.path.dirname(WORKFLOW_PATHS.get(
        state_prefix.replace('design_', ''), ''
    ))

    for hook_key, func_ref in hooks.items():
        # 解析扁平格式："on_enter_execute" → event="on_enter", state="execute"
        if not isinstance(func_ref, str):
            continue

        # 支持 on_enter_xxx 和 on_exit_xxx
        if hook_key.startswith('on_enter_'):
            event_type = 'on_enter'
            state_name = hook_key[len('on_enter_'):]
        elif hook_key.startswith('on_exit_'):
            event_type = 'on_exit'
            state_name = hook_key[len('on_exit_'):]
        else:
            continue

        # 动态导入函数
        module_name, func_name = func_ref.rsplit('.', 1)
        hooks_path = os.path.join(wf_dir, f"{module_name}.py")
        if not os.path.exists(hooks_path):
            continue

        hooks_mod = load_workflow(module_name, hooks_path)
        func = getattr(hooks_mod, func_name, None)
        if not func:
            continue

        # 绑定到 model：pytransitions 调 on_enter_executor_execute 时触发
        full_method = f"{event_type}_{state_prefix}_{state_name}"

        # 包装函数，自动传 model 给 hook
        import functools
        @functools.wraps(func)
        def make_wrapper(f):
            def wrapper(*args, **kwargs):
                import inspect
                sig = inspect.signature(f)
                if 'model' in sig.parameters:
                    return f(model=model, *args, **kwargs)
                else:
                    return f(*args, **kwargs)
            return wrapper

        setattr(model, full_method, make_wrapper(func))

