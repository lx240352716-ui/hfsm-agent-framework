# -*- coding: utf-8 -*-
"""
全量检测：MD 文档中引用的文件/路径是否真实存在。

用法:
    python tests/test_stale_refs.py

规则：
  1. .md 中的代码示例 import 语句引用的模块必须存在
  2. .md 中 from_json("xxx.json") 引用的 JSON 必须存在
  3. .md 中明确引用的 .py / .md / .json 文件必须存在（排除示例占位符）
"""

import os
import re

PROJECT_ROOT = REFERENCES_DIR
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'agents')

# 已知的搜索路径（import 时 Python 会查找的目录）
PYTHON_SEARCH_PATHS = [
    os.path.join(SCRIPTS_DIR, 'core'),
    os.path.join(SCRIPTS_DIR, 'combat'),
    os.path.join(SCRIPTS_DIR, 'workflow'),
    os.path.join(SCRIPTS_DIR, 'tools'),
    os.path.join(SCRIPTS_DIR, 'cli'),
]

# JSON 文件可能存在的目录
JSON_SEARCH_PATHS = [
    os.path.join(SCRIPTS_DIR, 'configs'),
    os.path.join(SCRIPTS_DIR, 'configs', 'workflows'),
    os.path.join(SCRIPTS_DIR, 'configs', 'pipelines'),
    os.path.join(SCRIPTS_DIR, 'configs', 'rules'),
    os.path.join(SCRIPTS_DIR, 'core'),
]

# 排除
EXCLUDE_DIRS = {'__pycache__', '.git', 'vendor', 'archive', 'node_modules'}
EXCLUDE_FILES = {'done.md', 'test_stale_refs.py'}

# 排除的已知占位符/示例
KNOWN_PLACEHOLDERS = {
    'combat_fill',  # 函数名不是模块名
    'excel_writer', 'db_writer',  # 可能已合并
}


def find_module(name):
    """检查 Python 模块是否存在于搜索路径中"""
    for d in PYTHON_SEARCH_PATHS:
        if os.path.exists(os.path.join(d, f'{name}.py')):
            return True
    return False


def find_json(name):
    """检查 JSON 文件是否存在于搜索路径中"""
    for d in JSON_SEARCH_PATHS:
        if os.path.exists(os.path.join(d, name)):
            return True
    # 也在 agents 子目录中搜索
    for dirpath, _, filenames in os.walk(AGENTS_DIR):
        if name in filenames:
            return True
    return False


def find_file_ref(name, source_dir):
    """检查引用的文件是否存在（相对于源文件目录或项目根目录）"""
    # 相对于源文件
    if os.path.exists(os.path.join(source_dir, name)):
        return True
    # 相对于项目根目录
    if os.path.exists(os.path.join(PROJECT_ROOT, name)):
        return True
    # 全局搜索
    for dirpath, _, filenames in os.walk(PROJECT_ROOT):
        if any(d in dirpath for d in EXCLUDE_DIRS):
            continue
        if os.path.basename(name) in filenames:
            return True
    return False


def scan_md(filepath):
    """扫描 MD 文件中的引用"""
    hits = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return hits

    for i, line in enumerate(lines, 1):
        # 1. from xxx import / import xxx（在代码块中）
        m = re.search(r'(?:from|import)\s+(\w+)\s+import', line)
        if m:
            mod = m.group(1)
            if mod not in KNOWN_PLACEHOLDERS and not find_module(mod):
                # 跳过标准库
                try:
                    __import__(mod)
                    continue
                except ImportError:
                    pass
                hits.append((i, f"import '{mod}' — 模块不存在", line.strip()[:80]))

        # 2. from_json("xxx.json") 或 Pipeline/Workflow.from_json
        m = re.search(r'from_json\(["\']([^"\']+\.json)["\']', line)
        if m:
            json_name = m.group(1)
            if not find_json(json_name):
                hits.append((i, f"from_json('{json_name}') — JSON 不存在", line.strip()[:80]))

        # 3. 明确的文件引用：`xxx.py`、`xxx.md`、`xxx.json`
        for m in re.finditer(r'`([^`]+\.(?:py|md|json))`', line):
            ref = m.group(1)
            # 跳过路径式引用（如 scripts/core/xxx.py）和通配符
            basename = os.path.basename(ref)
            if '*' in ref or '{' in ref:
                continue
            source_dir = os.path.dirname(filepath)
            if not find_file_ref(basename, source_dir):
                hits.append((i, f"引用 `{ref}` — 文件不存在", line.strip()[:80]))

    return hits


def run_all():
    total_issues = 0
    files_scanned = 0

    print(f"\n{'='*60}")
    print(f"  MD 文档引用存在性检测")
    print(f"{'='*60}\n")

    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for fname in filenames:
            if fname in EXCLUDE_FILES:
                continue
            if not fname.endswith('.md'):
                continue

            filepath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(filepath, PROJECT_ROOT)
            files_scanned += 1

            all_hits = scan_md(filepath)
            if all_hits:
                print(f"❌ {rel_path}")
                for line_no, desc, content in all_hits:
                    print(f"   L{line_no}: {desc}")
                    print(f"         {content}")
                total_issues += len(all_hits)

    print(f"\n{'='*60}")
    print(f"  扫描 MD 文件: {files_scanned}")
    print(f"  发现问题: {total_issues}")
    if total_issues == 0:
        print(f"  🎉 全部通过！")
    else:
        print(f"  ❌ 请检查以上引用")
    print(f"{'='*60}\n")

    return total_issues


if __name__ == '__main__':
    issues = run_all()
    exit(1 if issues else 0)
