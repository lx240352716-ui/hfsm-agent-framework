# -*- coding: utf-8 -*-
"""
全量检测：项目中是否残留中文字段名 / Pipeline 旧名 / 猜测代码。

用法:
    python tests/test_row6_compliance.py

规则：
  1. .py 文件中不得出现已知的中文字段名字符串（如 'Buff因子', '备注', '自增Id' 等）
  2. .py/.md 文件中不得出现 'Pipeline' 旧类名（done.md 等历史记录除外）
  3. .py 文件中不得出现模糊匹配猜测模式（如 .lower().replace(' ', '')）
  4. .json 配置文件中不得出现中文 value（key 允许中文注释 _comment）
"""

import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 规则定义 ──────────────────────────────────────────

# 已知的中文字段名（Row2），不应出现在代码中
CHINESE_FIELD_NAMES = [
    'Buff因子', '是否为减益buff', '是否可以被净化',
    '行动后生效计数', '行动前生效计数', '生效回合',
    '攻击生效次数', '防御生效次数', '整场战斗中限制生效次数',
    'id叠加的个数限制', '特殊配置数据', '附带关联buff',
    'buff参数1', '参数1升级加成', 'buff时机', 'buff目标',
    'buff条件', 'buff概率', '条件类型', '条件参数', '注释',
    '备注', '自增Id', 'buff分组', 'Unnamed: 0',
]

# Pipeline 旧名检测
PIPELINE_PATTERNS = [
    r'from\s+pipeline\s+import',
    r'Pipeline\.from_json',
    r'PipelineError',
    r'PipelineAbort',
    r'class\s+Pipeline',
]

# 猜测代码模式
GUESS_PATTERNS = [
    r'\.lower\(\)\.replace\(.+\)\s*==',     # 模糊字符串匹配
    r"KEY_COLS_FALLBACK",                     # 已删除的 fallback
    r"'_Buff'\s+not\s+in",                   # 用表名探测数据格式
]

# 排除的目录/文件
EXCLUDE_DIRS = {'__pycache__', '.git', 'vendor', 'archive', 'node_modules'}
EXCLUDE_FILES = {'done.md', 'postmortem_shadow_clone.md', 'daily_20260311.md', 'test_row6_compliance.py'}


def scan_file(filepath, rules, label):
    """扫描单个文件，返回 [(行号, 匹配内容, 规则名)]"""
    hits = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return hits

    for i, line in enumerate(lines, 1):
        # 跳过注释行中的历史记录描述
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            continue
        for pattern in rules:
            if isinstance(pattern, str):
                if pattern in line:
                    hits.append((i, line.strip()[:80], f"{label}: '{pattern}'"))
            else:
                if pattern.search(line):
                    hits.append((i, line.strip()[:80], f"{label}: {pattern.pattern}"))
    return hits


def run_all():
    total_issues = 0
    files_scanned = 0

    print(f"\n{'='*60}")
    print(f"  Row6 合规性全量检测")
    print(f"{'='*60}\n")

    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        # 排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            if fname in EXCLUDE_FILES:
                continue

            filepath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(filepath, PROJECT_ROOT)
            ext = os.path.splitext(fname)[1].lower()

            all_hits = []

            # .py 文件：检查全部规则
            if ext == '.py':
                files_scanned += 1
                all_hits += scan_file(filepath, CHINESE_FIELD_NAMES, '中文字段名')
                all_hits += scan_file(filepath, [re.compile(p) for p in PIPELINE_PATTERNS], 'Pipeline旧名')
                all_hits += scan_file(filepath, [re.compile(p) for p in GUESS_PATTERNS], '猜测代码')

            # .md 文件：只检查 Pipeline 旧名（agent memory 目录下）
            elif ext == '.md' and 'agents' in dirpath:
                files_scanned += 1
                all_hits += scan_file(filepath, [re.compile(p) for p in PIPELINE_PATTERNS], 'Pipeline旧名')

            # .json 配置文件：检查中文 value
            elif ext == '.json' and ('configs' in dirpath or 'memory' in dirpath):
                files_scanned += 1
                all_hits += scan_file(filepath, CHINESE_FIELD_NAMES, '中文字段名')

            if all_hits:
                print(f"❌ {rel_path}")
                for line_no, content, rule in all_hits:
                    print(f"   L{line_no}: {rule}")
                    print(f"         {content}")
                total_issues += len(all_hits)

    print(f"\n{'='*60}")
    print(f"  扫描文件: {files_scanned}")
    print(f"  发现问题: {total_issues}")
    if total_issues == 0:
        print(f"  🎉 全部通过！")
    else:
        print(f"  ❌ 请修复以上问题")
    print(f"{'='*60}\n")

    return total_issues


if __name__ == '__main__':
    issues = run_all()
    exit(1 if issues else 0)
