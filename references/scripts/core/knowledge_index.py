# -*- coding: utf-8 -*-
"""
知识摄入模块 -- 扫描文档目录，解析并缓存为 markdown。

职责：
1. 扫描 knowledge/gamedocs/ 目录
2. 调用 doc_reader 解析 docx/xlsx -> markdown
3. 缓存到 .cache/ 目录（doc_reader 内部完成）

不再维护 FTS5 索引，检索由 IDE AI 直接读取 .cache/ 完成。

Usage:
    from knowledge_index import build_index
    stats = build_index()           # 解析并缓存
    stats = build_index(force=True) # 强制重新解析
"""

import os
import sys

# 路径设置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from doc_reader import read_doc, scan_dir


# -- 默认路径 --
_BASE_DIR = os.environ.get('WORKSPACE_DIR') or os.path.normpath(
    os.path.join(SCRIPT_DIR, '..', '..', '..')
)
_KNOWLEDGE_DIR = os.path.join(_BASE_DIR, 'knowledge')
_GAMEDOCS_DIR = os.path.join(_KNOWLEDGE_DIR, 'gamedocs')


# ==============================================================
# 摄入（解析 + 缓存）
# ==============================================================

def build_index(dirs=None, force=False, **kwargs):
    """扫描目录，解析文件，缓存为 markdown。

    Args:
        dirs: 要扫描的目录列表，默认 [knowledge/gamedocs/]
        force: 是否强制重新解析（忽略缓存）

    Returns:
        dict: {total_files, indexed, skipped}
    """
    if dirs is None:
        dirs = [_GAMEDOCS_DIR]

    # 收集所有文件（去重）
    all_files = set()

    # 始终扫描 knowledge/*.md 根级文件
    import glob as _glob
    for md in _glob.glob(os.path.join(_KNOWLEDGE_DIR, '*.md')):
        all_files.add(os.path.abspath(md))

    for d in dirs:
        if os.path.isdir(d):
            for f in scan_dir(d):
                all_files.add(os.path.abspath(f))
        elif os.path.isfile(d):
            all_files.add(os.path.abspath(d))

    stats = {'total_files': len(all_files), 'indexed': 0, 'skipped': 0}

    for filepath in sorted(all_files):
        basename = os.path.basename(filepath)
        print(f"  [+] {basename}", end=' ')

        try:
            chunks = read_doc(filepath, force=force)
        except Exception as e:
            print(f"[ERR] {e}")
            continue

        if not chunks:
            print("(empty)")
            stats['skipped'] += 1
            continue

        print(f"[OK] {len(chunks)} chunks")
        stats['indexed'] += 1

    # Wiki 编译层
    try:
        from wiki_compiler import compile_wiki
        cache_dir = os.path.join(_GAMEDOCS_DIR, '.cache')
        if os.path.isdir(cache_dir):
            print("\n[+] Compiling wiki...")
            wiki_stats = compile_wiki(cache_dir, _KNOWLEDGE_DIR, force=force)
            stats['wiki'] = wiki_stats
    except Exception as e:
        print(f"[WARN] Wiki compilation failed: {e}")

    return stats


def get_stats():
    """获取知识库统计（基于缓存文件）。"""
    from knowledge_search import build_manifest
    manifest = build_manifest()
    total_files = len(manifest)
    total_size = sum(m['size'] for m in manifest)
    return {
        'total_files': total_files,
        'total_size_kb': total_size // 1024,
        'files': [
            {
                'source': m['filename'],
                'size_kb': m['size'] // 1024,
                'sections': len(m['titles']),
            }
            for m in manifest
        ],
    }


# -- CLI --
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python knowledge_index.py build         # parse and cache")
        print("  python knowledge_index.py build --force  # force re-parse")
        print("  python knowledge_index.py stats          # show stats")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'build':
        force = '--force' in sys.argv
        print("[+] Ingesting documents...")
        s = build_index(force=force)
        print(f"\n[OK] {s['indexed']}/{s['total_files']} files, "
              f"skipped {s['skipped']}")

    elif cmd == 'stats':
        s = get_stats()
        print(f"[i] {s['total_files']} cached files, {s['total_size_kb']}KB total")
        for f in s['files']:
            print(f"  {f['source']} ({f['size_kb']}KB, {f['sections']} sections)")

    else:
        print("Unknown command. Use: build / stats")
