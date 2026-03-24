# -*- coding: utf-8 -*-
"""
全局常量注册表。

所有表配置、字段契约、路径常量统一在此定义。
其他模块通过 from constants import XXX 引用，禁止私有定义。
"""

import os

# ══════════════════════════════════════════════════════════════
# 路径常量
# ══════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
EXCEL_DIR = os.path.join(BASE_DIR, 'excel')
REFERENCES_DIR = os.path.join(BASE_DIR, 'references')
OUTPUT_DIR = os.path.join(REFERENCES_DIR, 'output')
DESIGN_DIR = os.path.join(REFERENCES_DIR, 'design')
CORE_DIR = os.path.join(REFERENCES_DIR, 'scripts', 'core')
CONFIGS_DIR = os.path.join(REFERENCES_DIR, 'scripts', 'configs')
PIPELINES_DIR = os.path.join(CONFIGS_DIR, 'pipelines')
RULES_DIR = os.path.join(CONFIGS_DIR, 'rules')
DB_PATH = os.path.join(CORE_DIR, 'table_index.db')
AGENTS_DIR = os.path.join(REFERENCES_DIR, 'agents')


def agent_paths(agent_name):
    """返回某个 Agent 的标准子目录路径。

    Returns:
        dict: {agent_dir, knowledge_dir, data_dir, process_dir}
    """
    agent_dir = os.path.join(AGENTS_DIR, agent_name)
    return {
        'agent_dir': agent_dir,
        'knowledge_dir': os.path.join(agent_dir, 'knowledge'),
        'data_dir': os.path.join(agent_dir, 'data'),
        'process_dir': os.path.join(agent_dir, 'process'),
    }

# ══════════════════════════════════════════════════════════════
# 表主键列名映射
#   动态从 SQLite Row6 读取，首次查询后缓存。
#   规则：取 Row6 英文列名中第一个以 'Id' 结尾（或等于 'id'）的列。
#   _PK_HINT 仅在自动推断失败时作为 fallback。
# ══════════════════════════════════════════════════════════════

_PK_HINT = {
    '_Buff': 'buffId',
    'BuffActive': 'buffId',
    'FightBuff': 'fightBuffId',
    '_BuffCondition': 'conditionId',
}

_pk_cache = {}


def get_pk_col(table_name):
    """动态获取表的主键列名（Row6 英文）。

    优先从 SQLite Row6 自动推断（取第一个 *Id 或 *id 列），
    推断失败时 fallback 到 _PK_HINT。结果缓存。
    """
    if table_name in _pk_cache:
        return _pk_cache[table_name]

    try:
        from table_reader import get_columns
        en_cols = get_columns(table_name)['en'] or []
        # 找第一个以 Id/id 结尾的列（跳过 EmptyKey、Unnamed）
        for col in en_cols:
            if col.startswith('EmptyKey') or col.startswith('Unnamed'):
                continue
            if col == 'id' or (len(col) > 2 and col.endswith('Id') or col.endswith('id')):
                _pk_cache[table_name] = col
                return col
    except Exception:
        pass

    # fallback
    hint = _PK_HINT.get(table_name)
    if hint:
        _pk_cache[table_name] = hint
    return hint


# 向后兼容：旧代码用 KEY_COLS[tbl] 直接访问
class _KeyColsProxy(dict):
    """代理字典，读取时动态调用 get_pk_col()。"""
    def __getitem__(self, key):
        val = get_pk_col(key)
        if val is None:
            raise KeyError(key)
        return val

    def get(self, key, default=None):
        val = get_pk_col(key)
        return val if val is not None else default

    def __contains__(self, key):
        return get_pk_col(key) is not None

    def keys(self):
        return _PK_HINT.keys()

    def items(self):
        return {k: get_pk_col(k) for k in _PK_HINT}.items()


KEY_COLS = _KeyColsProxy()

# ══════════════════════════════════════════════════════════════
# Row6 英文名 → SQLite 实际列名 转换
# ══════════════════════════════════════════════════════════════

_sqlite_col_cache = {}  # {table_name: {row6_en_lower: sqlite_col}}


def get_sqlite_col(table_name, row6_en_name):
    """将 Row6 英文列名转换为 SQLite 实际列名。

    SQLite 列名来自 Excel 导入时的 header，可能是中文或混合名。
    而 Row6 英文名是数据行中的值。两者可能不同。

    Args:
        table_name: 表名
        row6_en_name: Row6 英文列名
    Returns:
        str: SQLite 实际列名，如果找不到则返回 row6_en_name 本身
    """
    if table_name not in _sqlite_col_cache:
        try:
            from table_reader import get_columns, _get_conn, _clean_identifier
            # 获取 SQLite 实际列名
            conn = _get_conn()
            sqlite_cols = [c[1] for c in conn.execute(
                f'PRAGMA table_info([{_clean_identifier(table_name)}])').fetchall()]
            # 获取 Row6 英文列名
            en_cols = get_columns(table_name)['en'] or []
            # 建映射
            mapping = {}
            for sqlite_c, en_c in zip(sqlite_cols, en_cols):
                mapping[en_c.lower()] = sqlite_c
            _sqlite_col_cache[table_name] = mapping
        except Exception:
            _sqlite_col_cache[table_name] = {}

    return _sqlite_col_cache.get(table_name, {}).get(
        row6_en_name.lower(), row6_en_name
    )

# ══════════════════════════════════════════════════════════════
# 必填字段契约（Row6 英文字段名，设计 JSON 必须包含）
# ══════════════════════════════════════════════════════════════

REQUIRED_FIELDS = {
    '_Buff': [
        'perfactor', 'isDebuff', 'canBeCleared',
        'afterActiveCount', 'beforeActiveCount', 'round',
        'attCount', 'defCount', 'limitedCount',
        'accumIdCount', 'someData',
        'additionalBuffs',
    ],
    'BuffActive': ['buffId', 'grade', 'buffParam1', 'buffParam1Levelup'],
    'FightBuff': [
        'buffTimings', 'buffTargets', 'buffConditions', 'buffOddRules',
        'buffList', 'buffGradeList',
    ],
    '_BuffCondition': ['conditionClass', 'conditionParam'],
}

# ══════════════════════════════════════════════════════════════
# 因子白名单路径
# ══════════════════════════════════════════════════════════════

WHITELIST_PATH = os.path.join(RULES_DIR, 'factor_whitelist.json')
