# -*- coding: utf-8 -*-
"""
知识库统一 CLI -- 两级混合检索入口。

搜索流程：
  1. grep knowledge/*.md（关键词匹配优先知识）
  2. gamedocs 缓存文件匹配（替代 FTS5）

命令：
  python knowledge_cli.py ingest              # 全量摄入
  python knowledge_cli.py ingest --path FILE  # 增量摄入
  python knowledge_cli.py search "关键词"      # 两级搜索
  python knowledge_cli.py stats               # 查看统计
"""

import os
import sys
import argparse
import glob

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'core'))
sys.path.insert(0, CORE_DIR)

from knowledge_index import build_index, get_stats
from knowledge_search import search_manifest, read_cached_file

_BASE_DIR = os.environ.get('WORKSPACE_DIR') or os.path.normpath(
    os.path.join(SCRIPT_DIR, '..', '..', '..')
)
_KNOWLEDGE_DIR = os.path.join(_BASE_DIR, 'knowledge')


# ══════════════════════════════════════════════════════════════
# L1: 优先知识搜索（grep knowledge/*.md）
# ══════════════════════════════════════════════════════════════

def _search_md_knowledge(query, knowledge_dir=None):
    """在 knowledge/*.md 中搜索关键词（第一优先级）。

    Returns:
        list[dict]: [{source, title, content}]
    """
    kdir = knowledge_dir or _KNOWLEDGE_DIR
    results = []

    md_files = glob.glob(os.path.join(kdir, '*.md'))
    for md_path in sorted(md_files):
        try:
            with open(md_path, encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        if query.lower() in content.lower():
            # 找到包含关键词的段落
            for para in content.split('\n\n'):
                if query.lower() in para.lower() and len(para.strip()) > 20:
                    results.append({
                        'source': md_path,
                        'title': os.path.basename(md_path),
                        'content': para.strip()[:500],
                        'layer': 'L1_md',
                    })

    return results


# ══════════════════════════════════════════════════════════════
# 两级搜索
# ══════════════════════════════════════════════════════════════

def hybrid_search(query, top_k=5, knowledge_dir=None):
    """两级混合搜索。

    1. knowledge/*.md 关键词匹配（L1 优先知识）
    2. gamedocs 缓存文件匹配（L2 原文）

    Returns:
        list[dict]: [{source, title, content, layer}]
    """
    all_results = []

    # L1: MD 优先知识
    md_results = _search_md_knowledge(query, knowledge_dir)
    if md_results:
        all_results.extend(md_results[:top_k])

    # 如果 L1 已经足够
    if len(all_results) >= top_k:
        return all_results[:top_k]

    # L2: gamedocs 缓存检索（关键词定位 + IDE AI 判断）
    remaining = top_k - len(all_results)
    matched = search_manifest(query)
    for m in matched[:remaining]:
        content = read_cached_file(m['filename'])
        if not content:
            continue
        # 大文件截断
        if len(content) > 3000:
            content = content[:3000]
        all_results.append({
            'source': m['cache_path'],
            'title': m['filename'],
            'content': content,
            'layer': 'L2_cache',
        })

    return all_results[:top_k]


# ══════════════════════════════════════════════════════════════
# CLI 命令
# ══════════════════════════════════════════════════════════════

def cmd_ingest(args):
    """摄入命令。"""
    if args.path:
        path = os.path.abspath(args.path)
        if os.path.isfile(path):
            print(f"[+] 增量摄入: {path}")
            stats = build_index(dirs=[path], force=args.force)
        elif os.path.isdir(path):
            print(f"[+] 摄入目录: {path}")
            stats = build_index(dirs=[path], force=args.force)
        else:
            print(f"[x] 路径不存在: {path}")
            return
    else:
        print(f"[+] 全量摄入: {_KNOWLEDGE_DIR}")
        stats = build_index(force=args.force)

    print(f"\n[OK] 完成: {stats['indexed']}/{stats['total_files']} 文件已解析, "
          f"跳过 {stats['skipped']}")


def cmd_search(args):
    """搜索命令。"""
    query = ' '.join(args.query)
    results = hybrid_search(query, top_k=args.top_k)

    if not results:
        print(f"[?] \"{query}\" → 无结果")
        return

    print(f"[?] \"{query}\" → {len(results)} 条结果\n")
    for i, r in enumerate(results, 1):
        src = os.path.basename(r['source'])
        layer = r.get('layer', '?')
        title = r.get('title', '')
        print(f"  {i}. [{layer}]  {src} → {title}")
        content = r['content'][:200].replace('\n', ' ')
        print(f"     {content}...")
        print()


def cmd_stats(args):
    """统计命令。"""
    s = get_stats()
    print(f"[i] 知识库统计")
    print(f"   缓存文件数: {s['total_files']}")
    print(f"   总大小: {s['total_size_kb']}KB")
    print()
    for f in s['files']:
        print(f"   {f['source']} ({f['size_kb']}KB, {f['sections']} sections)")


def main():
    parser = argparse.ArgumentParser(description='知识库混合检索 CLI')
    sub = parser.add_subparsers(dest='command')

    # ingest
    p_ingest = sub.add_parser('ingest', help='摄入文件到索引')
    p_ingest.add_argument('--path', help='指定文件或目录（默认全量）')
    p_ingest.add_argument('--force', action='store_true', help='强制重建')

    # search
    p_search = sub.add_parser('search', help='搜索知识库')
    p_search.add_argument('query', nargs='+', help='搜索关键词')
    p_search.add_argument('--top-k', type=int, default=5, help='返回结果数')

    # stats
    sub.add_parser('stats', help='查看索引统计')

    args = parser.parse_args()

    if args.command == 'ingest':
        cmd_ingest(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'stats':
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
