# -*- coding: utf-8 -*-
"""
Phase 1 验证脚本 — 测试 LLM 客户端 + Prompt 构建器。

Usage:
    python scripts/tests/test_llm.py

前提：
    .env 中已配置 DASHSCOPE_API_KEY
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from llm_client import LLMClient
from prompt_builder import (
    build_system_prompt,
    build_user_message,
    load_knowledge_files,
    AGENT_ROLES,
)


def test_prompt_builder():
    """测试 Prompt 构建器（不需要 API Key）"""
    print("=" * 50)
    print("Test 1: Prompt Builder")
    print("=" * 50)

    # 1. 角色定义
    assert 'numerical_memory' in AGENT_ROLES
    assert AGENT_ROLES['numerical_memory']['name'] == '数值策划'
    print("  ✅ 角色定义正确")

    # 2. 知识文件加载
    files = load_knowledge_files('coordinator_memory')
    print(f"  ✅ coordinator_memory 加载 {len(files)} 个知识文件")

    # 3. 构建 prompt
    prompt = build_system_prompt(
        'numerical_memory', 'fill',
        context={"table": "_Buff", "ref_id": 10001},
        extra_instructions="输出 JSON 格式",
    )
    assert '数值策划' in prompt
    assert 'fill' in prompt
    assert '_Buff' in prompt
    print(f"  ✅ system prompt 构建成功 ({len(prompt)} 字符)")

    # 4. 用户消息
    msg = build_user_message("新增一个速度 buff", {"buffId": 99999})
    assert '速度 buff' in msg
    assert '99999' in msg
    print(f"  ✅ user message 构建成功")

    print()


def test_llm_client():
    """测试 LLM 客户端（需要 API Key）"""
    print("=" * 50)
    print("Test 2: LLM Client")
    print("=" * 50)

    client = LLMClient()

    if not client.api_key:
        print("  ⚠️  DASHSCOPE_API_KEY 未设置，跳过 API 测试")
        print("  ℹ️  设置方法：在 .env 中添加 DASHSCOPE_API_KEY=sk-xxx")
        return

    print(f"  ℹ️  模型: {client.model}")
    print(f"  ℹ️  地址: {client.base_url}")

    # 简单对话测试
    try:
        response = client.chat(
            system_prompt="你是一个游戏策划助手。回复要简洁。",
            user_message="用一句话解释什么是 Buff",
        )
        print(f"  ✅ API 调用成功")
        print(f"  📝 回复: {response[:100]}...")
    except Exception as e:
        print(f"  ❌ API 调用失败: {e}")
        return

    # JSON 模式测试
    try:
        result = client.chat_json(
            system_prompt="你是一个 JSON 生成器。只返回 JSON，不要其他文字。",
            user_message='生成一个 buff 示例：{"name": "...", "type": "..."}',
        )
        if 'error' not in result:
            print(f"  ✅ JSON 模式成功: {result}")
        else:
            print(f"  ⚠️  JSON 解析失败: {result.get('error')}")
    except Exception as e:
        print(f"  ❌ JSON 模式失败: {e}")

    print()


def test_integration():
    """集成测试：Prompt Builder + LLM Client"""
    print("=" * 50)
    print("Test 3: Integration")
    print("=" * 50)

    client = LLMClient()
    if not client.api_key:
        print("  ⚠️  跳过集成测试（无 API Key）")
        return

    # 使用真实知识库构建 prompt 并调用 LLM
    system_prompt = build_system_prompt('coordinator_memory')
    user_msg = build_user_message("我想新增一个攻击力提升的 buff")

    try:
        response = client.chat(system_prompt, user_msg)
        print(f"  ✅ 集成测试成功")
        print(f"  📝 回复前 200 字: {response[:200]}...")
    except Exception as e:
        print(f"  ❌ 集成测试失败: {e}")

    print()


if __name__ == '__main__':
    test_prompt_builder()
    test_llm_client()
    test_integration()
    print("🎉 Phase 1 测试完成！")
