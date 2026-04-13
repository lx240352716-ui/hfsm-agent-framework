# -*- coding: utf-8 -*-
"""
知识检索基础设施 -- 为 IDE AI 提供知识库访问工具。

架构说明：
  - Python 负责：解析文档 -> 缓存为 markdown -> 提供读取/提取工具
  - IDE AI 负责：理解用户问题 -> 判断相关性 -> 选择文件/章节 -> 回答

工具函数：
  build_manifest()      — 扫描缓存，返回文件清单（文件名+标题列表）
  format_manifest()     — 格式化清单为文本
  read_cached_file()    — 读取指定文件的缓存 markdown
  extract_sections()    — 从大文件中提取指定章节

Usage:
    from knowledge_search import build_manifest, read_cached_file
    manifest = build_manifest()       # IDE AI 看清单
    text = read_cached_file('xxx')    # IDE AI 读文件
"""

import os
import re

# 项目路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
GAMEDOCS_DIR = os.path.join(BASE_DIR, 'knowledge', 'gamedocs')
CACHE_DIR = os.path.join(GAMEDOCS_DIR, '.cache')




# ==============================================================
# 清单构建
# ==============================================================

def build_manifest(cache_dir=None):
    """扫描缓存目录，提取每个文件的标题列表生成摘要清单。

    Returns:
        list[dict]: [{filename, cache_path, size, titles}]
    """
    cdir = cache_dir or CACHE_DIR
    if not os.path.isdir(cdir):
        return []

    manifest = []
    for fname in sorted(os.listdir(cdir)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(cdir, fname)
        size = os.path.getsize(fpath)

        # 提取 ## 标题作为摘要
        titles = []
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('## '):
                        titles.append(line.strip()[3:].strip())
        except Exception:
            continue

        # 去掉 .md 后缀得到原始文件名
        orig_name = fname[:-3] if fname.endswith('.md') else fname
        manifest.append({
            'filename': orig_name,
            'cache_path': fpath,
            'size': size,
            'titles': titles,
        })

    return manifest


def format_manifest(manifest):
    """将清单格式化为文本。"""
    lines = []
    for i, m in enumerate(manifest, 1):
        title_str = ', '.join(m['titles'][:15]) if m['titles'] else '(no sections)'
        if len(m['titles']) > 15:
            title_str += f' ... (+{len(m["titles"])-15})'
        lines.append(f"{i}. {m['filename']} -- {title_str}")
    return '\n'.join(lines)


# ==============================================================
# 章节提取（大文件用）
# ==============================================================


def extract_sections(text, section_names):
    """从 markdown 文本中提取指定章节的内容。"""
    if not section_names:
        return text[:3000]  # fallback: 返回前 3000 字

    parts = re.split(r'^(## .+)$', text, flags=re.MULTILINE)
    result = []

    for i, part in enumerate(parts):
        if part.startswith('## '):
            title = part[3:].strip()
            if title in section_names:
                # 取标题 + 下一个 part 的内容
                content = parts[i + 1] if i + 1 < len(parts) else ''
                result.append(f"## {title}\n{content.strip()}")

    return '\n\n'.join(result) if result else text[:3000]

# ==============================================================
# 文件读取与搜索
# ==============================================================


def get_manifest_text(cache_dir=None):
    """返回格式化的公有知识清单，供注入 agent prompt。

    清单内容很小（~2KB），可在每个 LLM 状态的 on_enter 注入。
    agent 看到清单后，按需调用 read_cached_file() 读取具体文件。

    如果 wiki 索引存在，追加 entity/concept 交叉引用信息。

    Returns:
        str: 格式化的文件清单文本，无缓存时返回空字符串
    """
    manifest = build_manifest(cache_dir)
    if not manifest:
        return ""
    lines = ["[Available gamedocs]"]
    for m in manifest:
        titles = ', '.join(m['titles'][:10]) if m['titles'] else '(no sections)'
        if len(m['titles']) > 10:
            titles += f' ... (+{len(m["titles"])-10})'
        lines.append(f"- {m['filename']} ({m['size']//1024}KB): {titles}")

    # 追加 wiki 索引
    wiki_index = os.path.join(
        os.path.dirname(cache_dir or CACHE_DIR), '..', 'wiki', 'index.md'
    )
    wiki_index = os.path.normpath(wiki_index)
    if os.path.exists(wiki_index):
        try:
            with open(wiki_index, 'r', encoding='utf-8') as f:
                wiki_content = f.read()
            # 截取合理大小，避免 prompt 过大
            if len(wiki_content) > 3000:
                wiki_content = wiki_content[:3000] + '\n...(truncated)'
            lines.append('')
            lines.append(wiki_content)
        except Exception:
            pass

    return '\n'.join(lines)


def read_cached_file(filename, cache_dir=None):
    """读取缓存文件全文。

    Args:
        filename: 原始文件名（如 '荣耀连战.docx'）
        cache_dir: 缓存目录

    Returns:
        str: 缓存的 markdown 文本，文件不存在返回 None
    """
    cdir = cache_dir or CACHE_DIR
    cache_path = os.path.join(cdir, filename + '.md')
    if not os.path.exists(cache_path):
        return None
    with open(cache_path, 'r', encoding='utf-8') as f:
        return f.read()


def search_manifest(query, cache_dir=None):
    """在清单中搜索关键词，返回匹配的文件条目。

    用于快速定位可能相关的文件，实际判断由 IDE AI 完成。

    Returns:
        list[dict]: 匹配的清单条目
    """
    manifest = build_manifest(cache_dir)
    results = []
    for m in manifest:
        searchable = m['filename'] + ' ' + ' '.join(m['titles'])
        if query in searchable:
            results.append(m)
    return results


# == CLI ==
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2 or sys.argv[1] == 'manifest':
        # 打印清单
        m = build_manifest()
        print(f"[i] {len(m)} files in gamedocs cache\n")
        for item in m:
            size_kb = item['size'] // 1024
            n_sections = len(item['titles'])
            print(f"  {item['filename']} ({size_kb}KB, {n_sections} sections)")
            for t in item['titles'][:5]:
                print(f"    - {t}")
            if n_sections > 5:
                print(f"    ... (+{n_sections - 5} more)")

    elif sys.argv[1] == 'read':
        # 读取指定文件
        if len(sys.argv) < 3:
            print("Usage: python knowledge_search.py read <filename>")
            sys.exit(1)
        fname = ' '.join(sys.argv[2:])
        text = read_cached_file(fname)
        if text:
            print(text)
        else:
            print(f"[WARN] file not found in cache: {fname}")

    elif sys.argv[1] == 'sections':
        # 读取指定文件的指定章节
        if len(sys.argv) < 4:
            print("Usage: python knowledge_search.py sections <filename> <section1> [section2] ...")
            sys.exit(1)
        fname = sys.argv[2]
        sections = sys.argv[3:]
        text = read_cached_file(fname)
        if text:
            print(extract_sections(text, sections))
        else:
            print(f"[WARN] file not found in cache: {fname}")

    else:
        print("Commands:")
        print("  python knowledge_search.py manifest          # list all cached files")
        print("  python knowledge_search.py read <filename>   # read full cached file")
        print("  python knowledge_search.py sections <file> <section> ...  # read specific sections")

