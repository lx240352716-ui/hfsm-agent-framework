# -*- coding: utf-8 -*-
"""
文档解析器 — 统一读取 docx / xlsx / md 等文件并切片。

基于 MarkItDown（微软）将任意文件转为 Markdown 文本，
然后按句号/换行处断开为固定大小 chunks。

支持格式（MarkItDown 原生支持）：
- .md / .docx / .xlsx / .xls / .pptx / .pdf / .html / .csv

Usage:
    from doc_reader import read_doc, chunk_text
    chunks = read_doc('knowledge/gamedocs/荣耀连战.docx')
"""

import os
import re

# MarkItDown 懒导入：仅在缓存未命中时才加载（避免 openpyxl/mammoth/magika 启动开销）
_md = None


def _get_md():
    """懒加载 MarkItDown 单例。首次调用才 import + 实例化。"""
    global _md
    if _md is None:
        from markitdown import MarkItDown
        _md = MarkItDown()
    return _md


# ══════════════════════════════════════════════════════════════
# docx 修复: WPS Office 会写入无效的关系引用 (../NULL)
# ══════════════════════════════════════════════════════════════

# 已知的无效 Target 模式 (WPS Office、PDF转换器等)
_BAD_TARGETS = frozenset(('../NULL', 'NULL', 'word/NULL', '#pdfImages', '#_top'))

# 1x1 透明 PNG 占位符
import base64 as _b64
_PLACEHOLDER_PNG = _b64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB'
    'Nl7BcQAAAABJRU5ErkJggg=='
)


def _fix_docx_rels(filepath):
    """检查 docx 内部 rels 是否有无效引用，有则原地修复。

    Returns:
        bool: True 表示已修复，False 表示无需修复或修复失败。
    """
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            # 快速扫描: 是否有需要修复的 rels
            needs_fix = False
            for name in z.namelist():
                if name.endswith('.rels'):
                    data = z.read(name).decode('utf-8')
                    root = ET.fromstring(data)
                    for rel in root:
                        if rel.get('Target', '') in _BAD_TARGETS:
                            needs_fix = True
                            break
                if needs_fix:
                    break

            if not needs_fix:
                return False

            # 重写 ZIP: 替换坏引用 + 注入占位图片
            import tempfile
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.docx')
            os.close(tmp_fd)
            fixed_count = 0
            with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                has_placeholder = False
                for item in z.infolist():
                    data = z.read(item.filename)
                    if item.filename.endswith('.rels'):
                        root = ET.fromstring(data)
                        for rel in root:
                            target = rel.get('Target', '')
                            if target in _BAD_TARGETS:
                                rel.set('Target', 'media/_placeholder.png')
                                fixed_count += 1
                        if fixed_count:
                            data = ET.tostring(root, xml_declaration=True,
                                               encoding='UTF-8')
                    zout.writestr(item, data)
                if fixed_count and not has_placeholder:
                    zout.writestr('word/media/_placeholder.png', _PLACEHOLDER_PNG)

        # 原地替换源文件
        import shutil
        shutil.move(tmp_path, filepath)
        print(f"[OK] fixed {fixed_count} bad rels: {os.path.basename(filepath)}")
        return True

    except Exception as ex:
        print(f"[WARN] fix_docx_rels failed: {ex}")
        return False


# ══════════════════════════════════════════════════════════════
# 文件解析：MarkItDown 统一转换 + 解析缓存
# ══════════════════════════════════════════════════════════════

# 需要缓存的慢格式（MarkItDown 解析耗时较长的格式）
_CACHED_EXTS = frozenset(('.docx', '.xlsx', '.xls', '.pptx'))


def _get_cache_path(filepath):
    """返回缓存文件路径: 同目录下 .cache/文件名.md"""
    dirpath = os.path.dirname(filepath)
    cache_dir = os.path.join(dirpath, '.cache')
    return os.path.join(cache_dir, os.path.basename(filepath) + '.md')


def _read_cache(filepath, force=False):
    """读取解析缓存。缓存新于源文件时返回文本，否则返回 None。"""
    if force:
        return None
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in _CACHED_EXTS:
        return None
    cache_path = _get_cache_path(filepath)
    if not os.path.exists(cache_path):
        return None
    if os.path.getmtime(cache_path) >= os.path.getmtime(filepath):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def _write_cache(filepath, text):
    """将解析结果写入缓存。"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in _CACHED_EXTS or not text:
        return
    cache_path = _get_cache_path(filepath)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(text)


# 中文字符检测（用于 xlsx 噪音过滤）
_RE_CHINESE = re.compile(r'[\u4e00-\u9fff]')


def _filter_xlsx_noise(text):
    """过滤 xlsx 转 markdown 后的噪音行。

    保留: sheet 标题(##)、表头分隔线(|---|)、含中文的数据行
    删除: 纯 NaN 行、纯数字/ID 行、空行
    """
    lines = text.split('\n')
    filtered = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # sheet 标题
        if stripped.startswith('## '):
            filtered.append(line)
            continue
        # 表头分隔线
        if stripped.startswith('| ---'):
            filtered.append(line)
            continue
        # 含中文 -> 保留整行（包括关联数字）
        if _RE_CHINESE.search(stripped):
            filtered.append(line)
            continue
        # 其余（纯 NaN / 纯数字行）-> 丢弃
    return '\n'.join(filtered)


def _parse_file(filepath, force=False):
    """用 MarkItDown 将任意文件转为 markdown 文本。

    对 docx/xlsx 等慢格式，使用 .cache/ 目录缓存解析结果，
    源文件未变时直接读缓存，避免重复解析。
    对 xlsx 文件额外过滤噪音行（纯 NaN / 纯数字），提升搜索质量。

    Args:
        filepath: 文件路径
        force: 是否强制重新解析（忽略缓存）

    Returns:
        list[tuple[str, str]]: [(title, text)] 列表
    """
    # 尝试读取缓存
    cached = _read_cache(filepath, force=force)
    if cached is not None:
        text = cached
    else:
        md = _get_md()
        text = None
        try:
            result = md.convert(filepath)
            text = result.text_content or ''
            text = re.sub(r'!\[.*?\]\(data:image/[^)]+\)', '[图片]', text)
        except Exception as e:
            # docx 懒修复: WPS Office 等工具会写入无效的 ../NULL 图片引用，
            # mammoth 解析时报 KeyError。检测到后原地修复源文件，下次直接解析。
            if filepath.lower().endswith('.docx') and _fix_docx_rels(filepath):
                try:
                    result = md.convert(filepath)
                    text = result.text_content or ''
                    text = re.sub(r'!\[.*?\]\(data:image/[^)]+\)', '[图片]', text)
                except Exception as e2:
                    print(f"[WARN] retry failed {os.path.basename(filepath)}: {e2}")
                    return []
            else:
                print(f"[WARN] cannot parse {os.path.basename(filepath)}: {type(e).__name__}: {e}")
                return []
        # xlsx 噪音过滤：删除纯 NaN / 纯数字行
        if filepath.lower().endswith(('.xlsx', '.xls')):
            text = _filter_xlsx_noise(text)
        # 解析成功，写入缓存（xlsx 存的是过滤后的文本）
        _write_cache(filepath, text)

    if not text.strip():
        return []

    # 按 ##/# 标题拆分为多段（与旧 _read_md 行为一致）
    sections = []
    parts = re.split(r'^(#{1,3}\s+.+)$', text, flags=re.MULTILINE)

    current_title = os.path.basename(filepath)
    current_text = []

    for part in parts:
        if re.match(r'^#{1,3}\s+', part):
            combined = '\n'.join(current_text).strip()
            if combined and len(combined) > 20:
                sections.append((current_title, combined))
            current_title = part.strip().lstrip('#').strip()
            current_text = []
        else:
            current_text.append(part)

    # 最后一段
    combined = '\n'.join(current_text).strip()
    if combined and len(combined) > 20:
        sections.append((current_title, combined))

    # 如果没有标题拆分，整个文本作为一段
    if not sections and text.strip():
        sections.append((os.path.basename(filepath), text.strip()))

    return sections


# ══════════════════════════════════════════════════════════════
# 切片：长文本 → 固定大小 chunks
# ══════════════════════════════════════════════════════════════

def chunk_text(text, max_chars=700, overlap=100):
    """将文本切成固定大小的 chunks。

    Args:
        text: 输入文本
        max_chars: 每个 chunk 最大字符数
        overlap: 相邻 chunk 重叠字符数

    Returns:
        list[str]: chunk 列表
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars

        # 尝试在句号/换行处断开
        if end < len(text):
            # 先找换行
            break_pos = text.rfind('\n', start + max_chars // 2, end)
            if break_pos == -1:
                # 再找句号
                for sep in ['。', '；', '.\n', '. ', '，']:
                    break_pos = text.rfind(sep, start + max_chars // 2, end)
                    if break_pos != -1:
                        break_pos += len(sep)
                        break
            else:
                break_pos += 1

            if break_pos > start:
                end = break_pos

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


# ══════════════════════════════════════════════════════════════
# 统一入口
# ══════════════════════════════════════════════════════════════

def read_doc(filepath, max_chunk_chars=700, overlap=100, force=False):
    """读取文件并切片，返回标准化 chunk 列表。

    Args:
        filepath: 文件路径
        max_chunk_chars: 每个 chunk 最大字符数
        overlap: 重叠字符数
        force: 是否强制重新解析（忽略缓存）

    Returns:
        list[dict]: [{
            'source': 文件路径,
            'title': 段落标题/sheet名,
            'chunk_id': 序号,
            'text': 文本内容,
        }]
    """
    filepath = os.path.abspath(filepath)

    # MarkItDown 统一处理所有格式
    sections = _parse_file(filepath, force=force)

    # 切片
    all_chunks = []
    chunk_id = 0
    for title, text in sections:
        for chunk in chunk_text(text, max_chunk_chars, overlap):
            all_chunks.append({
                'source': filepath,
                'title': title,
                'chunk_id': chunk_id,
                'text': chunk,
            })
            chunk_id += 1

    return all_chunks


def scan_dir(directory, extensions=None):
    """扫描目录下的所有文件，返回文件路径列表。

    Args:
        directory: 目录路径
        extensions: 允许的扩展名列表，如 ['.md', '.docx', '.xlsx']

    Returns:
        list[str]: 文件路径列表
    """
    if extensions is None:
        extensions = ['.md', '.docx', '.xlsx', '.xls']

    files = []
    for root, dirs, filenames in os.walk(directory):
        # 跳过缓存目录
        dirs[:] = [d for d in dirs if d != '.cache']
        for f in sorted(filenames):
            ext = os.path.splitext(f)[1].lower()
            if ext in extensions:
                files.append(os.path.join(root, f))
    return files


# ── 命令行快速测试 ──
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python doc_reader.py <文件路径>")
        sys.exit(1)

    path = sys.argv[1]
    chunks = read_doc(path)
    print(f"文件: {path}")
    print(f"共 {len(chunks)} 个 chunks\n")
    for c in chunks[:5]:
        print(f"--- [{c['title']}] chunk#{c['chunk_id']} ({len(c['text'])} 字) ---")
        print(c['text'][:200] + ('...' if len(c['text']) > 200 else ''))
        print()
