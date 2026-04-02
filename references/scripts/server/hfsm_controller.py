# -*- coding: utf-8 -*-
"""
HFSM Controller v2 — 异步任务模式。

核心变化（vs v1 同步模式）：
- 用户消息 → 创建后台任务 → 立即返回"收到"
- 任务在独立线程中运行 HFSM 状态机
- 遇到 pause 状态 → 通过回调通知 IM（发卡片）
- 用户确认 → 恢复任务继续执行
- 任务完成 → 通过回调通知 IM（发结果）

Usage:
    ctrl = get_controller(user_id, reply_callback=send_to_dingtalk)
    ctrl.submit("新增一个攻击力 buff")     # 非阻塞，立即返回
    ctrl.resume("确认")                    # 用户确认后调用
"""

import os
import sys
import json
import threading
import importlib
import traceback
import time
import logging
from enum import Enum

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'core'))

from constants import AGENTS_DIR, agent_paths
from llm_client import llm
from prompt_builder import build_system_prompt, build_user_message

logger = logging.getLogger('hfsm_controller')


# ── 任务状态 ──

class TaskStatus(Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    WAITING_USER = 'waiting_user'
    COMPLETED = 'completed'
    ERROR = 'error'


# ── 加载 Workflow / Hook ──

def _load_workflow(agent_name):
    """动态加载 Agent 的 workflow.py 定义。"""
    process_dir = agent_paths(agent_name)['process_dir']
    if not os.path.isdir(process_dir):
        return None
    for f in os.listdir(process_dir):
        if f.endswith('_workflow.py'):
            spec = importlib.util.spec_from_file_location(
                f"workflow_{agent_name}",
                os.path.join(process_dir, f),
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def _load_hook(hook_ref, agent_name):
    """从 hook 引用字符串加载函数。"""
    parts = hook_ref.split('.')
    if len(parts) != 2:
        return None
    module_name, func_name = parts
    process_dir = agent_paths(agent_name)['process_dir']
    module_path = os.path.join(process_dir, f"{module_name}.py")
    if not os.path.exists(module_path):
        return None
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'core'))
    spec.loader.exec_module(mod)
    return getattr(mod, func_name, None)


class HFSMController:
    """异步 HFSM 状态机控制器。"""

    def __init__(self, user_id: str, reply_callback=None):
        """
        Args:
            user_id: 用户唯一标识
            reply_callback: 回复回调函数 fn(user_id, message, card_data=None)
                - message: 文本消息
                - card_data: 互动卡片数据（包含按钮选项），None 则发普通文本
        """
        self.user_id = user_id
        self.reply = reply_callback or self._default_reply

        # 状态
        self.status = TaskStatus.IDLE
        self.current_agent = 'coordinator_memory'
        self.current_state = 'parse'
        self.requirement = ''
        self.context = {}
        self.history = []

        # 线程同步
        self._resume_event = threading.Event()
        self._user_input = ''
        self._worker_thread = None
        self._lock = threading.Lock()

        # 加载 workflows
        self.workflows = {}
        for name in ['coordinator_memory', 'combat_memory',
                      'numerical_memory', 'executor_memory', 'qa_memory']:
            try:
                wf = _load_workflow(name)
                if wf:
                    self.workflows[name] = wf
            except Exception:
                pass

    def _default_reply(self, user_id, message, card_data=None):
        """默认回复（打印到控制台）。"""
        logger.info(f"[→ {user_id}] {message}")

    # ── 公开接口 ──

    def submit(self, requirement: str):
        """提交新需求（非阻塞）。

        立即返回，任务在后台线程执行。
        """
        with self._lock:
            if self.status == TaskStatus.RUNNING:
                self.reply(self.user_id,
                           "⚠️ 上一个任务还在执行中，请等待完成或发 /reset 重置。")
                return

            self.requirement = requirement
            self.current_agent = 'coordinator_memory'
            self.current_state = 'parse'
            self.status = TaskStatus.RUNNING
            self.context = {}
            self._resume_event.clear()

        self.reply(self.user_id,
                   f"✅ 收到需求，开始处理...\n\n> {requirement}")

        # 后台启动
        self._worker_thread = threading.Thread(
            target=self._run_pipeline,
            daemon=True,
        )
        self._worker_thread.start()

    def resume(self, user_input: str):
        """用户确认/输入后恢复执行。"""
        if self.status != TaskStatus.WAITING_USER:
            # 不在等待状态，当作新需求
            if self.status == TaskStatus.IDLE or self.status == TaskStatus.COMPLETED:
                self.submit(user_input)
            else:
                self.reply(self.user_id,
                           "⚠️ 当前不在等待确认状态。")
            return

        self._user_input = user_input
        self._resume_event.set()

    def reset(self):
        """重置会话。"""
        self.status = TaskStatus.IDLE
        self.current_agent = 'coordinator_memory'
        self.current_state = 'parse'
        self.requirement = ''
        self.context = {}
        self._resume_event.set()  # 唤醒可能在等待的线程
        self.reply(self.user_id, "🔄 会话已重置，请发送新需求。")

    def get_status(self) -> dict:
        return {
            "user_id": self.user_id,
            "status": self.status.value,
            "agent": self.current_agent,
            "state": self.current_state,
            "waiting": self.status == TaskStatus.WAITING_USER,
        }

    # ── 后台执行 ──

    def _run_pipeline(self):
        """后台线程：驱动状态机直到完成。"""
        try:
            self._advance()
        except Exception as e:
            self.status = TaskStatus.ERROR
            logger.error(f"Pipeline 异常: {e}", exc_info=True)
            self.reply(self.user_id,
                       f"❌ 执行异常: {str(e)[:500]}")

    def _advance(self):
        """驱动状态机前进。"""
        max_steps = 30

        for step in range(max_steps):
            if self.status not in (TaskStatus.RUNNING,):
                break

            agent = self.current_agent
            state_name = self.current_state
            workflow = self.workflows.get(agent)

            if not workflow:
                self.reply(self.user_id, f"⚠️ 未找到 {agent} 的 workflow")
                self.status = TaskStatus.ERROR
                break

            # 查状态定义
            state_def = None
            for s in workflow.states:
                if s['name'] == state_name:
                    state_def = s
                    break
            if not state_def:
                self.reply(self.user_id, f"⚠️ 未找到状态 {agent}.{state_name}")
                self.status = TaskStatus.ERROR
                break

            state_type = state_def.get('type', 'llm')
            desc = state_def.get('description', state_name)

            logger.info(f"[{agent}] 进入状态: {state_name} ({state_type})")

            # 执行 on_enter hook
            hook_result = self._run_hook(agent, f"on_enter_{state_name}")

            # ── 根据状态类型处理 ──

            if state_type == 'pause':
                # 发确认卡片，等用户输入
                self.status = TaskStatus.WAITING_USER

                card_data = {
                    "title": f"⏸️ {desc}",
                    "agent": agent,
                    "state": state_name,
                    "buttons": [
                        {"text": "✅ 确认", "value": "确认"},
                        {"text": "❌ 取消", "value": "取消"},
                        {"text": "✏️ 修改", "value": "修改"},
                    ],
                }

                prompt_hint = ''
                if isinstance(hook_result, dict) and 'prompt' in hook_result:
                    prompt_hint = hook_result['prompt']
                elif isinstance(hook_result, str):
                    prompt_hint = hook_result

                msg = f"⏸️ **{desc}**\n\n{prompt_hint}\n\n请回复 确认/取消/修改 来继续。"
                self.reply(self.user_id, msg, card_data=card_data)

                # 阻塞等用户输入
                self._resume_event.wait()
                self._resume_event.clear()

                if self.status != TaskStatus.WAITING_USER:
                    break  # 被 reset 了

                self.status = TaskStatus.RUNNING
                user_input = self._user_input

                if user_input.strip() in ('取消', 'cancel', '/cancel'):
                    self.reply(self.user_id, "🛑 任务已取消。")
                    self.status = TaskStatus.COMPLETED
                    break

                self.context['user_input'] = user_input

                # 执行 on_exit hook
                self._run_hook(agent, f"on_exit_{state_name}")

                # 推进
                if not self._transition(agent, state_name):
                    break

            elif state_type == 'llm':
                # 发进度通知
                self.reply(self.user_id, f"🔄 **{desc}**...")

                # 调 LLM
                result = self._call_llm(agent, state_name)
                self.reply(self.user_id, result)

                # on_exit hook
                self._run_hook(agent, f"on_exit_{state_name}")

                if not self._transition(agent, state_name):
                    break

            elif state_type == 'script':
                self.reply(self.user_id, f"⚙️ **{desc}**...")

                self._run_hook(agent, f"on_exit_{state_name}")

                if state_name == 'done':
                    self.status = TaskStatus.COMPLETED
                    self.reply(self.user_id,
                               "✅ **任务完成！** 所有步骤已执行。")
                    break

                if not self._transition(agent, state_name):
                    break

        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.COMPLETED

    def _call_llm(self, agent_name: str, state_name: str) -> str:
        """调 LLM。"""
        system_prompt = build_system_prompt(
            agent_name, state_name,
            context=self.context,
        )
        user_msg = build_user_message(
            self.requirement,
            data=self.context.get('user_input'),
        )
        try:
            response = llm.chat(system_prompt, user_msg)
            self.context[f'{state_name}_response'] = response
            return response
        except Exception as e:
            return f"❌ LLM 调用失败: {e}"

    def _run_hook(self, agent_name: str, hook_key: str):
        """执行 hook。"""
        workflow = self.workflows.get(agent_name)
        if not workflow or not hasattr(workflow, 'hooks'):
            return None
        hook_ref = workflow.hooks.get(hook_key)
        if not hook_ref:
            return None
        try:
            hook_fn = _load_hook(hook_ref, agent_name)
            if hook_fn:
                return hook_fn(self)
        except Exception as e:
            logger.error(f"Hook {hook_key} 失败: {e}")
            return {"error": str(e)}
        return None

    def _transition(self, agent_name: str, current_state: str) -> bool:
        """推进到下一个状态。"""
        workflow = self.workflows.get(agent_name)
        if not workflow:
            return False
        for t in workflow.transitions:
            if len(t) >= 3 and t[1] == current_state:
                self.current_state = t[2]
                return True
        return False


# ── 多用户管理 ──

_controllers = {}  # user_id → HFSMController
_lock = threading.Lock()


def get_controller(user_id: str, reply_callback=None) -> HFSMController:
    """获取或创建用户控制器。"""
    with _lock:
        if user_id not in _controllers:
            _controllers[user_id] = HFSMController(user_id, reply_callback)
        elif reply_callback:
            _controllers[user_id].reply = reply_callback
    return _controllers[user_id]


def reset_controller(user_id: str):
    """重置用户控制器。"""
    with _lock:
        if user_id in _controllers:
            _controllers[user_id].reset()
            del _controllers[user_id]
