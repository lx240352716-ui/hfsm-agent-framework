# HFSM Agent Framework

> 基于分层有限状态机 (HFSM) 的多 Agent 协作框架，用于 Excel 配置表的自动化填写。

## 快速上手

### 1. 安装

```bash
git clone https://github.com/lx240352716-ui/hfsm-agent-framework.git
cd hfsm-agent-framework
pip install -e .
```

> **Windows PATH 问题**：如果 `hfsm` 命令不可用，可能是 pip scripts 目录不在 PATH 中。  
> 解决方案（任选一种）：
> ```powershell
> # 方案 A：手动添加 PATH（推荐）
> $env:PATH += ";$env:APPDATA\Python\Python3x\Scripts"
> # 永久生效：在系统环境变量中添加上述路径
>
> # 方案 B：直接用 python -m 调用
> python -m hfsm_agent_framework.cli <command>
>
> # 方案 C：查看 pip 安装位置
> pip show hfsm-agent-framework  # 查看 Location 字段
> ```

### 2. 配置工作目录

```bash
# 复制 .env 模板并填入你的项目根目录
cp .env.example .env
# 编辑 .env，设置 WORKSPACE_DIR
```

`.env` 文件内容：
```ini
# 项目工作区根目录（必填）
WORKSPACE_DIR=G:\your_project
```

### 3. 放置 Excel 文件

```
<WORKSPACE_DIR>/
├── excel/              ← 所有 Excel 源文件放这里
│   ├── fight/          ← 按功能分子目录
│   │   ├── FightBuff.xlsx
│   │   ├── Skill.xlsx
│   │   └── ...
│   ├── recruit/
│   └── ...
└── references/         ← 本框架的内容（clone 到这里）
```

**约定**：
- Excel 源文件统一放在 `WORKSPACE_DIR/excel/` 目录下
- 可按功能模块建子目录（如 `fight/`, `recruit/`）
- 首次放置后运行 `python scripts/tools/rebuild_registry.py` 生成表注册表

### 4. 生成表注册表

```bash
python scripts/tools/rebuild_registry.py
```

这会扫描 `excel/` 目录，生成 `scripts/configs/table_registry.json`。

### 5. 填写知识库

每个 Agent 的 `knowledge/` 目录需要填入你项目的领域知识：

| Agent | 知识目录 | 需要填什么 |
|-------|---------|-----------|
| coordinator_memory | `knowledge/coordinator_rules.md` | 主策划工作规则、评审标准 |
| combat_memory | `knowledge/understand/`, `knowledge/translate/` | 游戏战斗机制、字段翻译规则 |
| numerical_memory | `knowledge/numerical_rules.md`, `knowledge/fill/` | 数值填写规则、公式、案例 |
| executor_memory | `knowledge/executor_rules.md`, `knowledge/fill/` | 执行层规则、Sheet 页索引 |
| qa_memory | `knowledge/qa_rules.md` | QA 校验规则、业务红线 |

> 每个 knowledge 目录下有 `.md` 文件，保留了标题结构，清空了项目特定内容。  
> 按格式填入你自己的项目知识即可。

### 6. 运行

```bash
# 启动状态机
python scripts/core/hfsm_bootstrap.py
```

---

## 目录结构

```
hfsm-agent-framework/
├── .env                  ← 环境变量（WORKSPACE_DIR）
├── agents.json           ← Agent 注册配置
├── agents/               ← Agent 角色系统
│   ├── coordinator_memory/  ← 主策划 (L0)
│   ├── combat_memory/       ← 战斗策划 (L1)
│   ├── numerical_memory/    ← 数值策划 (L1)
│   ├── executor_memory/     ← 执行策划 (L2)
│   └── qa_memory/           ← QA (L3)
├── scripts/              ← Python 脚本
│   ├── core/             ← HFSM 引擎 + 核心工具
│   ├── configs/          ← JSON 配置（工作流、规则）
│   ├── tools/            ← 通用工具脚本
│   ├── tests/            ← 测试脚本
│   ├── cli/              ← 命令行工具
│   ├── combat/           ← 战斗校验
│   └── workflow/         ← Agent 间交接
├── design/               ← 设计参考文档
├── domains/              ← 功能域知识
└── mapping/              ← 表间关系
```

每个 Agent 统一三层目录：
```
agent_name/
├── knowledge/    ← 领域知识（MD 文件）
├── process/      ← 工作流定义 + Hook 函数
└── data/         ← 运行时数据（.gitignore 排除）
```

> 详细目录说明见 [`project_map.md`](project_map.md)

---

## 核心概念

- **HFSM**：分层有限状态机，驱动多 Agent 协作
- **Agent**：每个角色（主策划/数值/执行/QA）有独立知识库和工作流
- **Hook**：每个工作流步骤的回调函数，实现具体业务逻辑
- **constants.py**：所有路径集中管理，通过 `WORKSPACE_DIR` 环境变量适配不同环境

---

## 自定义

### 添加新 Agent

1. 创建目录：`agents/<agent_name>/{knowledge, process, data}/`
2. 编写工作流：`process/<agent_name>_workflow.py`
3. 编写 Hook：`process/<agent_name>_hooks.py`
4. 注册到 `agents.json`
5. 在 `scripts/core/hfsm_registry.py` 中添加注册

### 添加项目特定常量

编辑 `scripts/core/constants.py`：
- `_PK_HINT`：表主键映射（自动推断失败时的 fallback）
- `REQUIRED_FIELDS`：必填字段契约

---

## License

MIT
