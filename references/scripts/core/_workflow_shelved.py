# -*- coding: utf-8 -*-
# [SHELVED] 旧 Workflow 框架，已被 hfsm_registry.py (pytransitions) 替代。
# 保留代码供参考，不再使用。
"""
通用 Workflow 框架 — 给 AI agent 的纪律工具。

使用方式:
    from workflow import Workflow
    wf = Workflow.from_json("combat.json")
    wf.advance("split", {"clauses": [...]})
    wf.advance("categorize", {"trigger": [...], ...})

分层嵌套:
    wf = Workflow.from_json("standard.json")
    wf.advance("understand", {...})
    wf.advance("scope", {...})
    # design 步自动进入子 Workflow (combat.json)
    # 后续 advance 透明委托给子 Workflow
    wf.advance("split", {"clauses": [...]})     # → 子 Workflow
    wf.advance("categorize", {...})              # → 子 Workflow
    ...
    # 子 Workflow 完成后，自动退回主 Workflow

设计原则:
    - 不可跳步: advance() 只接受当前步骤名
    - 防死循环: 同一步最多重试 max_retries 次
    - 防幻觉: require_user_confirm 步骤需用户确认后才能继续
    - 强制执行: hook 步骤由系统自动调用，AI 不碰读写代码
    - 分层嵌套: sub_workflow 步骤自动创建子 Workflow，advance/confirm 透明委托
"""

import copy
import json
import os
import importlib
import logging
import uuid
from datetime import datetime
from typing import Callable, Dict, Any, Optional

# ==========================================
# Type Protocols (类型安全契约)
# ==========================================
# Hook 函数标准签名，用于反射调用时的契约约束。
# 任何配置在 json 的 "hook" 字段中的被调函数都必须实现此签名。
HookFn = Callable[[Dict[str, Any], Any], Optional[Dict[str, Any]]]

# ==========================================
# 模块级 Logger 工厂（单例）
# ==========================================
_logger_cache = {}  # {workflow_name: logger}

def _get_workflow_logger(workflow_name):
    """获取或创建工作流专属 logger（同一 name 只挂一次 FileHandler）"""
    if workflow_name in _logger_cache:
        return _logger_cache[workflow_name]
    
    logger = logging.getLogger(f"workflow.{workflow_name}")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        try:
            from constants import OUTPUT_DIR
            log_dir = os.path.join(OUTPUT_DIR, "_logs")
            os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(
                os.path.join(log_dir, f"{workflow_name}_{datetime.now().strftime('%Y%m%d')}.log"),
                encoding='utf-8'
            )
            fh.setFormatter(logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S'
            ))
            logger.addHandler(fh)
        except Exception:
            pass  # 测试环境下 constants 可能不可用，静默降级
    
    _logger_cache[workflow_name] = logger
    return logger

class WorkflowError(Exception):
    """步骤校验失败（可重试）"""
    pass
class WorkflowAbort(Exception):
    """重试超限，必须上报用户"""
    pass


class Step:
    """工作流中的一个步骤。"""

    def __init__(self, name, outputs, inputs=None, description="",
                 require_user_confirm=False, validator=None, hook=None,
                 hook_kwargs=None, sub_workflow=None, sub_workflow_rules=None,
                 input_mapping=None, output_mapping=None):
        """
        Args:
            name: 步骤名（唯一标识）
            outputs: 本步必须产出的 key 列表
            inputs: 需要的上游输出 key 列表（默认无）
            description: 人类可读描述
            require_user_confirm: 是否需要用户确认才能进下一步
            validator: 可选的自定义校验函数 fn(context) -> None, raise on fail
            hook: 自动执行函数路径 "module.function"（如 "executor_hooks.resolve"）。
                  必须实现 HookFn 协议: def fn(input_data: dict, **kwargs) -> dict
                  工作流引擎会自动传入 output 并将其返回值合并。
            hook_kwargs: hook 函数的额外固定参数 dict（如 {"system": "passive_skill"}）
            sub_workflow: 子工作流配置文件名（如 "combat.json"）
            sub_workflow_rules: 条件子工作流规则 [{"when": "expr", "use": "file"}]
            input_mapping: 主→子数据映射 {"主key": "子key"}
            output_mapping: 子→主数据映射 {"子key": "主key"}
        """
        self.name = name
        self.outputs = outputs or []
        self.inputs = inputs or []
        self.description = description
        self.require_user_confirm = require_user_confirm
        self.validator = validator
        self.hook = hook
        self.hook_kwargs = hook_kwargs or {}
        self.sub_workflow = sub_workflow
        self.sub_workflow_rules = sub_workflow_rules or []
        self.input_mapping = input_mapping or {}
        self.output_mapping = output_mapping or {}

    @property
    def has_sub_workflow(self):
        return bool(self.sub_workflow or self.sub_workflow_rules)

    def __repr__(self):
        hook_tag = " [hook]" if self.hook else ""
        confirm = " [需用户确认]" if self.require_user_confirm else ""
        sub = " [子工作流]" if self.has_sub_workflow else ""
        return f"Step({self.name}{confirm}{hook_tag}{sub})"


class Workflow:
    """
    通用工作流：顺序执行、入口/出口校验、用户确认点、分层嵌套。

    状态流转:
        READY -> (advance) -> RUNNING / WAITING_USER_CONFIRM -> ... -> COMPLETED
                           -> IN_SUB_WORKFLOW -> (子完成) -> RUNNING -> ...
    """

    # 状态常量
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_USER_CONFIRM = "WAITING_USER_CONFIRM"
    IN_SUB_WORKFLOW = "IN_SUB_WORKFLOW"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"

    def __init__(self, name, steps, max_retries=3, description="",
                 final_handoff=None):
        """
        Args:
            name: 工作流名（如 "combat_buff"）
            steps: Step 对象列表（按执行顺序）
            max_retries: 同一步最大重试次数
            description: 人类可读描述
            final_handoff: 工作流完成后的交接声明 dict（可选）
        """
        self.name = name
        self.description = description
        self.steps = steps
        self.max_retries = max_retries
        self.final_handoff = final_handoff or {}
        self.trace_id = uuid.uuid4().hex[:8]
        
        # 使用模块级 logger（避免每个实例重复添加 handler）
        self.logger = _get_workflow_logger(self.name)

        self.context = {}       # 累积的所有数据
        self.current = 0        # 当前步骤索引
        self.retries = [0] * len(steps)  # 每步重试计数
        self.log = []           # 执行日志
        self.state = self.READY
        self._user_confirmed = True  # 初始不需要确认
        self._active_sub = None     # 当前活跃的子 Workflow

    # ── 核心方法 ──────────────────────────────────────

    def confirm(self):
        """用户确认当前等待步骤，解锁下一步。"""
        # 透明委托：子 Workflow 需要确认时，转发给子 Workflow
        if self.state == self.IN_SUB_WORKFLOW and self._active_sub:
            if self._active_sub.state == self.WAITING_USER_CONFIRM:
                result = self._active_sub.confirm()
                # 子 Workflow 确认后检查是否完成
                if self._active_sub.state == self.COMPLETED:
                    self._finish_sub_workflow()
                return self.status()

        if self.state != self.WAITING_USER_CONFIRM:
            raise WorkflowError(
                f"当前状态是 {self.state}，不需要确认"
            )
        step = self.steps[self.current - 1]  # 已 advance 过，current 已 +1
        self._user_confirmed = True

        # 确认后，检查下一步是否要进入子 Workflow
        if self.current < len(self.steps):
            next_step = self.steps[self.current]
            if next_step.has_sub_workflow:
                self._enter_sub_workflow(next_step)
            else:
                self.state = self.RUNNING
        else:
            self.state = self.COMPLETED

        self._log(f"用户已确认 '{step.name}'")
        return self.status()

    def advance(self, step_name, output):
        """
        推进一步。支持透明委托——如果处于 IN_SUB_WORKFLOW 状态，
        调用会自动转发给子 Workflow。

        Args:
            step_name: 当前步骤名（必须与当前步骤匹配）
            output: 本步产出的 dict

        Returns:
            dict: 当前状态信息

        Raises:
            WorkflowError: 校验失败（可重试）
            WorkflowAbort: 重试超限（必须上报）
        """
        # ── 透明委托：IN_SUB_WORKFLOW 时转发给子 Workflow ──
        if self.state == self.IN_SUB_WORKFLOW and self._active_sub:
            result = self._active_sub.advance(step_name, output)
            # 子 Workflow 完成后，自动退出
            if self._active_sub.state == self.COMPLETED:
                self._finish_sub_workflow()
            return self.status()

        # ── 以下是主 Workflow 正常逻辑 ──

        # 状态检查
        if self.state == self.COMPLETED:
            raise WorkflowError("工作流已完成，不能再 advance")
        if self.state == self.ABORTED:
            raise WorkflowError("工作流已中止，不能再 advance")
        if self.state == self.WAITING_USER_CONFIRM:
            raise WorkflowError(
                f"等待用户确认 '{self.steps[self.current - 1].name}' 的结果，"
                f"请先调用 confirm()"
            )

        # 不可跳步
        if self.current >= len(self.steps):
            raise WorkflowError("所有步骤已完成")

        step = self.steps[self.current]
        if step_name != step.name:
            raise WorkflowError(
                f"当前应执行 '{step.name}'，你传了 '{step_name}'。"
                f"不可跳步。"
            )

        # 重试限制
        self.retries[self.current] += 1
        if self.retries[self.current] > self.max_retries:
            self.state = self.ABORTED
            raise WorkflowAbort(
                f"'{step.name}' 已重试 {self.max_retries} 次仍未通过，"
                f"请上报用户处理。"
            )

        # 入口校验：上游输出是否齐全
        missing_inputs = [k for k in step.inputs if k not in self.context]
        if missing_inputs:
            raise WorkflowError(
                f"'{step.name}' 所需的上游数据缺失: {missing_inputs}"
            )

        # 出口校验：本步输出是否齐全
        if not isinstance(output, dict):
            raise WorkflowError(
                f"output 必须是 dict，收到 {type(output).__name__}"
            )
        missing_outputs = [k for k in step.outputs if k not in output]
        if missing_outputs:
            raise WorkflowError(
                f"'{step.name}' 输出不完整，缺: {missing_outputs}"
            )

        # 空值检查
        empty_outputs = [k for k in step.outputs
                         if output.get(k) is None
                         or (isinstance(output.get(k), (list, dict, str))
                             and len(output.get(k)) == 0)]
        if empty_outputs:
            raise WorkflowError(
                f"'{step.name}' 输出为空: {empty_outputs}"
            )

        # 自定义校验
        merged = {**self.context, **output}
        if step.validator:
            step.validator(merged)

        # ── Hook 自动执行 ──
        hook_result = None
        if step.hook:
            self._log(f"执行 hook: {step.hook}")
            hook_fn = self._resolve_hook(step.hook)
            hook_kwargs = {**step.hook_kwargs, '_workflow_ctx': self}
            hook_result = hook_fn(output, **hook_kwargs)
            # hook 的返回值合并到 output 中
            if isinstance(hook_result, dict):
                output.update(hook_result)

        # 全部通过 → 合并数据、推进
        self.context.update(output)
        self._log(f"完成 '{step.name}' → 输出: {list(output.keys())}")
        self.current += 1

        # 判断下一状态
        if step.require_user_confirm:
            self.state = self.WAITING_USER_CONFIRM
            self._user_confirmed = False
        elif self.current >= len(self.steps):
            self.state = self.COMPLETED
        else:
            # 检查下一步是否需要进入子 Workflow
            next_step = self.steps[self.current]
            if next_step.has_sub_workflow:
                self._enter_sub_workflow(next_step)
            else:
                self.state = self.RUNNING

        result = self.status()
        if hook_result is not None:
            result["hook_result"] = hook_result
        return result

    # ── 子 Workflow 管理 ──────────────────────────────

    def _resolve_sub_workflow_config(self, step):
        """根据 step 配置和当前 context 确定子 Workflow 配置文件。"""
        # 优先按条件规则匹配
        for rule in step.sub_workflow_rules:
            when = rule.get("when", "")
            # 简单的 key == value 表达式求值
            if "==" in when:
                key, val = [s.strip().strip("'\"") for s in when.split("==")]
                if str(self.context.get(key, "")) == val:
                    return rule["use"]
        # 回退到默认
        if step.sub_workflow:
            return step.sub_workflow
        raise WorkflowError(
            f"'{step.name}' 配置了子工作流规则，但没有匹配的条件，"
            f"也没有默认 sub_workflow。context keys: {list(self.context.keys())}"
        )

    def _enter_sub_workflow(self, step):
        """创建并进入子 Workflow。"""
        config_file = self._resolve_sub_workflow_config(step)
        sub = Workflow.from_json(config_file)

        # 通过 input_mapping 注入主 context 数据到子 Workflow
        for parent_key, child_key in step.input_mapping.items():
            if parent_key in self.context:
                sub.context[child_key] = self.context[parent_key]

        self._active_sub = sub
        self.state = self.IN_SUB_WORKFLOW
        self._log(f"进入子工作流 '{sub.name}' (配置: {config_file})")

    def _finish_sub_workflow(self):
        """子 Workflow 完成后，提取输出并恢复主流程。"""
        sub = self._active_sub
        step = self.steps[self.current]  # 当前主步骤（带 sub_workflow 的那个）

        # 通过 output_mapping 把子 Workflow 输出映射回主 context
        for child_key, parent_key in step.output_mapping.items():
            if child_key in sub.context:
                self.context[parent_key] = sub.context[child_key]

        # 记录子 Workflow 的 final_handoff（如果有）
        handoff_info = None
        if sub.final_handoff:
            handoff_info = sub.final_handoff
            self._log(f"子工作流交接: {handoff_info}")

        self._log(f"退出子工作流 '{sub.name}'，输出已映射回主流程")
        self._active_sub = None

        # 推进主流程
        self.current += 1
        if step.require_user_confirm:
            self.state = self.WAITING_USER_CONFIRM
            self._user_confirmed = False
        elif self.current >= len(self.steps):
            self.state = self.COMPLETED
        else:
            # 检查下一步是否也是子 Workflow
            next_step = self.steps[self.current]
            if next_step.has_sub_workflow:
                self._enter_sub_workflow(next_step)
            else:
                self.state = self.RUNNING

    # ── 查询方法 ──────────────────────────────────────

    def status(self):
        """返回当前状态信息。"""
        result = {
            "workflow": self.name,
            "state": self.state,
            "completed_steps": [s.name for s in self.steps[:self.current]],
            "total_steps": len(self.steps),
        }

        # 子 Workflow 状态
        if self.state == self.IN_SUB_WORKFLOW and self._active_sub:
            sub_status = self._active_sub.status()
            result["sub_workflow_status"] = sub_status
            # 透传子 Workflow 的 waiting_confirm_for
            if self._active_sub.state == self.WAITING_USER_CONFIRM:
                result["waiting_confirm_for"] = sub_status.get("waiting_confirm_for")
                result["review_text"] = sub_status.get("review_text")

        # 主 Workflow 等待确认
        elif self.state == self.WAITING_USER_CONFIRM:
            step = self.steps[self.current - 1]
            result["waiting_confirm_for"] = step.name
            result["review_text"] = self.format_for_review(step.name)

        # 下一步信息
        if self.state == self.IN_SUB_WORKFLOW and self._active_sub:
            sub_status = self._active_sub.status()
            if "next_step" in sub_status:
                result["next_step"] = sub_status["next_step"]
                result["next_step_needs"] = sub_status.get("next_step_needs", [])
        elif self.current < len(self.steps):
            next_step = self.steps[self.current]
            result["next_step"] = next_step.name
            result["next_step_needs"] = next_step.inputs

        # SYSTEM_HANDOFF: 工作流完成且有交接声明
        if self.state == self.COMPLETED and self.final_handoff:
            result["SYSTEM_HANDOFF"] = {
                "status": "PAUSED_FOR_ROLE_SWITCH",
                "hand_to": self.final_handoff.get("role", "UNKNOWN"),
                "action": self.final_handoff.get("action", ""),
            }

        return result

    def format_for_review(self, step_name=None):
        """
        把当前步骤的输出渲染为人类友好的 Markdown 格式。

        用于 WAITING_USER_CONFIRM 时展示给用户，替代原始 JSON。

        Args:
            step_name: 指定要展示的步骤输出（默认展示最近完成的步骤）

        Returns:
            str: Markdown 格式的确认文本
        """
        if step_name is None and self.current > 0:
            step_name = self.steps[self.current - 1].name

        # 找到该步骤定义的输出 keys
        step = None
        for s in self.steps:
            if s.name == step_name:
                step = s
                break

        lines = [f"## 请确认: {step_name}"]
        if step:
            lines.append(f"> {step.description}")
        lines.append("")

        # 遍历该步骤的输出
        output_keys = step.outputs if step else []
        for key in output_keys:
            val = self.context.get(key)
            if val is None:
                continue

            lines.append(f"### {key}")

            if isinstance(val, list):
                if len(val) == 0:
                    lines.append("（空）")
                elif isinstance(val[0], dict):
                    # list of dicts → Markdown 表格
                    headers = list(val[0].keys())
                    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                    lines.append("| " + " | ".join("---" for _ in headers) + " |")
                    for row in val:
                        cells = [str(row.get(h, "")) for h in headers]
                        lines.append("| " + " | ".join(cells) + " |")
                else:
                    # list of primitives → 编号列表
                    for i, item in enumerate(val, 1):
                        lines.append(f"{i}. {item}")

            elif isinstance(val, dict):
                # dict → key-value 表格
                lines.append("| 字段 | 值 |")
                lines.append("| --- | --- |")
                for k, v in val.items():
                    lines.append(f"| {k} | {v} |")

            else:
                lines.append(str(val))

            lines.append("")

        return "\n".join(lines)

    def summary(self):
        """人类可读的进度报告。"""
        lines = [f"📋 Workflow: {self.name}",
                 f"   状态: {self.state}",
                 f"   进度: {self.current}/{len(self.steps)}",
                 ""]

        for i, step in enumerate(self.steps):
            if i < self.current:
                mark = "[OK]"
            elif i == self.current:
                if self.state == self.IN_SUB_WORKFLOW:
                    mark = "🔄"
                elif self.state == self.WAITING_USER_CONFIRM and i == self.current - 1:
                    mark = "🔔"
                else:
                    mark = "👉"
            else:
                mark = "⬜"
            confirm_tag = " [需确认]" if step.require_user_confirm else ""
            sub_tag = " [子工作流]" if step.has_sub_workflow else ""
            lines.append(f"   {mark} {i+1}. {step.name}{confirm_tag}{sub_tag} — {step.description}")

        # 如果在子工作流中，显示子流程进度
        if self.state == self.IN_SUB_WORKFLOW and self._active_sub:
            lines.append("")
            lines.append(f"   ┗━ 子工作流进度:")
            sub_summary = self._active_sub.summary()
            for line in sub_summary.split("\n"):
                lines.append(f"      {line}")

        if self.log:
            lines.append("")
            lines.append("   日志（最近3条）:")
            for entry in self.log[-3:]:
                lines.append(f"     {entry}")

        return "\n".join(lines)

    # ── 序列化 ────────────────────────────────────────

    @classmethod
    def from_json(cls, path):
        """从 JSON 定义文件加载 Workflow。

        Args:
            path: JSON 文件路径（绝对路径或相对于 configs/workflows/ 目录）

        Returns:
            Workflow 实例
        """
        # 如果是相对路径，相对于 configs/workflows/ 目录
        if not os.path.isabs(path):
            scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(scripts_dir, 'configs', 'workflows', path)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        steps = []
        for s in data["steps"]:
            steps.append(Step(
                name=s["name"],
                outputs=s.get("outputs", []),
                inputs=s.get("inputs", []),
                description=s.get("description", ""),
                require_user_confirm=s.get("require_user_confirm", False),
                hook=s.get("hook"),
                hook_kwargs=s.get("hook_kwargs", {}),
                sub_workflow=s.get("sub_workflow"),
                sub_workflow_rules=s.get("sub_workflow_rules", []),
                input_mapping=s.get("input_mapping", {}),
                output_mapping=s.get("output_mapping", {}),
            ))

        return cls(
            name=data["name"],
            steps=steps,
            max_retries=data.get("max_retries", 3),
            description=data.get("description", ""),
            final_handoff=data.get("final_handoff"),
        )

    # ── 内部方法 ──────────────────────────────────────

    def _log(self, message):
        """内部记录日志，使用 logging 模块落地"""
        self.logger.info(message)
        # 为了向前兼容及前端展示，依然保留内存列表
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] [{self.trace_id}] {message}")

    @staticmethod
    def _resolve_hook(hook_path):
        """解析 hook 路径为可调用函数。

        Args:
            hook_path: "module.function" 格式，如 "executor_hooks.resolve"

        Returns:
            callable
        """
        parts = hook_path.rsplit('.', 1)
        if len(parts) != 2:
            raise WorkflowError(f"hook 格式错误: '{hook_path}'，应为 'module.function'")
        mod_name, fn_name = parts

        # 额外搜索路径：agents/执行策划/ 和 scripts/core/
        import sys
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        extra_paths = [
            os.path.join(base, 'agents', '执行策划'),
            os.path.join(base, 'scripts', 'core'),
            os.path.join(base, 'scripts', 'combat'),
        ]
        for p in extra_paths:
            if p not in sys.path:
                sys.path.insert(0, p)

        try:
            mod = importlib.import_module(mod_name)
        except ImportError as e:
            raise WorkflowError(f"hook 模块加载失败: {mod_name} → {e}")
        fn = getattr(mod, fn_name, None)
        if fn is None:
            raise WorkflowError(f"hook 函数不存在: {mod_name}.{fn_name}")
        return fn
