# -*- coding: utf-8 -*-
"""
HFSM 运行时上下文与 Hook 包装器
"""

import json
from pathlib import Path
from .config import Config

class HookContext:
    def __init__(self, agent_name, state_name=None, machine_ctx=None):
        self.agent_name = agent_name
        self.state_name = state_name
        self.data_dir = Config.get_agent_data_dir(agent_name)
        self.knowledge_dir = Config.get_agent_dir(agent_name) / "knowledge"
        self.machine_ctx = machine_ctx or {}

    @property
    def input(self):
        """自动从 data/input.json 加载数据"""
        input_file = self.data_dir / 'input.json'
        if input_file.exists():
            with open(input_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    @property
    def knowledge(self):
        """
        自动加载该 Agent 知识库目录下所有的 .md 文件。
        """
        content = []
        if self.knowledge_dir.exists():
            for md_file in self.knowledge_dir.glob("*.md"):
                with open(md_file, 'r', encoding='utf-8') as f:
                    content.append(f"--- {md_file.name} ---\n{f.read()}")
        return "\n\n".join(content)

    def call_llm(self, prompt, system_prompt=None):
        """预留的 LLM 调用接口"""
        print(f"\n[LLM Call] 使用知识库长度: {len(self.knowledge)} characters")
        print(f"[LLM Call] Prompt: {prompt}")
        return "这是来自 LLM 的模拟回复"

    def get_machine_context(self, key, default=None):
        """获取共享的 machine context 变量"""
        return self.machine_ctx.get(key, default)

    def set_machine_context(self, key, value):
        """设置共享的 machine context 变量"""
        self.machine_ctx[key] = value

def wrap_hook(hook_func, agent_name):
    """
    包装原始的 hook_func，自动注入 HookContext，并自动持久化返回值。
    """
    def wrapper(model=None, *args, **kwargs):
        # 尝试从当前 model 中提取状态名（如果有）
        state_name = getattr(model, 'state', None)
        ctx = HookContext(agent_name, state_name=state_name, machine_ctx=getattr(model, 'context', {}))
        
        # 自动注入 context
        result = hook_func(ctx, *args, **kwargs)
        
        # 自动持久化输出
        if isinstance(result, dict):
            out_file = ctx.data_dir / 'output.json'
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
        return result
    return wrapper
