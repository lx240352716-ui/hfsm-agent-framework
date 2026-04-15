# -*- coding: utf-8 -*-
"""Excel/SQLite 统一读取层"""

import os
import re
import sqlite3
from constants import EXCEL_DIR, DB_PATH

# 模块级缓存
_db_conn = None  # 连接缓存
_table_registry = None  # 注册表缓存
_com_excel = None  # COM Excel 单例


# ── COM Excel 统一入口 ──

def get_com_excel():
    """获取 COM Excel Application 单例（隐藏窗口）。

    所有需要 COM 操作 xlsx 的地方统一调此方法，避免重复创建实例。
    """
    global _com_excel
    if _com_excel is not None:
        try:
            _ = _com_excel.Visible  # 检查实例是否还活着
            return _com_excel
        except Exception:
            _com_excel = None
    import win32com.client
    _com_excel = win32com.client.Dispatch("Excel.Application")
    _com_excel.Visible = False
    _com_excel.DisplayAlerts = False
    return _com_excel


def close_com_excel():
    """关闭 COM Excel 单例。在整轮操作结束后调用。"""
    global _com_excel
    if _com_excel is not None:
        try:
            _com_excel.Quit()
        except Exception:
            pass
        _com_excel = None


def open_workbook(table_name, read_only=False):
    """用 COM Excel 打开源表，返回 (workbook, worksheet)。

    Args:
        table_name: 表名（如 'Item', '_ShopItem'）
        read_only: 是否只读打开
    Returns:
        (wb, ws) 元组
    """
    excel = get_com_excel()
    src_path, _ = _get_table_path(table_name)
    src_path = os.path.abspath(src_path)
    wb = excel.Workbooks.Open(src_path, ReadOnly=read_only)
    ws = wb.ActiveSheet
    return wb, ws



def _clean_identifier(name):
    return re.sub(r'[\]\[]', '', str(name))

def _get_conn(db_path=None):
    """获取SQLite连接（缓存复用），带损坏自愈"""
    global _db_conn
    path = db_path or DB_PATH

    def _create_and_verify():
        c = sqlite3.connect(path, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            c.execute("PRAGMA schema_version;")
            return c
        except sqlite3.DatabaseError:
            c.close()
            if os.path.exists(path):
                os.remove(path)
            print("  [WARN] SQLite 索引库已损坏，自动删除重建...")
            c2 = sqlite3.connect(path, timeout=10)
            c2.row_factory = sqlite3.Row
            return c2

    if db_path is None and _db_conn is not None:
        try:
            _db_conn.execute("PRAGMA schema_version;")
            return _db_conn
        except sqlite3.DatabaseError:
            _db_conn.close()
            _db_conn = None

    conn = _create_and_verify()
    if db_path is None:
        _db_conn = conn
    return conn


def query_db(sql, params=None, db_path=None):
    """SQLite秒查 — 对已索引的大表执行SQL查询

    Args:
        sql: SQL语句，表名用[]包裹，如 SELECT * FROM [_Buff] WHERE [perfactor]=?
        params: SQL参数元组（防注入）
        db_path: 数据库路径（默认 scripts/table_index.db，传入则不缓存）
    Returns:
        list[dict]: 查询结果

    用法：
        results = query_db("SELECT * FROM [_Buff] WHERE [perfactor] = ?", ('speed',))
        max_id = query_db("SELECT MAX(CAST([Unnamed:_0] AS INT)) as m FROM [_Buff]")[0]['m']
    """
    # 自动解析 FROM [表名]，模糊匹配后替换为完整表名
    m = re.search(r'FROM\s+\[([^\]]+)\]', sql, re.IGNORECASE)
    if m:
        raw_name = m.group(1)
        resolved = _ensure_indexed(raw_name)
        if resolved != raw_name:
            sql = sql.replace(f'[{raw_name}]', f'[{_clean_identifier(resolved)}]')

    conn = _get_conn(db_path)
    if params:
        rows = conn.execute(sql, params).fetchall()
    else:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def refresh_index(xlsx_path, table_name, header_row=1):
    """自动为单张大表建立 SQLite 索引（首次几秒，后续毫秒级）"""
    import pandas as pd
    import time

    global _db_conn

    print(f"  [AUTO-INDEX] {table_name} 未索引，自动建立...", end="", flush=True)
    t0 = time.time()

    try:
        df = pd.read_excel(xlsx_path, header=header_row, engine='calamine')
    except Exception:
        df = pd.read_excel(xlsx_path, header=header_row, engine='openpyxl')

    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql(_clean_identifier(table_name), conn, if_exists='replace', index=False)
    finally:
        conn.close()

    # 清除连接缓存（索引已更新）
    _db_conn = None

    elapsed = time.time() - t0
    print(f" {len(df)} rows, {elapsed:.1f}s")



def _get_table_path(table_name):
    """解析表名，返回 (xlsx_path, resolved_name)。

    支持 basename 模糊匹配：BeastPiratesBoss -> BeastPirates/BeastPiratesBoss

    Returns:
        (str, str): (xlsx 文件绝对路径, 解析后的完整表名) 或 (None, table_name)
    """
    global _table_registry
    if _table_registry is None:
        import json as _json
        reg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'configs', 'table_registry.json'
        )
        with open(reg_path, 'r', encoding='utf-8') as f:
            _table_registry = _json.load(f)
    resolved_name = table_name
    entry = _table_registry.get(table_name)
    # basename 模糊匹配：BeastPiratesBoss -> BeastPirates/BeastPiratesBoss
    if not entry:
        suffix = '/' + table_name
        candidates = [k for k in _table_registry if k.endswith(suffix)]
        if len(candidates) == 1:
            resolved_name = candidates[0]
            entry = _table_registry[resolved_name]
    if not entry:
        return None, table_name
    rel_path = entry if isinstance(entry, str) else entry.get('path', '')
    return os.path.join(EXCEL_DIR, rel_path), resolved_name

# ── 行结构自动检测（类似 CC detectLanguage 模式） ──

# 兜底正则：用于首次采样前的 bootstrap 分类
_FALLBACK_TYPE_RE = re.compile(
    r'^('
    r'int|string|float|bool|long|double|short|byte|text|json|date|time|varchar|'
    r'fix16|fix32|DWORD|enum|'
    r'array_\w+|string\(intern\)|'
    r'none|primary|index|unique'
    r')\b',
    re.IGNORECASE
)

# 动态词表缓存（运行时加载一次）
_project_vocabulary = None
_VOCAB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'configs', 'table_vocabulary.json'
)

_schema_cache = {}
_columns_cache = {}


def _has_cjk(s):
    """是否包含 CJK 字符"""
    return any('\u4e00' <= c <= '\u9fff' for c in str(s))


def _is_identifier(s):
    """是否是英文标识符（camelCase, snake_case, PascalCase）"""
    s = str(s).strip()
    if not s:
        return False
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', s))


def _is_en(s):
    """是否包含 ASCII 英文字母"""
    return s and any(c.isalpha() and ord(c) < 128 for c in str(s))


def detect_project_vocabulary(force=False):
    """采样项目的 Excel 表，自动学习元数据关键词（懒加载 + 文件缓存）。

    调用时机：_classify_row() 首次被调用时自动触发。
    缓存位置：configs/table_vocabulary.json

    流程：
      1. 随机采样 ≤30 张小表（<0.5MB）
      2. 统计 Row3-Row5（offset 0-2）的高频值
      3. 排除也出现在 Row7+（offset 4+）的值 → 剩下的 = 元数据关键词
      4. 缓存到 JSON，后续直接读取

    Returns:
        set[str]: 元数据关键词集合（小写）
    """
    global _project_vocabulary
    import json as _json

    # 内存缓存命中
    if _project_vocabulary is not None and not force:
        return _project_vocabulary

    # 文件缓存命中
    if os.path.exists(_VOCAB_PATH) and not force:
        with open(_VOCAB_PATH, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        _project_vocabulary = set(data.get('meta_keywords', []))
        return _project_vocabulary

    # ── 首次采样 ──
    import random, collections

    # 找所有小表
    small_tables = []
    for f in os.listdir(EXCEL_DIR):
        if f.endswith('.xlsx') and not f.startswith('~'):
            path = os.path.join(EXCEL_DIR, f)
            size = os.path.getsize(path) / (1024 * 1024)
            if size < 0.5:
                small_tables.append((os.path.splitext(f)[0], path))

    if not small_tables:
        _project_vocabulary = set()
        return _project_vocabulary

    # 采样 ≤30 张
    sample = random.sample(small_tables, min(30, len(small_tables)))

    meta_counter = collections.Counter()   # offset 0-2 的值
    data_counter = collections.Counter()   # offset 4+ 的值

    for name, path in sample:
        try:
            refresh_index(path, name)
            conn = _get_conn()
            clean = _clean_identifier(name)
            rows = conn.execute(
                f"SELECT * FROM [{clean}] LIMIT 8 OFFSET 0").fetchall()

            for i, row in enumerate(rows):
                for cell in row:
                    val = str(cell).strip().lower() if cell is not None else ''
                    if not val or len(val) > 30:
                        continue
                    if i < 3:          # 元数据行 (Row3-Row5)
                        meta_counter[val] += 1
                    elif i >= 4:       # 数据行 (Row7+)
                        data_counter[val] += 1
        except Exception:
            continue

    # 元数据关键词 = 在元数据行出现 ≥3 次，且不在数据行频繁出现的纯英文词
    meta_keywords = set()
    for val, count in meta_counter.items():
        if count < 3:
            continue
        if data_counter.get(val, 0) > count * 2:
            continue  # 数据行更多 → 是数据值不是关键词
        if _is_identifier(val) or _FALLBACK_TYPE_RE.match(val):
            meta_keywords.add(val)

    # 保存
    os.makedirs(os.path.dirname(_VOCAB_PATH), exist_ok=True)
    vocab_data = {
        'meta_keywords': sorted(meta_keywords),
        'sample_count': len(sample),
        'total_tables': len(small_tables),
    }
    with open(_VOCAB_PATH, 'w', encoding='utf-8') as f:
        _json.dump(vocab_data, f, ensure_ascii=False, indent=2)

    print(f"  [VOCAB] 采样 {len(sample)} 张表，学习到 {len(meta_keywords)} 个元数据关键词")

    _project_vocabulary = meta_keywords
    return _project_vocabulary


def _classify_row(cells):
    """判断一行数据的类型：cn / en / type / data / empty

    使用动态词表（首次调用时自动学习）+ 兜底正则。
    """
    non_empty = [c for c in cells if c and str(c).strip()]
    if not non_empty:
        return 'empty'

    total = len(non_empty)

    # 中文检测：>60% 的非空 cell 含有 CJK
    cn_count = sum(1 for c in non_empty if _has_cjk(c))
    if cn_count / total > 0.6:
        return 'cn'

    # 加载动态词表
    vocab = detect_project_vocabulary()

    # 类型/索引关键词检测：>40% 的非空 cell 命中词表或兜底正则
    def _is_meta(c):
        val = str(c).strip().lower()
        return val in vocab or bool(_FALLBACK_TYPE_RE.match(val))

    type_count = sum(1 for c in non_empty if _is_meta(c))
    if type_count / total > 0.4:
        return 'type'

    # 英文标识符检测：>50% 的非空 cell 是标识符格式
    en_count = sum(1 for c in non_empty if _is_identifier(c))
    if en_count / total > 0.5:
        return 'en'

    # 其他 → 数据行
    return 'data'


def detect_row_schema(table_name):
    """自动检测表的行结构（懒加载 + 缓存）。

    扫描 SQLite 表头 + 前 8 行数据，按内容特征自动判断
    哪行是中文名、英文名、类型行。

    Returns:
        dict:
            cn_row:     'header' 或 行偏移 int（None = 未检测到）
            en_rows:    [行偏移, ...] 优先级从低到高（后面的优先）
            type_row:   行偏移 int（None = 未检测到）
            data_start: 行偏移 int（首个数据行）
    """
    if table_name in _schema_cache:
        return _schema_cache[table_name]

    resolved_name = _ensure_indexed(table_name)
    conn = _get_conn()
    clean = _clean_identifier(resolved_name)

    # 取前 8 行数据
    rows = conn.execute(
        f"SELECT * FROM [{clean}] LIMIT 8 OFFSET 0").fetchall()

    # SQLite 表头
    header_cols = [c[1] for c in conn.execute(
        f'PRAGMA table_info([{clean}])').fetchall()]

    schema = {
        'cn_row': None,
        'en_rows': [],
        'type_row': None,
        'data_start': None,
    }

    # 检测 header 行
    if _classify_row(header_cols) == 'cn':
        schema['cn_row'] = 'header'

    # 检测前 8 行
    for i, row in enumerate(rows):
        cells = [str(c).strip() if c is not None else '' for c in row]
        kind = _classify_row(cells)

        if kind == 'cn' and schema['cn_row'] is None:
            schema['cn_row'] = i
        elif kind == 'en':
            schema['en_rows'].append(i)
        elif kind == 'type' and schema['type_row'] is None:
            schema['type_row'] = i
        elif kind == 'data' and schema['data_start'] is None:
            schema['data_start'] = i

    # 兜底
    if schema['data_start'] is None:
        meta_rows = len(schema['en_rows']) + (1 if schema['type_row'] is not None else 0)
        schema['data_start'] = meta_rows + 1

    _schema_cache[table_name] = schema
    return schema


# ── 字段信息获取（唯一入口） ──

def get_columns(table_name):
    """获取表的完整字段信息（【唯一入口】，禁止其他地方自己读行数据）。

    一次查询返回所有字段元数据，调用方按需取用。
    走 SQLite 缓存 + 自动行结构检测，毫秒级，结果内存缓存。

    Args:
        table_name: 表名（如 'Item', '_Buff', 'BuffActive'）
    Returns:
        dict:
            cn:      list[str]  — 中文列名（过滤 EmptyKey/_pending）
            en:      list[str]  — 英文列名（自动检测的 en_rows，后面优先）
            types:   list[str]  — 数据类型（如 'int', 'string'），无则空列表
            cn_en:   dict       — {中文: 英文} 对照
            en_cn:   dict       — {英文: 中文} 反向对照
            en_type: dict       — {英文: 数据类型}
            col_map: dict       — {英文: Excel列号(1-indexed)}
    """
    if table_name in _columns_cache:
        return _columns_cache[table_name]

    resolved_name = _ensure_indexed(table_name)
    conn = _get_conn()
    clean = _clean_identifier(resolved_name)
    schema = detect_row_schema(resolved_name)

    # 中文列名来源
    all_cn = [c[1] for c in conn.execute(
        f'PRAGMA table_info([{clean}])').fetchall()]
    total_cols = len(all_cn)

    # 读前 8 行（覆盖所有可能的元数据行）
    rows = conn.execute(
        f"SELECT * FROM [{clean}] LIMIT 8 OFFSET 0").fetchall()

    # 按 schema 动态取英文行和类型行
    en_rows_data = []
    for idx in schema['en_rows']:
        if idx < len(rows):
            en_rows_data.append(rows[idx])

    type_row_data = None
    if schema['type_row'] is not None and schema['type_row'] < len(rows):
        type_row_data = rows[schema['type_row']]

    # 构建字段映射
    cn_filtered = []
    en_list = []
    type_list = []
    cn_en = {}
    en_cn = {}
    en_type = {}
    col_map = {}

    for i in range(total_cols):
        cn = all_cn[i]
        if cn == '_pending' or cn.startswith('EmptyKey-'):
            continue

        cn_filtered.append(cn)

        # 英文名：后面的 en_row 优先（如 Row6 > Row3）
        en = None
        for en_row in reversed(en_rows_data):
            val = str(en_row[i]).strip() if i < len(en_row) and en_row[i] is not None else None
            if _is_en(val):
                en = val
                break

        if en:
            en_list.append(en)
            cn_en[cn] = en
            en_cn[en] = cn
            col_map[en] = i + 1

            # 类型
            if type_row_data is not None:
                t = str(type_row_data[i]).strip() if i < len(type_row_data) and type_row_data[i] is not None else ''
                if t and _is_en(t):
                    type_list.append(t)
                    en_type[en] = t

    result = {
        'cn': cn_filtered,
        'en': en_list,
        'types': type_list,
        'cn_en': cn_en,
        'en_cn': en_cn,
        'en_type': en_type,
        'col_map': col_map,
    }
    _columns_cache[table_name] = result
    return result


def _ensure_indexed(table_name):
    """确保表已被索引到 SQLite，过期则自动重建。

    Returns:
        str: 解析后的完整表名（模糊匹配时可能与输入不同）
    """
    conn = _get_conn()
    full_path, resolved_name = _get_table_path(table_name)
    if not full_path:
        raise ValueError(f"表 '{table_name}' 不在 table_registry.json 中")

    need_reindex = False
    try:
        cols = [c[1] for c in conn.execute(
            f'PRAGMA table_info([{_clean_identifier(resolved_name)}])').fetchall()]
        if not cols:
            need_reindex = True
        else:
            if os.path.exists(full_path) and os.path.exists(DB_PATH):
                if os.path.getmtime(full_path) > os.path.getmtime(DB_PATH):
                    print(f"  [WARN] 检测到 '{resolved_name}' 源表已被外部修改，自动重建索引...")
                    need_reindex = True
    except Exception:
        need_reindex = True

    if need_reindex:
        refresh_index(full_path, resolved_name)

    return resolved_name


def max_id(table_name, id_field, min_val=None, max_val=None):
    """查询表中指定 ID 字段的最大值。

    Args:
        table_name: 表名
        id_field: ID 字段名
        min_val: ID 范围下限（可选）
        max_val: ID 范围上限（可选）
    Returns:
        int or None: 最大 ID
    """
    resolved_name = _ensure_indexed(table_name)
    conn = _get_conn()
    tbl = _clean_identifier(resolved_name)
    fld = _clean_identifier(id_field)
    try:
        if min_val is not None and max_val is not None:
            row = conn.execute(
                f"SELECT MAX(CAST([{fld}] AS INTEGER)) as m FROM [{tbl}] "
                f"WHERE CAST([{fld}] AS INTEGER) BETWEEN ? AND ?",
                (min_val, max_val)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT MAX(CAST([{fld}] AS INTEGER)) as m FROM [{tbl}]"
            ).fetchone()
        return row['m'] if row and row['m'] is not None else None
    except sqlite3.OperationalError:
        return None

