# -*- coding: utf-8 -*-
"""
Wiki 公有知识编译器 -- 从解析缓存中自动提取 entity/concept 交叉引用。

职责：
1. 从 skill.md 加载已知表名集合
2. 从 table_registry.json 提取文件夹/前缀分组 + CN-EN 映射
3. 扫描 .cache/*.md，提取每个表名出现的位置 (entity)，支持中文关键词匹配
4. 扫描 .cache/*.md，提取章节标题的跨文档关联 (concept)
5. 运行 lint 检查（未收录表名、孤立文档等）
6. 生成 knowledge/wiki/ 下的索引文件

Usage:
    from wiki_compiler import compile_wiki
    stats = compile_wiki(cache_dir, knowledge_dir)
"""

import os
import re
import json
import sys
import hashlib
from collections import defaultdict
from datetime import date

# 超过此大小的缓存文件跳过 entity/lint 详细扫描（避免 1MB+ xlsx 卡死）
MAX_SCAN_SIZE = 200 * 1024  # 200KB


# ==============================================================
# 表名词表加载
# ==============================================================

def _load_known_tables(knowledge_dir):
    """从 skill.md 读取已知表名集合。

    skill.md 格式: 在 ## ID / ## Id / ## id 下以 '- TableName' 列出。

    Returns:
        set[str]: 已知表名集合
    """
    skill_path = os.path.join(knowledge_dir, 'skill.md')
    if not os.path.exists(skill_path):
        return set()

    tables = set()
    with open(skill_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('- ') and len(line) > 2:
                name = line[2:].strip()
                # 表名一般是 PascalCase 或 _前缀, 过滤纯中文/数字项
                if name and re.match(r'^[A-Za-z_]', name):
                    tables.add(name)

    return tables


# ==============================================================
# CN-EN 中英映射（文件夹提取 + LLM 翻译 + hash 懒更新）
# ==============================================================

def _extract_table_groups(knowledge_dir):
    """从 table_registry.json 提取文件夹→表名包含关系。

    Returns:
        tuple: (groups, registry_hash)
            groups: {folder_or_prefix: [table_name, ...]}
            registry_hash: str, sha256 of sorted table names
    """
    registry_path = os.path.join(
        knowledge_dir, '..', 'references', 'scripts', 'configs', 'table_registry.json'
    )
    registry_path = os.path.normpath(registry_path)
    if not os.path.exists(registry_path):
        return {}, ''

    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    # 计算 hash
    sorted_names = sorted(registry.keys())
    registry_hash = hashlib.sha256('|'.join(sorted_names).encode()).hexdigest()[:16]

    # 按文件夹分组
    folder_groups = defaultdict(list)  # folder -> [table_names]
    root_tables = []  # 无文件夹的散表

    for table_name, rel_path in registry.items():
        # 路径中有 \\ 表示有文件夹
        parts = rel_path.replace('/', '\\').split('\\')
        if len(parts) > 1:
            folder = parts[0]
            folder_groups[folder].append(table_name)
        else:
            root_tables.append(table_name)

    # 散表按前缀聚合（提取首个大写词作为前缀）
    prefix_groups = defaultdict(list)
    for table in root_tables:
        # PascalCase 拆分: HeroLevel -> Hero, EquipRefine -> Equip
        parts = re.findall(r'[A-Z_][a-z0-9]*', table)
        prefix = parts[0] if parts else table
        # 跳过太短的前缀（单字符无意义）
        if len(prefix) >= 2:
            prefix_groups[prefix].append(table)

    # 合并: 文件夹组 + 前缀组（只保留有 2+ 张表的前缀）
    groups = dict(folder_groups)
    for prefix, tables in prefix_groups.items():
        if len(tables) >= 2 and prefix not in groups:
            groups[prefix] = tables

    return groups, registry_hash


def _build_cn_en_map(wiki_dir, groups, registry_hash, force=False):
    """读取中英映射，检测新增 group 并自动触发翻译脚本。

    映射文件 cn_en_map.json 由 IDE AI 生成/维护，不依赖外部 API。
    当 registry hash 变化或文件缺失时，自动调用 build_cn_en_map.py
    输出结构化翻译指令，让 IDE AI 补全。

    Returns:
        dict: {chinese_keyword: folder_or_prefix}  e.g. {'神秘商店': 'MysteryShop'}
    """
    cache_path = os.path.join(wiki_dir, 'cn_en_map.json')

    # hash 一致且不强制刷新 -> 直接用缓存
    if os.path.exists(cache_path) and not force:
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if cached.get('registry_hash') == registry_hash:
                mapping = cached.get('mapping', {})
                print(f"  [i] Wiki: loaded {len(mapping)} CN-EN terms from cache")
                return mapping
        except Exception:
            pass

    if not groups:
        return {}

    # hash 不一致或无缓存 -> 尝试读旧缓存
    mapping = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            mapping = cached.get('mapping', {})
            translated_en = set(mapping.values())
            new_groups = [g for g in sorted(groups.keys()) if g not in translated_en]
            if not new_groups:
                print(f"  [i] Wiki: loaded {len(mapping)} CN-EN terms (hash stale but complete)")
                return mapping
        except Exception:
            pass

    # 缺失或不完整 -> 调用 build_cn_en_map.py 输出翻译指令
    _trigger_cn_en_build()
    return mapping


def _trigger_cn_en_build():
    """调用 build_cn_en_map.py 输出翻译指令供 IDE AI 执行。"""
    import subprocess
    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_script = os.path.normpath(
        os.path.join(script_dir, '..', 'cli', 'build_cn_en_map.py')
    )
    if os.path.exists(build_script):
        subprocess.run([sys.executable, build_script], cwd=os.path.dirname(script_dir))
    else:
        print(f"  [WARN] build_cn_en_map.py not found at {build_script}")



# ==============================================================
# Entity 扫描
# ==============================================================

def _parse_sections(text):
    """将 markdown 文本拆分为 (章节标题, 章节内容) 列表。

    支持 #, ##, ### 级别标题。

    Returns:
        list[tuple[str, str]]: [(section_title, section_content), ...]
    """
    sections = []
    current_title = '(top)'
    current_lines = []

    for line in text.split('\n'):
        if line.startswith('#') and ' ' in line and not line.startswith('####'):
            # 保存上一章节
            if current_lines:
                sections.append((current_title, '\n'.join(current_lines)))
            current_title = line.lstrip('#').strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 最后一个章节
    if current_lines:
        sections.append((current_title, '\n'.join(current_lines)))

    return sections


def _scan_entity_refs(cache_dir, known_tables, cn_groups=None):
    """扫描缓存文件，返回表名->位置映射。

    用单次扫描提取所有英文词，和已知表名集做交集。
    如果有 cn_groups，同时扫描中文关键词并关联到该组下所有表名。

    Args:
        cn_groups: {chinese_keyword: [table_name, ...]}

    Returns:
        dict: {table_name: [(filename, section_title), ...]}
    """
    entity_refs = defaultdict(list)

    if not os.path.isdir(cache_dir):
        return entity_refs

    # 预编译: 提取所有 英文/下划线 开头的词（表名一般是 PascalCase 或 _前缀）
    word_pattern = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\b')
    # 中文字符检测（用于快速跳过纯 ASCII 章节）
    has_cjk = re.compile(r'[\u4e00-\u9fff]')

    for fname in sorted(os.listdir(cache_dir)):
        if not fname.endswith('.md'):
            continue

        fpath = os.path.join(cache_dir, fname)

        # 跳过超大文件的详细扫描
        if os.path.getsize(fpath) > MAX_SCAN_SIZE:
            continue

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            continue

        # 去掉 .md 后缀得到原始文件名
        doc_name = fname[:-3] if fname.endswith('.md') else fname

        sections = _parse_sections(text)
        for section_title, section_content in sections:
            # Pass 1: 英文表名集合交集
            words_in_section = set(word_pattern.findall(section_content))
            matched_tables = words_in_section & known_tables
            for table in matched_tables:
                ref = (doc_name, section_title)
                if ref not in entity_refs[table]:
                    entity_refs[table].append(ref)

            # Pass 2: 中文关键词匹配（跳过无中文字符的章节）
            if cn_groups:
                combined = section_title + section_content
                if not has_cjk.search(combined):
                    continue
                for cn_word, table_list in cn_groups.items():
                    if cn_word in combined:
                        for table in table_list:
                            ref = (doc_name, section_title)
                            if ref not in entity_refs[table]:
                                entity_refs[table].append(ref)

    return dict(entity_refs)


# ==============================================================
# Concept 扫描
# ==============================================================

def _scan_concept_refs(cache_dir):
    """扫描缓存文件，提取章节标题并建立跨文档关联。

    同名章节标题出现在多个文档中 = 同一个概念。

    Returns:
        dict: {concept_name: [doc_name, ...]}
    """
    concept_docs = defaultdict(list)

    if not os.path.isdir(cache_dir):
        return concept_docs

    # 要过滤的通用标题（无领域意义）
    skip_titles = {
        '(top)', '', 'Sheet1', 'Sheet2', 'Sheet3',
        'Sheet4', 'Sheet5',
    }

    for fname in sorted(os.listdir(cache_dir)):
        if not fname.endswith('.md'):
            continue

        fpath = os.path.join(cache_dir, fname)
        doc_name = fname[:-3] if fname.endswith('.md') else fname

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('# ') or line.startswith('## '):
                        title = line.lstrip('#').strip()
                        if title and title not in skip_titles:
                            if doc_name not in concept_docs[title]:
                                concept_docs[title].append(doc_name)
        except Exception:
            continue

    # 只保留在 2+ 个文档中出现的概念（跨文档关联才有价值）
    cross_doc = {
        concept: docs
        for concept, docs in concept_docs.items()
        if len(docs) >= 2
    }

    return cross_doc


# ==============================================================
# Lint
# ==============================================================

def _run_lint(entity_refs, concept_refs, cache_dir, known_tables):
    """运行知识健康检查。

    concept_refs 由 _scan_concept_refs() 提供（已扫描过跨文档概念），
    本函数直接复用，不再重复扫描。

    Returns:
        dict: {
            'unknown_tables': [(name, docs), ...],
            'orphan_docs': [doc_name, ...],
            'single_source_concepts': int,
        }
    """
    report = {
        'unknown_tables': [],
        'orphan_docs': [],
        'single_source_concepts': 0,
    }

    if not os.path.isdir(cache_dir):
        return report

    # 1. 扫描缓存文件中的 PascalCase 词，找出不在 known_tables 中的
    unknown_counts = defaultdict(set)  # {name: set(doc_names)}
    pascal_pattern = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b')

    # 已引用的文档集合（entity 索引中出现过的）
    referenced_docs = set()
    for refs in entity_refs.values():
        for doc_name, _ in refs:
            referenced_docs.add(doc_name)

    # 也加入 concept 引用的文档
    for docs in concept_refs.values():
        for doc_name in docs:
            referenced_docs.add(doc_name)

    for fname in sorted(os.listdir(cache_dir)):
        if not fname.endswith('.md'):
            continue

        fpath = os.path.join(cache_dir, fname)
        doc_name = fname[:-3] if fname.endswith('.md') else fname

        # 跳过超大文件的 PascalCase 扫描
        if os.path.getsize(fpath) > MAX_SCAN_SIZE:
            if doc_name not in referenced_docs:
                report['orphan_docs'].append(doc_name)
            continue

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            continue

        # 检测未知 PascalCase 表名
        for match in pascal_pattern.finditer(text):
            name = match.group(1)
            if name not in known_tables and len(name) > 4:
                unknown_counts[name].add(doc_name)

        # 2. 孤立文档检测
        if doc_name not in referenced_docs:
            report['orphan_docs'].append(doc_name)

    # 只报告在 2+ 个文档中出现的未知表名（过滤噪音）
    report['unknown_tables'] = [
        (name, sorted(docs))
        for name, docs in sorted(unknown_counts.items())
        if len(docs) >= 2
    ]

    # 3. 利用已有的 concept_refs 计算单源概念数
    # concept_refs 只包含 2+ docs 的概念；总概念数需要扫描文件标题
    # 但为避免重复扫描，这里只统计 concept_refs 中的跨文档概念数作为参考
    report['cross_doc_concepts'] = len(concept_refs)

    return report


# ==============================================================
# 文件生成
# ==============================================================

def _write_entity_index(wiki_dir, entity_refs):
    """生成 wiki/entities.md。"""
    lines = ['# Entity Cross-Reference', '']
    lines.append('> Auto-compiled from gamedocs cache.')
    lines.append('')

    # 按引用文档数降序排列
    sorted_entities = sorted(
        entity_refs.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    for table, refs in sorted_entities:
        lines.append(f'## {table} ({len(refs)} refs)')
        # 按文档分组
        doc_sections = defaultdict(list)
        for doc_name, section in refs:
            doc_sections[doc_name].append(section)

        for doc_name, sections in sorted(doc_sections.items()):
            section_str = ', '.join(s for s in sections if s != '(top)')
            if section_str:
                lines.append(f'- {doc_name} -> {section_str}')
            else:
                lines.append(f'- {doc_name}')

        lines.append('')

    path = os.path.join(wiki_dir, 'entities.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


def _write_concept_index(wiki_dir, concept_refs):
    """生成 wiki/concepts.md。"""
    lines = ['# Concept Cross-Reference', '']
    lines.append('> Auto-compiled. Only concepts appearing in 2+ documents.')
    lines.append('')

    # 按文档数降序排列
    sorted_concepts = sorted(
        concept_refs.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    for concept, docs in sorted_concepts:
        lines.append(f'## {concept} ({len(docs)} docs)')
        for doc in docs:
            lines.append(f'- {doc}')
        lines.append('')

    path = os.path.join(wiki_dir, 'concepts.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


def _write_wiki_index(wiki_dir, entity_refs, concept_refs):
    """生成 wiki/index.md（Agent 消费入口）。"""
    today = date.today().isoformat()
    lines = [
        '# Wiki Knowledge Index',
        f'> Auto-compiled. Last updated: {today}',
        '',
    ]

    # 统计
    all_docs = set()
    for refs in entity_refs.values():
        for doc_name, _ in refs:
            all_docs.add(doc_name)
    for docs in concept_refs.values():
        for doc in docs:
            all_docs.add(doc)

    lines.append(f'## Stats')
    lines.append(f'- {len(all_docs)} documents')
    lines.append(f'- {len(entity_refs)} entities (table names)')
    lines.append(f'- {len(concept_refs)} cross-doc concepts')
    lines.append('')

    # Top entities
    lines.append('## Top Entities')
    top_entities = sorted(
        entity_refs.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:20]
    for table, refs in top_entities:
        doc_names = sorted(set(d for d, _ in refs))
        doc_str = ', '.join(doc_names[:5])
        if len(doc_names) > 5:
            doc_str += f' (+{len(doc_names)-5})'
        lines.append(f'- {table}: {doc_str}')
    lines.append('')

    # Top concepts
    if concept_refs:
        lines.append('## Top Concepts')
        top_concepts = sorted(
            concept_refs.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:15]
        for concept, docs in top_concepts:
            doc_str = ', '.join(docs[:5])
            if len(docs) > 5:
                doc_str += f' (+{len(docs)-5})'
            lines.append(f'- {concept}: {doc_str}')
        lines.append('')

    path = os.path.join(wiki_dir, 'index.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


def _write_lint_report(wiki_dir, lint_result):
    """生成 wiki/lint_report.md。"""
    today = date.today().isoformat()
    lines = [
        '# Wiki Lint Report',
        f'> Generated: {today}',
        '',
    ]

    # 未知表名
    unknown = lint_result.get('unknown_tables', [])
    if unknown:
        lines.append(f'## Unknown Table Names ({len(unknown)})')
        lines.append('> PascalCase words in 2+ docs, not in skill.md')
        lines.append('')
        for name, docs in unknown[:30]:
            lines.append(f'- {name} (in {len(docs)} docs): {", ".join(docs[:3])}')
        lines.append('')

    # 孤立文档
    orphans = lint_result.get('orphan_docs', [])
    if orphans:
        lines.append(f'## Orphan Documents ({len(orphans)})')
        lines.append('> No known entity references found')
        lines.append('')
        for doc in orphans:
            lines.append(f'- {doc}')
        lines.append('')

    # 跨文档概念
    cross = lint_result.get('cross_doc_concepts', 0)
    lines.append(f'## Cross-Doc Concepts: {cross}')
    lines.append('> Section titles appearing in 2+ documents')
    lines.append('')

    if not unknown and not orphans:
        lines.append('[OK] No issues found.')

    path = os.path.join(wiki_dir, 'lint_report.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


# ==============================================================
# 主入口
# ==============================================================

def compile_wiki(cache_dir, knowledge_dir, force=False):
    """编译 wiki 索引。

    Args:
        cache_dir: .cache/ 目录路径
        knowledge_dir: knowledge/ 目录路径
        force: 是否强制重编译（暂留，目前每次都重编译）

    Returns:
        dict: {generated_files, entity_count, concept_count, lint}
    """
    wiki_dir = os.path.join(knowledge_dir, 'wiki')
    os.makedirs(wiki_dir, exist_ok=True)

    # 1. 加载表名词表
    known_tables = _load_known_tables(knowledge_dir)
    print(f"  [i] Wiki: {len(known_tables)} known table names from skill.md")

    # 2. 提取文件夹→表名包含关系 + CN-EN 翻译
    groups, registry_hash = _extract_table_groups(knowledge_dir)
    cn_en_map = _build_cn_en_map(wiki_dir, groups, registry_hash, force=force)
    # 构建 cn_groups: {chinese_keyword: [table_names]}
    cn_groups = {}
    if cn_en_map and groups:
        for cn_word, en_folder in cn_en_map.items():
            if en_folder in groups:
                cn_groups[cn_word] = groups[en_folder]
    if cn_groups:
        print(f"  [i] Wiki: {len(cn_groups)} Chinese keywords for entity matching")

    # 3. Entity 扫描（英文 + 中文）
    entity_refs = _scan_entity_refs(cache_dir, known_tables, cn_groups)
    print(f"  [i] Wiki: {len(entity_refs)} entities referenced in cache")

    # 4. Concept 扫描
    concept_refs = _scan_concept_refs(cache_dir)
    print(f"  [i] Wiki: {len(concept_refs)} cross-doc concepts found")

    # 5. Lint
    lint_result = _run_lint(entity_refs, concept_refs, cache_dir, known_tables)
    if lint_result['unknown_tables']:
        print(f"  [WARN] {len(lint_result['unknown_tables'])} unknown table names in 2+ docs")
    if lint_result['orphan_docs']:
        print(f"  [WARN] {len(lint_result['orphan_docs'])} orphan documents")

    # 6. 生成文件
    files = []
    files.append(_write_entity_index(wiki_dir, entity_refs))
    files.append(_write_concept_index(wiki_dir, concept_refs))
    files.append(_write_wiki_index(wiki_dir, entity_refs, concept_refs))
    files.append(_write_lint_report(wiki_dir, lint_result))

    for f in files:
        print(f"  [OK] {os.path.relpath(f, knowledge_dir)}")

    return {
        'generated_files': len(files),
        'entity_count': len(entity_refs),
        'concept_count': len(concept_refs),
        'lint': lint_result,
    }


# -- CLI --
if __name__ == '__main__':
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
    KNOWLEDGE_DIR = os.path.join(BASE_DIR, 'knowledge')
    CACHE_DIR = os.path.join(KNOWLEDGE_DIR, 'gamedocs', '.cache')

    print("[+] Compiling wiki...")
    stats = compile_wiki(CACHE_DIR, KNOWLEDGE_DIR)
    print(f"\n[OK] Wiki compiled: {stats['entity_count']} entities, "
          f"{stats['concept_count']} concepts, "
          f"{stats['generated_files']} files generated")
