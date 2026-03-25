# HFSM Agent Framework

> **用状态机约束 LLM，用 Hook 定义边界，用 JSON 传递数据，用文件持久记忆。**

一个面向 LLM 应用的多 Agent 编排框架。核心设计目标：**控制幻觉**。

## 为什么不用 Pipeline

| 环节 | Pipeline 做法 | 本框架做法 | 原因 |
|:-----|:-------------|:-----------|:-----|
| 流程编排 | LLM 链式串联 | 分层状态机 (HFSM) | 上游幻觉不会传导到下游 |
| 步骤执行 | LLM 自主决定 | Hook 函数约束 | `on_enter` 限输入，`on_exit` 校输出 |
| Agent 通信 | LLM 转述 | JSON 直接交接 | 消除转述失真 |
| 知识管理 | LLM 记忆 | Markdown 文件按需加载 | 文件持久、可编辑、不丢 |

## 框架核心（< 1000 行）

```
hfsm/
├── machine.py       # State / Transition / Machine 引擎
├── config.py        # 项目路径配置（环境变量驱动）
├── hook_utils.py    # JSON/MD 读写 + pending 暂存机制
└── registry.py      # 从 agents.json 自动组装 HFSM
```

## 安装

```bash
pip install git+https://github.com/lx240352716-ui/hfsm-agent-framework.git
```

安装后即可使用 `hfsm` 命令。

## 快速开始

### 方式一：CLI（推荐）

```bash
# 1. 创建新项目
hfsm init my-project
cd my-project

# 2. 添加 Agent
hfsm add-agent my_agent

# 3. 编辑 knowledge 和 hooks（见下方详细说明）

# 4. 运行
hfsm run my_agent
```

### 方式二：Python API

```python
from hfsm.config import Config
from hfsm.registry import build_hfsm

Config.init("/path/to/project")
workflows = build_hfsm()
```

### 定义一个 Agent

每个 Agent 需要：
- `process/xxx_workflow.py` — 状态和转移定义
- `process/xxx_hooks.py` — 每个状态的 Hook 函数
- `knowledge/` — 该 Agent 的领域知识（Markdown）
- `data/` — 运行时工作数据（JSON，可清理）

```python
# agents/my_agent/process/my_workflow.py

states = [
    {"name": "parse",   "type": "script", "description": "解析输入"},
    {"name": "process", "type": "llm",    "description": "LLM 处理"},
    {"name": "output",  "type": "script", "description": "组装输出"},
]

transitions = [
    {"trigger": "parsed",    "source": "parse",   "dest": "process"},
    {"trigger": "processed", "source": "process", "dest": "output"},
]

hooks = {
    "on_enter_parse":   "my_hooks.on_enter_parse",
    "on_exit_process":  "my_hooks.on_exit_process",
    "on_enter_output":  "my_hooks.on_enter_output",
}
```

### 写 Hook 函数

```python
# agents/my_agent/process/my_hooks.py

from hfsm.hook_utils import load_json, save_json, load_md

def on_enter_parse():
    """进入 parse：加载知识 + 读输入"""
    knowledge = load_md(KNOWLEDGE_DIR, 'rules.md')
    input_data = load_json(os.path.join(DATA_DIR, 'input.json'))
    return {"knowledge": knowledge, "input": input_data}

def on_exit_process():
    """退出 process：校验 LLM 输出"""
    result = load_json(os.path.join(DATA_DIR, 'process_result.json'))
    if not result or 'output' not in result:
        raise ValueError("LLM 输出格式不合法")
    return result
```

### 注册配置

```json
// agents.json
{
  "agents": {
    "my_agent": {
      "role": "sub",
      "workflow": "agents/my_agent/process/my_workflow.py"
    }
  }
}
```

## Agent 目录结构约定

```
agents/
└── {agent_name}/
    ├── knowledge/           # 技能系统（按需加载）
    │   ├── rules.md         #   Agent 级规则
    │   ├── examples.md      #   案例（pending 机制自动积累）
    │   └── {state}/         #   状态级知识
    │       ├── rules.md
    │       └── examples.md
    ├── process/             # 流程定义
    │   ├── xxx_workflow.py  #   状态 + 转移 + hooks 映射
    │   └── xxx_hooks.py     #   on_enter_* / on_exit_*
    └── data/                # 运行时数据（可清理）
        ├── input.json
        ├── output.json
        └── pending_examples.json
```

## 关键机制

### Pending 暂存（防止失败污染知识库）

```
任务开始 → init_pending()    清空上次残留
过程中   → append_pending()  追加到 pending_examples.json
任务完成 → commit_pending()  正式写入 knowledge/*.md
任务失败 → pending 被丢弃    知识库不受影响
```

### JSON Handoff（消除 LLM 转述）

Agent 间数据通过 `data/output.json` → 下游 `data/input.json` 直接传递，不经过 LLM 总结。

## 示例

`examples/game_config/` — 游戏配表自动化（5 个 Agent，完整实现）

## License

MIT
