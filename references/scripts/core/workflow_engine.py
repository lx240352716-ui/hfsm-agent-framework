# -*- coding: utf-8 -*-
"""
通用工作流引擎 — 基于 pytransitions 库。

从各 Agent 的 workflow.py 读取定义，按 Skill 配置组装状态机。
新增 Skill 只需添加 SKILL_CONFIGS 条目，不需要修改本文件的构建逻辑。

使用方式：
    from workflow_engine import build_workflow
    model = build_workflow("doc")   # 出设计文档
    model = build_workflow("excel") # 填配表
"""

import functools
import importlib.util
import inspect
import json
import os
import sys
from datetime import datetime

from transitions.extensions import HierarchicalMachine


# ── 调试日志 ────────────────────────────────────────

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
_LOG_FILE = os.path.join(_LOG_DIR, 'workflow_debug.log')


def _engine_log(tag, msg):
    """写入调试日志文件 + 打印到控制台"""
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    line = f"[{ts}] [{tag}] {msg}"
    print(f"  {line}")
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        with open(_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


# ── 路径常量 ────────────────────────────────────────

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'agents')

# Agent workflow.py 路径映射（所有可用的 workflow 文件）
WORKFLOW_PATHS = {
    "coordinator": os.path.join(AGENTS_DIR, 'coordinator_memory', 'process', 'coordinator_workflow.py'),
    "combat":      os.path.join(AGENTS_DIR, 'combat_memory',      'process', 'combat_workflow.py'),
    "numerical":   os.path.join(AGENTS_DIR, 'numerical_memory',   'process', 'numerical_workflow.py'),
    "system":      os.path.join(AGENTS_DIR, 'system_memory',      'process', 'system_workflow.py'),
    "executor":    os.path.join(AGENTS_DIR, 'executor_memory',    'process', 'executor_workflow.py'),
    "qa":          os.path.join(AGENTS_DIR, 'qa_memory',          'process', 'qa_workflow.py'),
    # Phase 1/2 新增
    "numerical_doc":   os.path.join(AGENTS_DIR, 'numerical_memory', 'process', 'numerical_doc_workflow.py'),
    "numerical_excel": os.path.join(AGENTS_DIR, 'numerical_memory', 'process', 'numerical_excel_workflow.py'),
    "combat_doc":      os.path.join(AGENTS_DIR, 'combat_memory',    'process', 'combat_doc_workflow.py'),
    "combat_excel":    os.path.join(AGENTS_DIR, 'combat_memory',    'process', 'combat_excel_workflow.py'),
}

# ── Skill 配置 ──────────────────────────────────────
# 每个 Skill 声明它需要哪些 workflow，如何组装

SKILL_CONFIGS = {
    # /excel — 填配表，完整策划流程（原 /design 重命名）
    "excel": {
        "name": "excel",
        "description": "填配表：完整策划流程（L0 → L1 → L2 → L3）",
        "workflows": ["coordinator", "combat", "numerical", "system", "executor", "qa"],
        "structure": "full_pipeline",
    },
    # /doc — 出设计文档
    "doc": {
        "name": "doc",
        "description": "出设计文档（L0 管理 → L1 各 agent 写 draft.md）",
        "workflows": ["coordinator", "system", "numerical_doc", "combat_doc"],
        "structure": "doc_pipeline",
    },
    # [DEPRECATED] /design — 旧名，等同于 /excel，保留向后兼容
    "design": {
        "name": "design",
        "description": "[DEPRECATED] 请使用 /excel。完整策划流程（L0 → L1 → L2 → L3）",
        "workflows": ["coordinator", "combat", "numerical", "system", "executor", "qa"],
        "structure": "full_pipeline",
    },
}


# ── 知识加载 ────────────────────────────────────────

_wiki_knowledge_cache = None


def _get_manifest_text():
    """获取公有知识文本：wiki/index.md + wiki/concepts.md 全文（带模块级缓存）。"""
    global _wiki_knowledge_cache
    if _wiki_knowledge_cache is None:
        parts = []
        wiki_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'knowledge', 'wiki'
        )
        for fname in ('index.md', 'concepts.md'):
            fpath = os.path.join(wiki_dir, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content:
                        parts.append(content)
                except Exception:
                    pass
        _wiki_knowledge_cache = '\n\n---\n\n'.join(parts) if parts else ""
    return _wiki_knowledge_cache


def load_state_knowledge(agent_name, state_name, workflow_mod=None):
    """加载指定 agent 状态的知识上下文。"""
    if workflow_mod is None:
        wf_path = WORKFLOW_PATHS.get(agent_name)
        if not wf_path or not os.path.exists(wf_path):
            return ""
        workflow_mod = load_workflow(agent_name, wf_path)

    knowledge_map = getattr(workflow_mod, 'knowledge', {})
    file_list = knowledge_map.get(state_name, [])
    if not file_list:
        return ""

    # 私有知识目录（去掉 _doc/_excel 后缀找 agent 目录）
    base_agent = agent_name.replace('_doc', '').replace('_excel', '')
    knowledge_dir = os.path.join(AGENTS_DIR, f'{base_agent}_memory', 'knowledge')

    parts = []
    for f in file_list:
        if f == "__manifest__":
            manifest = _get_manifest_text()
            if manifest:
                parts.append(manifest)
        else:
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


# ── Model 类 ────────────────────────────────────────

class WorkflowModel:
    """通用工作流模型 — pytransitions 的 model 对象"""

    def is_dispatch_ready(self):
        return bool(getattr(self, 'dispatched_tasks', None))

    def is_design_done(self):
        return bool(getattr(self, 'design_output', None))

    def is_staging_confirmed(self):
        return getattr(self, 'staging_confirmed', False)

    def is_qa_clean(self):
        return getattr(self, 'qa_errors', 1) == 0

    def is_out_of_scope(self):
        return getattr(self, 'out_of_scope', False)

    def has_design_flaw(self):
        return bool(getattr(self, 'design_flaws', None))

    def has_qa_errors(self):
        return getattr(self, 'qa_errors', 0) > 0

    def _auto_route_design(self):
        """dispatch 完成后自动调用：读 output.json -> 建队列 -> 路由第一个"""
        output_path = os.path.join(AGENTS_DIR, 'coordinator_memory', 'data', 'output.json')
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                output = json.load(f)
            self.design_dispatch = output.get('dispatch', {})
            self.design_roles = list(self.design_dispatch.keys())

        self.design_queue = list(getattr(self, 'design_roles', []))
        self._route_next()

    def _route_next(self):
        """跳到 design_queue 中的下一个 Agent，队列空则触发 design_complete"""
        if self.design_queue:
            next_role = self.design_queue.pop(0)
            trigger = f'route_to_{next_role}'
            getattr(self, trigger)()
        else:
            self.design_output = True
            self.design_complete()


# ── 回调绑定 ────────────────────────────────────────

def _bind_callbacks(model, state_prefix, workflow_mod):
    """从 workflow 模块的 hooks 映射绑定 on_enter/on_exit 回调"""
    hooks = getattr(workflow_mod, 'hooks', {})
    if not hooks:
        return

    # hooks.py 所在目录
    agent_key = state_prefix.replace('design_', '').replace('doc_', '').replace('excel_', '')
    wf_path = WORKFLOW_PATHS.get(agent_key, '')
    wf_dir = os.path.dirname(wf_path) if wf_path else ''

    for hook_key, func_ref in hooks.items():
        if not isinstance(func_ref, str):
            continue

        if hook_key.startswith('on_enter_'):
            event_type = 'on_enter'
            state_name = hook_key[len('on_enter_'):]
        elif hook_key.startswith('on_exit_'):
            event_type = 'on_exit'
            state_name = hook_key[len('on_exit_'):]
        else:
            continue

        module_name, func_name = func_ref.rsplit('.', 1)
        hooks_path = os.path.join(wf_dir, f"{module_name}.py")
        if not os.path.exists(hooks_path):
            continue

        hooks_mod = load_workflow(module_name, hooks_path)
        func = getattr(hooks_mod, func_name, None)
        if not func:
            continue

        full_method = f"{event_type}_{state_prefix}_{state_name}"
        agent_name = state_prefix.replace('design_', '')

        @functools.wraps(func)
        def make_wrapper(f, method_name, evt_type, st_name, ag_name, wf_mod):
            def wrapper(*args, **kwargs):
                _engine_log('HOOK', f'{method_name} -> calling {f.__module__}.{f.__name__}()')
                sig = inspect.signature(f)
                if 'model' in sig.parameters:
                    result = f(model=model, *args, **kwargs)
                else:
                    result = f(*args, **kwargs)
                if isinstance(result, dict):
                    keys = list(result.keys())
                    _engine_log('HOOK', f'{method_name} returned keys={keys}')
                    if result.get('trigger'):
                        _engine_log('HOOK', f'{method_name} trigger={result["trigger"]}')

                    if evt_type == 'on_enter':
                        try:
                            public_knowledge = load_state_knowledge(ag_name, st_name, wf_mod)
                            if public_knowledge:
                                existing = result.get('knowledge', [])
                                if isinstance(existing, list):
                                    result['knowledge'] = existing + [public_knowledge]
                                else:
                                    result['knowledge'] = [existing, public_knowledge]
                                _engine_log('KNOWLEDGE', f'{method_name} injected public knowledge ({len(public_knowledge)} chars)')
                                wiki_hint = '\n[公有知识已注入] 请查阅注入的 wiki/gamedocs 公有知识，从中寻找类似设计文档和配表数据作为参考依据。'
                                existing_inst = result.get('instruction', '')
                                if isinstance(existing_inst, str):
                                    result['instruction'] = existing_inst + wiki_hint
                        except Exception as e:
                            _engine_log('WARN', f'{method_name} failed to load public knowledge: {e}')

                return result
            return wrapper

        setattr(model, full_method, make_wrapper(
            func, full_method, event_type, state_name, agent_name, workflow_mod
        ))


# ── 构建工作流 ──────────────────────────────────────

def build_workflow(skill_name="excel"):
    """
    根据 Skill 配置构建状态机。

    Args:
        skill_name: Skill 名称（"design", "doc", "excel"）

    Returns:
        WorkflowModel: 构建好的状态机 model
    """
    config = SKILL_CONFIGS.get(skill_name)
    if not config:
        raise ValueError(f"Unknown skill: {skill_name}. Available: {list(SKILL_CONFIGS.keys())}")

    structure = config["structure"]

    if structure == "full_pipeline":
        return _build_full_pipeline(config)
    elif structure == "doc_pipeline":
        return _build_doc_pipeline(config)
    elif structure == "excel_pipeline":
        return _build_excel_pipeline(config)
    else:
        raise ValueError(f"Unknown structure: {structure}")


def _build_full_pipeline(config):
    """构建完整策划流程（原 build_hfsm）"""
    _engine_log('BUILD', f'Building {config["name"]} pipeline...')

    # 加载 workflow
    wf_names = config["workflows"]
    wfs = {}
    for name in wf_names:
        path = WORKFLOW_PATHS.get(name)
        if not path or not os.path.exists(path):
            _engine_log('WARN', f'Workflow not found: {name} at {path}')
            continue
        wfs[name] = load_workflow(name, path)
        _engine_log('BUILD', f'Loaded workflow: {name}')

    coord_wf = wfs['coordinator']
    combat_wf = wfs['combat']
    numerical_wf = wfs['numerical']
    system_wf = wfs['system']
    executor_wf = wfs['executor']
    qa_wf = wfs['qa']

    # 状态定义
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
             {'name': 'system',
              'children': workflow_to_states(system_wf),
              'initial': system_wf.initial},
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

    # 转移定义
    transitions = []

    for t in coord_wf.transitions:
        transitions.append([t[0], f'coordinator_{t[1]}', f'coordinator_{t[2]}'])
    for t in combat_wf.transitions:
        transitions.append([t[0], f'design_combat_{t[1]}', f'design_combat_{t[2]}'])
    for t in numerical_wf.transitions:
        transitions.append([t[0], f'design_numerical_{t[1]}', f'design_numerical_{t[2]}'])
    for t in system_wf.transitions:
        transitions.append([t[0], f'design_system_{t[1]}', f'design_system_{t[2]}'])
    for t in executor_wf.transitions:
        transitions.append([t[0], f'executor_{t[1]}', f'executor_{t[2]}'])
    for t in qa_wf.transitions:
        transitions.append([t[0], f'pipeline_{t[1]}', f'pipeline_{t[2]}'])

    # 层间转移
    transitions.extend([
        {'trigger': 'dispatch', 'source': 'coordinator_dispatch', 'dest': 'design',
         'conditions': 'is_dispatch_ready', 'after': '_auto_route_design'},
        {'trigger': 'route_to_combat', 'source': 'design_router', 'dest': 'design_combat'},
        {'trigger': 'route_to_numerical', 'source': 'design_router', 'dest': 'design_numerical'},
        {'trigger': 'route_to_system', 'source': 'design_router', 'dest': 'design_system'},
        {'trigger': 'agent_done', 'source': 'design_combat_review', 'dest': 'design_router',
         'after': '_route_next'},
        {'trigger': 'agent_done', 'source': 'design_numerical_output', 'dest': 'design_router',
         'after': '_route_next'},
        {'trigger': 'agent_done', 'source': 'design_system_export', 'dest': 'design_router',
         'after': '_route_next'},
        {'trigger': 'design_complete', 'source': 'design_router', 'dest': 'executor',
         'conditions': 'is_design_done'},
        {'trigger': 'escalate', 'source': 'design', 'dest': 'coordinator',
         'conditions': 'is_out_of_scope'},
        {'trigger': 'staging_approved', 'source': 'executor_write', 'dest': 'pipeline',
         'conditions': 'is_staging_confirmed'},
        {'trigger': 'design_issue', 'source': 'executor', 'dest': 'design',
         'conditions': 'has_design_flaw'},
        {'trigger': 'all_done', 'source': 'pipeline_done', 'dest': 'completed',
         'conditions': 'is_qa_clean'},
        {'trigger': 'qa_failed', 'source': 'pipeline', 'dest': 'executor',
         'conditions': 'has_qa_errors'},
    ])

    # 构建状态机
    model = WorkflowModel()
    machine = HierarchicalMachine(
        model=model, states=states, transitions=transitions,
        initial='coordinator', ignore_invalid_triggers=False,
        queued=True, after_state_change='_on_state_changed',
    )

    def _on_state_changed():
        _engine_log('STATE', f'-> {model.state}')
    model._on_state_changed = _on_state_changed

    model.machine = machine
    model.skill_name = config["name"]
    model.workflows = wfs

    # 绑定回调
    _bind_callbacks(model, 'coordinator', coord_wf)
    _bind_callbacks(model, 'design_combat', combat_wf)
    _bind_callbacks(model, 'design_numerical', numerical_wf)
    _bind_callbacks(model, 'design_system', system_wf)
    _bind_callbacks(model, 'executor', executor_wf)
    _bind_callbacks(model, 'pipeline', qa_wf)

    from machine_hooks import on_enter_design, on_enter_design_router, on_enter_executor, on_enter_pipeline
    model.on_enter_design = lambda: on_enter_design(model)
    model.on_enter_design_router = lambda: on_enter_design_router(model)
    model.on_enter_executor = lambda: on_enter_executor(model)
    model.on_enter_pipeline = lambda: on_enter_pipeline(model)

    _engine_log('BUILD', f'{config["name"]} pipeline ready.')
    return model


def _build_doc_pipeline(config):
    """构建 /doc 流程 — L0 项目经理 → L1 各 agent 写 draft.md"""
    _engine_log('BUILD', f'Building {config["name"]} pipeline...')

    # 加载 workflow
    wf_names = config["workflows"]
    wfs = {}
    for name in wf_names:
        path = WORKFLOW_PATHS.get(name)
        if not path or not os.path.exists(path):
            _engine_log('WARN', f'Workflow not found: {name} at {path}')
            continue
        wfs[name] = load_workflow(name, path)
        _engine_log('BUILD', f'Loaded workflow: {name}')

    coord_wf = wfs['coordinator']
    system_wf = wfs['system']
    numerical_doc_wf = wfs['numerical_doc']
    combat_doc_wf = wfs['combat_doc']

    # ── 状态定义 ──
    # L0: parse → plan → user_confirm → (动态派发 L1)
    # 中间层 doc_agents: router + 各 L1 agent
    # 最终: deliver / completed
    states = [
        {'name': 'coordinator',
         'children': ['parse', 'plan', 'user_confirm', 'sync', 'run_next'],
         'initial': 'parse'},

        {'name': 'docwork',
         'children': [
             'router',
             {'name': 'system',
              'children': workflow_to_states(system_wf),
              'initial': system_wf.initial},
             {'name': 'numerical',
              'children': workflow_to_states(numerical_doc_wf),
              'initial': numerical_doc_wf.initial},
             {'name': 'combat',
              'children': workflow_to_states(combat_doc_wf),
              'initial': combat_doc_wf.initial},
         ],
         'initial': 'router'},

        'deliver',
        'completed',
    ]

    # ── 转移定义 ──
    transitions = []

    # L0 内部转移
    transitions.extend([
        ['parsed',        'coordinator_parse',        'coordinator_plan'],
        ['planned',       'coordinator_plan',         'coordinator_user_confirm'],
        ['confirmed',     'coordinator_user_confirm', 'docwork'],
        ['synced',        'coordinator_sync',         'coordinator_run_next'],
        ['has_next',      'coordinator_run_next',     'docwork'],
        ['all_done',      'coordinator_run_next',     'deliver'],
    ])

    # L1 system 内部转移
    for t in system_wf.transitions:
        transitions.append([t[0], f'docwork_system_{t[1]}', f'docwork_system_{t[2]}'])

    # L1 numerical_doc 内部转移
    for t in numerical_doc_wf.transitions:
        transitions.append([t[0], f'docwork_numerical_{t[1]}', f'docwork_numerical_{t[2]}'])

    # L1 combat_doc 内部转移
    for t in combat_doc_wf.transitions:
        transitions.append([t[0], f'docwork_combat_{t[1]}', f'docwork_combat_{t[2]}'])

    # L1 完成 -> 回 L0 sync
    transitions.extend([
        {'trigger': 'agent_done', 'source': 'docwork_system_export', 'dest': 'coordinator_sync'},
        {'trigger': 'agent_done', 'source': 'docwork_numerical_done', 'dest': 'coordinator_sync'},
        {'trigger': 'agent_done', 'source': 'docwork_combat_done', 'dest': 'coordinator_sync'},
    ])

    # docwork 内部路由
    transitions.extend([
        {'trigger': 'route_to_system', 'source': 'docwork_router', 'dest': 'docwork_system'},
        {'trigger': 'route_to_numerical', 'source': 'docwork_router', 'dest': 'docwork_numerical'},
        {'trigger': 'route_to_combat', 'source': 'docwork_router', 'dest': 'docwork_combat'},
    ])

    # deliver -> completed
    transitions.append(['finish', 'deliver', 'completed'])

    # -- 构建状态机 --
    model = WorkflowModel()
    machine = HierarchicalMachine(
        model=model, states=states, transitions=transitions,
        initial='coordinator', ignore_invalid_triggers=True,
        queued=True, after_state_change='_on_state_changed',
    )

    def _on_state_changed():
        _engine_log('STATE', f'-> {model.state}')
    model._on_state_changed = _on_state_changed

    model.machine = machine
    model.skill_name = config["name"]
    model.workflows = {
        'coordinator': coord_wf,
        'system': system_wf,
        'numerical_doc': numerical_doc_wf,
        'combat_doc': combat_doc_wf,
    }

    # -- 绑定回调 --
    _bind_callbacks(model, 'coordinator', coord_wf)
    coord_hooks_dir = os.path.dirname(WORKFLOW_PATHS['coordinator'])
    coord_hooks_mod = load_workflow('coordinator_hooks', os.path.join(coord_hooks_dir, 'coordinator_hooks.py'))
    if hasattr(coord_hooks_mod, 'on_enter_plan'):
        model.on_enter_coordinator_plan = lambda: coord_hooks_mod.on_enter_plan()
    if hasattr(coord_hooks_mod, 'on_enter_sync'):
        model.on_enter_coordinator_sync = lambda: coord_hooks_mod.on_enter_sync()
    if hasattr(coord_hooks_mod, 'on_enter_run_next'):
        model.on_enter_coordinator_run_next = lambda: coord_hooks_mod.on_enter_run_next()

    # L1 agents
    _bind_callbacks(model, 'docwork_system', system_wf)
    _bind_callbacks(model, 'docwork_numerical', numerical_doc_wf)
    _bind_callbacks(model, 'docwork_combat', combat_doc_wf)

    _engine_log('BUILD', f'{config["name"]} pipeline ready.')
    return model


def _build_excel_pipeline(config):
    """构建 /excel 流程 — 直接进入 L1 填表，无 L0 coordinator"""
    _engine_log('BUILD', f'Building {config["name"]} pipeline...')

    # 前置检查: draft.md 必须存在
    system_draft = os.path.join(AGENTS_DIR, 'system_memory', 'data', 'draft.md')
    if not os.path.exists(system_draft):
        _engine_log('ERR', 'draft.md not found! Please run /doc first.')
        raise FileNotFoundError(
            "agents/system_memory/data/draft.md not found.\n"
            "Please run /doc first to generate design documents."
        )

    # 加载 workflow
    wf_names = config["workflows"]
    wfs = {}
    for name in wf_names:
        path = WORKFLOW_PATHS.get(name)
        if not path or not os.path.exists(path):
            _engine_log('WARN', f'Workflow not found: {name} at {path}')
            continue
        wfs[name] = load_workflow(name, path)
        _engine_log('BUILD', f'Loaded workflow: {name}')

    numerical_wf = wfs['numerical_excel']
    combat_wf = wfs['combat_excel']

    # -- 状态定义 --
    states = [
        {'name': 'excelwork',
         'children': [
             'router',
             {'name': 'numerical',
              'children': workflow_to_states(numerical_wf),
              'initial': numerical_wf.initial},
             {'name': 'combat',
              'children': workflow_to_states(combat_wf),
              'initial': combat_wf.initial},
         ],
         'initial': 'router'},

        'completed',
    ]

    # -- 转移定义 --
    transitions = []

    # L1 numerical 内部转移
    for t in numerical_wf.transitions:
        transitions.append([t[0], f'excelwork_numerical_{t[1]}', f'excelwork_numerical_{t[2]}'])

    # L1 combat 内部转移
    for t in combat_wf.transitions:
        transitions.append([t[0], f'excelwork_combat_{t[1]}', f'excelwork_combat_{t[2]}'])

    # 路由
    transitions.extend([
        {'trigger': 'route_to_numerical', 'source': 'excelwork_router', 'dest': 'excelwork_numerical'},
        {'trigger': 'route_to_combat', 'source': 'excelwork_router', 'dest': 'excelwork_combat'},
    ])

    # 完成后路由到下一个或结束
    transitions.extend([
        {'trigger': 'agent_done', 'source': 'excelwork_numerical_output', 'dest': 'excelwork_router',
         'after': '_route_next'},
        {'trigger': 'agent_done', 'source': 'excelwork_combat_review', 'dest': 'excelwork_router',
         'after': '_route_next'},
        {'trigger': 'all_done', 'source': 'excelwork_router', 'dest': 'completed'},
    ])

    # -- 构建状态机 --
    model = WorkflowModel()
    machine = HierarchicalMachine(
        model=model, states=states, transitions=transitions,
        initial='excelwork', ignore_invalid_triggers=True,
        queued=True, after_state_change='_on_state_changed',
    )

    def _on_state_changed():
        _engine_log('STATE', f'-> {model.state}')
    model._on_state_changed = _on_state_changed

    model.machine = machine
    model.skill_name = config["name"]
    model.workflows = {
        'numerical_excel': numerical_wf,
        'combat_excel': combat_wf,
    }

    # -- 绑定回调 --
    _bind_callbacks(model, 'excelwork_numerical', numerical_wf)
    _bind_callbacks(model, 'excelwork_combat', combat_wf)

    _engine_log('BUILD', f'{config["name"]} pipeline ready.')
    return model
