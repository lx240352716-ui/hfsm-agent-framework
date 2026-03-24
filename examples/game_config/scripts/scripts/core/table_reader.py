# -*- coding: utf-8 -*-
"""Excel/SQLite 统一读取层"""

import os
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
    src_path = os.path.abspath(_get_table_path(table_name))
    wb = excel.Workbooks.Open(src_path, ReadOnly=read_only)
    ws = wb.ActiveSheet
    return wb, ws



def _clean_identifier(name):
    import re
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


def read_table(xlsx_path, header_row=1):
    """统一读取Excel表

    ★ 调用者无需关心文件大小或索引状态，本函数自动处理：
      - 已索引 → SQLite 毫秒级查询
      - 未索引 + >1MB → 自动建索引 → SQLite 查询
      - 未索引 + ≤1MB → pandas 直读

    Args:
        xlsx_path: xlsx文件路径（可以是相对于EXCEL_DIR的路径）
        header_row: 表头行号（默认1，即第2行是字段名）
    Returns:
        DataFrame
    """
    import pandas as pd
    if not os.path.isabs(xlsx_path):
        xlsx_path = os.path.join(EXCEL_DIR, xlsx_path)

    basename = os.path.splitext(os.path.basename(xlsx_path))[0]
    file_size_mb = os.path.getsize(xlsx_path) / (1024 * 1024) if os.path.exists(xlsx_path) else 0

    # ★ 第一优先：尝试走 SQLite 快查（已索引的表）
    if os.path.exists(DB_PATH):
        xlsx_mtime = os.path.getmtime(xlsx_path) if os.path.exists(xlsx_path) else 0
        db_mtime = os.path.getmtime(DB_PATH)
        if xlsx_mtime > db_mtime:
            print(f"  [STALE] {basename} 源文件已更新，重建索引...")
            refresh_index(xlsx_path, basename, header_row)
        try:
            all_rows = query_db(f"SELECT * FROM [{basename}]")
            if all_rows:
                print(f"  [SQLITE] {basename}: {len(all_rows)} rows (毫秒级)")
                return pd.DataFrame(all_rows)
        except Exception:
            pass

    # ★ 第二优先：大表(>1MB)自动建索引，再走 SQLite
    if file_size_mb > 1:
        print(f"  [GUARD] {basename}.xlsx = {file_size_mb:.1f}MB > 1MB，禁止 pandas 硬读")
        refresh_index(xlsx_path, basename, header_row)
        all_rows = query_db(f"SELECT * FROM [{basename}]")
        if all_rows:
            print(f"  [SQLITE] {basename}: {len(all_rows)} rows (已自动索引)")
            return pd.DataFrame(all_rows)

    # ★ 第三优先：小表直接 pandas
    return pd.read_excel(xlsx_path, header=header_row)


def _get_table_path(table_name):
    global _table_registry
    if _table_registry is None:
        import json as _json
        reg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'configs', 'table_registry.json'
        )
        with open(reg_path, 'r', encoding='utf-8') as f:
            _table_registry = _json.load(f)
    entry = _table_registry.get(table_name)
    if not entry:
        return None
    rel_path = entry if isinstance(entry, str) else entry.get('path', '')
    return os.path.join(EXCEL_DIR, rel_path)

def get_columns(table_name):
    """获取表的完整字段信息（【唯一入口】，禁止其他地方自己读行数据）。

    一次查询返回所有字段元数据，调用方按需取用。
    走 SQLite 缓存，毫秒级，结果内存缓存。

    Args:
        table_name: 表名（如 'Item', '_Buff', 'BuffActive'）
    Returns:
        dict:
            cn:      list[str]  — Row2 中文列名（过滤 EmptyKey/_pending）
            en:      list[str]  — Row3+Row6 英文并集（Row6 优先，Row3 补充，无英文名的跳过）
            types:   list[str]  — Row4 数据类型（如 'int', 'string'），无则空列表
            cn_en:   dict       — {中文: 英文} 对照
            en_cn:   dict       — {英文: 中文} 反向对照
            en_type: dict       — {英文: 数据类型}
            col_map: dict       — {英文: Excel列号(1-indexed)}
    """
    if table_name in _columns_cache:
        return _columns_cache[table_name]

    _ensure_indexed(table_name)
    conn = _get_conn()
    clean = _clean_identifier(table_name)

    # Row2 中文列名（SQLite 表头）
    all_cn = [c[1] for c in conn.execute(
        f'PRAGMA table_info([{clean}])').fetchall()]
    total_cols = len(all_cn)

    # 读前4行数据（Row3~Row6）
    rows = conn.execute(
        f"SELECT * FROM [{clean}] LIMIT 4 OFFSET 0").fetchall()

    row3 = rows[0] if len(rows) > 0 else [None] * total_cols  # 客户端英文
    row4 = rows[1] if len(rows) > 1 else [None] * total_cols  # 数据类型
    # row5 = rows[2]  # 索引类型（暂不用）
    row6 = rows[3] if len(rows) > 3 else [None] * total_cols  # 服务器英文

    # 构建英文并集：Row6 优先，Row6 为空则用 Row3
    cn_filtered = []
    en_list = []
    type_list = []
    cn_en = {}
    en_cn = {}
    en_type = {}
    col_map = {}

    def _is_en(s):
        return s and any(c.isalpha() and ord(c) < 128 for c in s)

    for i in range(total_cols):
        cn = all_cn[i]
        if cn == '_pending' or cn.startswith('EmptyKey-'):
            continue

        cn_filtered.append(cn)

        # 英文名：Row6 优先，Row3 补充
        en6 = str(row6[i]).strip() if i < len(row6) and row6[i] is not None else None
        en3 = str(row3[i]).strip() if i < len(row3) and row3[i] is not None else None

        en = None
        if _is_en(en6):
            en = en6
        elif _is_en(en3):
            en = en3

        if en:
            en_list.append(en)
            cn_en[cn] = en
            en_cn[en] = cn
            col_map[en] = i + 1

            t = str(row4[i]).strip() if i < len(row4) and row4[i] is not None else ''
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


# ── 字段信息缓存 ──
_columns_cache = {}


def _ensure_indexed(table_name):
    """确保表已被索引到 SQLite，过期则自动重建。"""
    conn = _get_conn()
    full_path = _get_table_path(table_name)
    if not full_path:
        raise ValueError(f"表 '{table_name}' 不在 table_registry.json 中")

    need_reindex = False
    try:
        cols = [c[1] for c in conn.execute(
            f'PRAGMA table_info([{_clean_identifier(table_name)}])').fetchall()]
        if not cols:
            need_reindex = True
        else:
            if os.path.exists(full_path) and os.path.exists(DB_PATH):
                if os.path.getmtime(full_path) > os.path.getmtime(DB_PATH):
                    print(f"  [WARN] 检测到 '{table_name}' 源表已被外部修改，自动重建索引...")
                    need_reindex = True
    except Exception:
        need_reindex = True

    if need_reindex:
        refresh_index(full_path, table_name)


# 兼容旧接口
def read_headers(table_name):
    """兼容旧接口：返回中文列名列表"""
    return get_columns(table_name)['cn']

get_headers = read_headers

def build_header_map(table_name):
    """兼容旧接口：返回 {英文: 列号} 映射"""
    return get_columns(table_name)['col_map']


def find_row_by_id(xlsx_path, target_id, header_row=1):
    """按主键(第一列)查找行，返回字典

    已索引表自动走SQLite。

    Returns:
        dict: {列名: 值}，None=未找到
    """
    basename = os.path.splitext(os.path.basename(xlsx_path))[0]
    target_str = str(target_id).replace('.0', '')
    if os.path.exists(DB_PATH):
        try:
            cols = [r['name'] for r in query_db(f"PRAGMA table_info([{basename}])")]
            if cols:
                pk = cols[0]
                rows = query_db(
                    f"SELECT * FROM [{_clean_identifier(basename)}] WHERE REPLACE(CAST([{_clean_identifier(pk)}] AS TEXT),'.0','')=?",
                    (target_str,)
                )
                return rows[0] if rows else None
        except Exception:
            pass

    import pandas as pd
    df = read_table(xlsx_path, header_row)
    pk_col = df.columns[0]
    df[pk_col] = df[pk_col].astype(str).str.replace('.0', '', regex=False)
    match = df[df[pk_col] == target_str]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


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
    conn = _get_conn()
    tbl = _clean_identifier(table_name)
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

