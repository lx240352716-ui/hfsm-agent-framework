# -*- coding: utf-8 -*-
"""
分层状态机 (HFSM) 引擎骨架

核心概念：
    - State:      状态（系统当前所处的阶段）
    - Event:      事件（触发状态变化的信号）
    - Transition:  转移（从状态A→状态B的路径，含 guard 和 action）
    - Machine:     引擎（管理状态流转的核心）

使用方式：
    machine = Machine("L0_coordinator", initial="parse")
    machine.add_state("parse", on_enter=load_knowledge)
    machine.add_state("split_modules")
    machine.add_transition(
        trigger="parse_done",
        source="parse",
        dest="split_modules",
        guard=lambda ctx: "requirement_type" in ctx,
        action=lambda ctx: print(f"需求类型: {ctx['requirement_type']}")
    )
    machine.send("parse_done", {"requirement_type": "ur_equipment"})

分层嵌套：
    parent = Machine("root", initial="L0")
    child = Machine("L0_coordinator", initial="parse")
    parent.add_child("L0", child)
"""

import json
import os
from datetime import datetime


# ── State ──────────────────────────────────────────

class State:
    """状态定义"""

    def __init__(self, name, on_enter=None, on_exit=None, description=""):
        """
        Args:
            name: 状态名（唯一标识）
            on_enter: 进入状态时的回调 fn(context) -> None
            on_exit: 离开状态时的回调 fn(context) -> None
            description: 人类可读描述
        """
        self.name = name
        self.on_enter = on_enter
        self.on_exit = on_exit
        self.description = description

    def __repr__(self):
        return f"State({self.name})"


# ── Transition ─────────────────────────────────────

class Transition:
    """状态转移定义"""

    def __init__(self, trigger, source, dest, guard=None, action=None, description=""):
        """
        Args:
            trigger: 触发事件名（如 "parse_done", "user_confirmed"）
            source: 源状态名
            dest: 目标状态名
            guard: 守卫条件 fn(context) -> bool，返回 False 则转移不执行
            action: 转移时执行的动作 fn(context) -> None
            description: 人类可读描述
        """
        self.trigger = trigger
        self.source = source
        self.dest = dest
        self.guard = guard
        self.action = action
        self.description = description

    def is_allowed(self, context):
        """检查守卫条件"""
        if self.guard is None:
            return True
        return self.guard(context)

    def __repr__(self):
        return f"Transition({self.source} --[{self.trigger}]--> {self.dest})"


# ── Machine ────────────────────────────────────────

class Machine:
    """
    状态机引擎。

    支持：
        - 状态注册 (add_state)
        - 转移注册 (add_transition)
        - 事件发送 (send) → 查找转移 → 检查守卫 → 执行动作 → 跳转
        - 子状态机嵌套 (add_child)
        - 状态持久化 (save / load)
        - 历史状态 (回退后恢复到上次离开的步骤)
    """

    def __init__(self, name, initial=None, description=""):
        """
        Args:
            name: 状态机名（如 "L0_coordinator"）
            initial: 初始状态名
            description: 人类可读描述
        """
        self.name = name
        self.description = description
        self.initial = initial

        self._states = {}           # {name: State}
        self._transitions = []      # [Transition]
        self._children = {}         # {state_name: Machine} 子状态机
        self._history = {}          # {child_name: last_state} 历史状态

        self.current = None         # 当前状态名
        self.context = {}           # 共享数据上下文
        self.log = []               # 事件日志

    # ── 注册 API ──

    def add_state(self, name, on_enter=None, on_exit=None, description=""):
        """注册一个状态"""
        state = State(name, on_enter=on_enter, on_exit=on_exit, description=description)
        self._states[name] = state
        return self

    def add_transition(self, trigger, source, dest, guard=None, action=None, description=""):
        """注册一个转移"""
        t = Transition(trigger, source, dest, guard=guard, action=action, description=description)
        self._transitions.append(t)
        return self

    def add_child(self, state_name, child_machine):
        """给某个状态注册子状态机（分层嵌套）"""
        self._children[state_name] = child_machine
        return self

    # ── 核心：启动 ──

    def start(self, context=None):
        """启动状态机，进入初始状态"""
        if self.initial is None:
            raise RuntimeError(f"[{self.name}] 未设置初始状态")
        if self.initial not in self._states:
            raise RuntimeError(f"[{self.name}] 初始状态 '{self.initial}' 未注册")

        self.context = context or {}
        self.current = self.initial
        self._log(f"启动 → 进入 '{self.current}'")
        self._enter_state(self.current)

    # ── 核心：发送事件 ──

    def send(self, event, data=None):
        """
        发送事件，触发状态转移。

        Args:
            event: 事件名
            data: 附带数据（合并到 context）

        Returns:
            dict: {"handled": bool, "from": str, "to": str, "machine": str}
        """
        if self.current is None:
            raise RuntimeError(f"[{self.name}] 状态机未启动，请先调用 start()")

        # 合并数据到 context
        if data:
            self.context.update(data)

        # 优先让子状态机处理（事件下沉）
        if self.current in self._children:
            child = self._children[self.current]
            if child.current is not None:
                result = child.send(event, data)
                if result["handled"]:
                    # 子状态机完成？检查是否需要退出子层
                    if child.current is None:  # 子状态机到了终态
                        self._history[self.current] = None
                        # 子完成后，合并子 context 到父
                        self.context.update(child.context)
                        self._log(f"子状态机 '{child.name}' 完成，数据已合并")
                    return result

        # 本层处理
        for t in self._transitions:
            if t.trigger == event and t.source == self.current:
                if t.is_allowed(self.context):
                    return self._execute_transition(t)

        # 未处理 → 事件冒泡（由父层处理）
        self._log(f"事件 '{event}' 在状态 '{self.current}' 无匹配转移")
        return {"handled": False, "machine": self.name, "state": self.current}

    # ── 核心：执行转移 ──

    def _execute_transition(self, transition):
        """执行一次状态转移"""
        old = self.current

        # 1) 退出旧状态
        self._exit_state(old)

        # 2) 执行转移动作
        if transition.action:
            self._log(f"执行动作: {transition.description or transition.trigger}")
            transition.action(self.context)

        # 3) 进入新状态
        self.current = transition.dest
        self._log(f"转移: '{old}' --[{transition.trigger}]--> '{self.current}'")
        self._enter_state(self.current)

        return {
            "handled": True,
            "machine": self.name,
            "from": old,
            "to": self.current,
            "trigger": transition.trigger
        }

    def _enter_state(self, state_name):
        """进入状态：执行 on_enter 回调 + 启动子状态机"""
        state = self._states.get(state_name)
        if state and state.on_enter:
            state.on_enter(self.context)

        # 如果该状态有子状态机，启动它
        if state_name in self._children:
            child = self._children[state_name]
            # 历史状态：恢复上次离开时的状态
            history = self._history.get(state_name)
            if history:
                child.current = history
                self._log(f"恢复子状态机 '{child.name}' 到历史状态 '{history}'")
            else:
                child.start(context=self.context)

    def _exit_state(self, state_name):
        """退出状态：保存子状态机历史 + 执行 on_exit 回调"""
        # 保存子状态机的当前状态为历史
        if state_name in self._children:
            child = self._children[state_name]
            if child.current:
                self._history[state_name] = child.current

        state = self._states.get(state_name)
        if state and state.on_exit:
            state.on_exit(self.context)

    # ── 状态查询 ──

    def status(self):
        """返回当前状态信息"""
        result = {
            "machine": self.name,
            "state": self.current,
            "context_keys": list(self.context.keys()),
        }
        # 子状态机信息
        if self.current in self._children:
            child = self._children[self.current]
            result["child"] = child.status()
        return result

    # ── 持久化 ──

    def save(self, filepath):
        """保存状态到 JSON 文件"""
        data = {
            "machine": self.name,
            "current": self.current,
            "context": self.context,
            "history": self._history,
            "timestamp": datetime.now().isoformat(),
            "children": {}
        }
        for name, child in self._children.items():
            data["children"][name] = {
                "current": child.current,
                "context": child.context,
                "history": child._history,
            }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, filepath):
        """从 JSON 文件恢复状态"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.current = data["current"]
        self.context = data.get("context", {})
        self._history = data.get("history", {})

        for name, child_data in data.get("children", {}).items():
            if name in self._children:
                child = self._children[name]
                child.current = child_data["current"]
                child.context = child_data.get("context", {})
                child._history = child_data.get("history", {})

    # ── 日志 ──

    def _log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{self.name}] {message}"
        self.log.append(entry)
