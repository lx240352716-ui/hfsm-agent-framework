# -*- coding: utf-8 -*-
"""
项目初始化脚本 — 新用户 clone 后运行此脚本完成一键配置。

Usage:
    python scripts/tools/init_project.py

功能：
1. 检查 .env 中 WORKSPACE_DIR 是否已配置
2. 运行 rebuild_registry.py → 生成 table_registry.json
3. 运行 gen_table_dir.py → 生成 table_directory.md
4. 在每个 Agent 的 knowledge/ 下生成带提示注释的空模板
5. 打印 checklist
"""
import os, sys, json, subprocess

# 定位项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..'))

sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'core'))
from constants import (
    BASE_DIR, EXCEL_DIR, REFERENCES_DIR, AGENTS_DIR,
    CONFIGS_DIR, CORE_DIR, DB_PATH
)

# ─── 颜色输出 ────────────────────────────────────────────────
def ok(msg):   print(f"  ✅ {msg}")
def warn(msg): print(f"  ⚠️  {msg}")
def fail(msg): print(f"  ❌ {msg}")
def info(msg): print(f"  ℹ️  {msg}")

# ─── Step 1: 检查 .env ──────────────────────────────────────
print("\n═══ Step 1: 检查环境配置 ═══\n")

env_path = os.path.join(PROJECT_ROOT, '.env')
env_example = os.path.join(PROJECT_ROOT, '.env.example')

if not os.path.exists(env_path):
    if os.path.exists(env_example):
        import shutil
        shutil.copy2(env_example, env_path)
        warn(f".env 不存在，已从 .env.example 复制")
        warn(f"请编辑 {env_path} 填入 WORKSPACE_DIR")
        print(f"\n    打开文件: notepad {env_path}\n")
        sys.exit(1)
    else:
        fail(".env 和 .env.example 都不存在")
        sys.exit(1)

workspace = os.environ.get('WORKSPACE_DIR', '')
if not workspace or workspace.startswith('#'):
    # 重新读 .env
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k.strip() == 'WORKSPACE_DIR' and v.strip():
                    workspace = v.strip()

if not workspace:
    fail("WORKSPACE_DIR 未设置")
    warn(f"请编辑 {env_path}，取消注释并填入你的项目根目录")
    sys.exit(1)

if not os.path.isdir(workspace):
    fail(f"WORKSPACE_DIR 目录不存在: {workspace}")
    sys.exit(1)

ok(f"WORKSPACE_DIR = {workspace}")

# ─── Step 2: 检查 Excel 目录 ────────────────────────────────
print("\n═══ Step 2: 检查 Excel 目录 ═══\n")

if not os.path.isdir(EXCEL_DIR):
    warn(f"Excel 目录不存在: {EXCEL_DIR}")
    info("请创建目录并放入 .xlsx 文件:")
    info(f"  mkdir {EXCEL_DIR}")
    info(f"  # 将 Excel 文件复制到 {EXCEL_DIR}")
    sys.exit(1)

xlsx_count = sum(1 for r, d, fs in os.walk(EXCEL_DIR) 
                 for f in fs if f.endswith('.xlsx') and not f.startswith('~$'))
if xlsx_count == 0:
    warn(f"Excel 目录为空: {EXCEL_DIR}")
    info("请放入 .xlsx 文件后重新运行")
    sys.exit(1)

ok(f"找到 {xlsx_count} 个 Excel 文件")

# ─── Step 3: 生成 table_registry.json ────────────────────────
print("\n═══ Step 3: 生成表注册表 ═══\n")

rebuild_script = os.path.join(SCRIPT_DIR, 'rebuild_registry.py')
result = subprocess.run([sys.executable, rebuild_script], capture_output=True, text=True)
if result.returncode == 0:
    ok("table_registry.json 生成成功")
    for line in result.stdout.strip().split('\n'):
        info(line)
else:
    fail("rebuild_registry.py 执行失败")
    print(result.stderr)
    sys.exit(1)

# ─── Step 4: 生成 table_directory.md ─────────────────────────
print("\n═══ Step 4: 生成表目录文档 ═══\n")

gen_script = os.path.join(SCRIPT_DIR, 'gen_table_dir.py')
if os.path.exists(DB_PATH):
    result = subprocess.run([sys.executable, gen_script], capture_output=True, text=True)
    if result.returncode == 0:
        ok("table_directory.md 生成成功")
        for line in result.stdout.strip().split('\n'):
            info(line)
    else:
        warn("gen_table_dir.py 执行失败（可能需要先导入 Excel 到 SQLite）")
        info(result.stderr[:200] if result.stderr else "无错误输出")
else:
    warn(f"SQLite 数据库不存在: {DB_PATH}")
    info("需要先导入 Excel 到 SQLite，然后重新运行此步骤")
    info(f"  python scripts/tools/gen_table_dir.py")

# ─── Step 5: 生成 Agent 知识模板 ─────────────────────────────
print("\n═══ Step 5: 生成 Agent 知识模板 ═══\n")

# Agent 模板定义：{agent_name: {file: content}}
AGENT_TEMPLATES = {
    'coordinator_memory': {
        'knowledge/coordinator_rules.md': """# 主策划工作规则

> 在此填写你的项目的主策划工作规则。

## 评审标准

<!-- 填写需求评审时的检查要点 -->

## 案例分派规则

<!-- 填写如何将需求分派给不同的子策划 -->

## 会话管理

<!-- 填写会话创建、归档的规则 -->
""",
        'knowledge/coordinator_examples.md': """# 主策划参考案例

> 在此填写你的项目的已完成案例，供后续参考。

## 案例模板

<!-- 
### [案例名称]
- **需求**: 
- **涉及表**: 
- **关键决策**: 
- **结果**: 
-->
""",
    },
    'combat_memory': {
        'knowledge/combat_rules.md': """# 战斗策划规则

> 在此填写你的项目的战斗系统规则。

## 战斗机制概览

<!-- 填写核心战斗机制 -->

## 字段翻译规则

<!-- 填写自然语言 → 配置字段的翻译规则 -->
""",
    },
    'numerical_memory': {
        'knowledge/numerical_rules.md': """# 数值策划规则

> 在此填写你的项目的数值填写规则。

## 填写流程

<!-- 
1. locate — 定位需要填写的表
2. fill — 按规则填写字段
3. validate — 校验填写结果
-->

## 公式和约束

<!-- 填写数值计算公式、取值范围等 -->
""",
        'knowledge/numerical_examples.md': """# 数值填写案例

> 在此填写具体的数值填写案例，格式如下。

<!-- 
### [案例名称]
- **表名**: 
- **填写字段**: 
- **填写值**: 
- **计算过程**: 
-->
""",
    },
    'executor_memory': {
        'knowledge/executor_rules.md': """# 执行策划规则

> 在此填写执行层的工作规则。

## 对齐规则

<!-- 填写如何将设计 JSON 对齐到 Excel 行 -->

## 填写规则

<!-- 填写字段的默认值、必填检查等 -->

## 写入规则

<!-- 填写 staging → output 的转换规则 -->
""",
    },
    'qa_memory': {
        'knowledge/qa_rules.md': """# QA 校验规则

> 在此填写 QA 层的校验规则和业务红线。

## 必检项

<!-- 填写每次都必须检查的项目 -->

## 业务红线

<!-- 填写绝对不允许出错的规则 -->

## 常见错误

<!-- 填写历史上出过的典型错误及解决方案 -->
""",
    },
}

created = 0
skipped = 0
for agent_name, files in AGENT_TEMPLATES.items():
    agent_dir = os.path.join(AGENTS_DIR, agent_name)
    for rel_path, content in files.items():
        full_path = os.path.join(agent_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 只在文件不存在或为空时生成
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                existing = f.read().strip()
            if len(existing) > 50:  # 已有实质内容
                skipped += 1
                continue
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        created += 1

ok(f"生成 {created} 个知识模板，跳过 {skipped} 个已有文件")

# ─── Step 6: 复制 .agents/ 到工作区根目录 ─────────────────────
print("\n═══ Step 6: 安装 AI 工作流 ═══\n")

import shutil

# .agents/ 在 references/ (PROJECT_ROOT) 下，需要复制到 WORKSPACE_DIR/
src_agents = os.path.join(PROJECT_ROOT, '.agents')
dst_agents = os.path.join(workspace, '.agents')

if os.path.isdir(src_agents):
    # 只复制 workflows/ 目录
    src_wf = os.path.join(src_agents, 'workflows')
    dst_wf = os.path.join(dst_agents, 'workflows')
    if os.path.isdir(src_wf):
        os.makedirs(dst_wf, exist_ok=True)
        copied_wf = 0
        for f in os.listdir(src_wf):
            if f.endswith('.md'):
                src_f = os.path.join(src_wf, f)
                dst_f = os.path.join(dst_wf, f)
                shutil.copy2(src_f, dst_f)
                copied_wf += 1
        ok(f"复制 {copied_wf} 个工作流到 {dst_wf}")
        info("编辑器将在此目录发现 /design 等 AI 工作流命令")
    else:
        warn("未找到 .agents/workflows/ 目录")
else:
    warn("未找到 .agents/ 目录（跳过工作流安装）")

# ─── 最终 Checklist ──────────────────────────────────────────
print("\n" + "═" * 50)
print("  🎉 初始化完成！接下来请手动完成：")
print("═" * 50)
print("""
  □ 1. 填写 agents/coordinator_memory/knowledge/ 下的规则文件
  □ 2. 填写 agents/numerical_memory/knowledge/ 下的数值规则和案例
  □ 3. 填写 agents/executor_memory/knowledge/ 下的执行规则
  □ 4. 填写 agents/qa_memory/knowledge/ 下的 QA 校验规则
  □ 5. 填写 agents/combat_memory/knowledge/ 下的战斗规则（如有）
  □ 6. 编辑 scripts/core/constants.py 中的 _PK_HINT 和 REQUIRED_FIELDS

  📖 详见 README.md 第 5 节 "填写知识库"
""")
