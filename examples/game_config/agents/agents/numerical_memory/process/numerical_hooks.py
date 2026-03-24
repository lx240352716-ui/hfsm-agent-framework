# -*- coding: utf-8 -*-
"""
数值策划 Hooks

每个 on_enter / on_exit 函数对应 workflow 中的一个状态。
函数无参数，读文件获取上下文，返回 dict 给 LLM 或下游。

hooks 做确定性操作（查 SQL、搜表、分配 ID），LLM 做判断决策。
"""

import os
import sys
import json
import re

# ── 路径 ──
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保 core 在 sys.path
sys.path.insert(0, os.path.join(BASE, 'scripts', 'core'))

from constants import CONFIGS_DIR, agent_paths

_p = agent_paths('numerical_memory')
NUMERICAL_DIR = _p['agent_dir']
KNOWLEDGE_DIR = _p['knowledge_dir']
DATA_DIR = _p['data_dir']
COORDINATOR_DATA = agent_paths('coordinator_memory')['data_dir']
REGISTRY_PATH = os.path.join(CONFIGS_DIR, 'table_registry.json')

from hook_utils import load_json as _load_json, save_json as _save_json
from hook_utils import load_md as _load_md_raw, init_pending, append_pending


# ── 通用工具 ──

def _load_md(filename):
    """加载知识库 MD 文件"""
    return _load_md_raw(KNOWLEDGE_DIR, filename)


def _search_table(keyword):
    """从 registry 搜索表名（Python 版 search_table.py，避免编码问题）"""
    registry = _load_json(REGISTRY_PATH) or {}
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return [(name, path) for name, path in registry.items() if pattern.search(name)]


def _get_row6_fields(table_name):
    """获取表的 Row6 英文字段名列表（统一用 get_columns）"""
    from table_reader import get_columns
    return get_columns(table_name)['en']


# ────────────────────────────────────────────
# match: 读上游需求 + 查案例
# ────────────────────────────────────────────
def on_enter_match():
    """进入 match: 加载上游需求、系统索引、历史案例"""
    coordinator_output = _load_json(os.path.join(COORDINATOR_DATA, 'output.json'))
    upstream = {}
    if coordinator_output and 'dispatch' in coordinator_output:
        upstream = coordinator_output['dispatch'].get('numerical', {})

    # 初始化 pending（覆盖写，清除上一次残留）
    init_pending(DATA_DIR, upstream.get('task_id', ''), upstream.get('requirement', ''))

    return {
        "knowledge": [
            _load_md('numerical_rules.md'),
            _load_md('systems_index.md'),
            _load_md('numerical_examples.md'),
        ],
        "upstream": upstream,
        "instruction": (
            "你现在是数值策划。请阅读上游需求和系统索引：\n"
            "1. 判断需求涉及哪些游戏系统（对照 systems_index.md 的关键词）\n"
            "2. 查 examples.md 有没有类似案例\n"
            "3. 输出 match 结果：{systems: [...], reference_case: '...' or null}\n"
            "4. 将结果写入 data/match_result.json"
        ),
    }


# ────────────────────────────────────────────
# split: 拆解模块
# ────────────────────────────────────────────
def on_enter_split():
    """进入 split: 加载 match 结果 + 对应系统知识 → 拆模块"""
    match_result = _load_json(os.path.join(DATA_DIR, 'match_result.json'))
    systems = match_result.get('systems', []) if match_result else []

    system_knowledge = []
    system_file_map = {
        'economy': 'system_economy.md',
        'character': 'system_character.md',
        'equipment': 'system_equipment.md',
        'gem_formation': 'system_gem_formation.md',
        'gacha': 'system_gacha.md',
        'activity': 'system_activity.md',
        'misc': 'system_misc.md',
    }
    for sys_name in systems:
        md_file = system_file_map.get(sys_name)
        if md_file:
            system_knowledge.append(_load_md(md_file))

    return {
        "knowledge": [_load_md('numerical_rules.md')] + system_knowledge,
        "match_result": match_result,
        "instruction": (
            "根据 match 结果和系统知识，将需求拆解为独立模块：\n"
            "1. 每个模块 = 一个功能单元（如 道具注册、掉落配置、商城上架）\n"
            "2. 标注每个模块涉及的系统\n"
            "3. 输出格式：{modules: [{name, system, description}, ...]}\n"
            "4. 写入 data/split_result.json"
        ),
    }


# ────────────────────────────────────────────
# confirm: 用户确认拆分（pause 状态，on_exit 保存）
# ────────────────────────────────────────────
def on_exit_confirm():
    """退出 confirm: 保存确认后的拆分结果 + 追加案例"""
    split_result = _load_json(os.path.join(DATA_DIR, 'split_result.json'))
    if not split_result:
        return {"status": "ERROR", "reason": "split_result.json not found"}

    _save_json(os.path.join(DATA_DIR, 'confirmed_split.json'), split_result)

    # 追加到 pending（不直接写 examples.md）
    modules_str = ', '.join(m.get('name', '?') for m in split_result.get('modules', []))
    requirement = split_result.get('requirement', '未知需求')
    append_pending(DATA_DIR, "numerical_examples.md",
                   f"\n### 案例: {requirement}\n- 模块: {modules_str}\n")

    return {"status": "OK", "confirmed_modules": len(split_result.get('modules', []))}


# ────────────────────────────────────────────
# locate: 查真实表名 + 拿字段 + 查参考数据
# ────────────────────────────────────────────
def on_enter_locate():
    """
    进入 locate:
    1. 读 confirmed_split.json
    2. 对每个模块关键词搜 registry 找候选表（Python search，不依赖 grep）
    3. 如果模块已指定 table，查参考数据
    4. 返回候选表 + 参考数据 + 表目录 → LLM 做最终选择和字段过滤
    """
    from table_reader import query_db

    confirmed = _load_json(os.path.join(DATA_DIR, 'confirmed_split.json'))
    if not confirmed:
        return {"status": "ERROR", "reason": "confirmed_split.json not found"}

    table_dir = _load_md('table_directory.md')

    # 对每个模块自动搜候选表
    candidates = {}
    sample_data = {}
    for module in confirmed.get('modules', []):
        module_name = module.get('name', '')
        # 抽取关键词搜索
        keywords = _extract_table_keywords(module_name)
        module_candidates = []
        for kw in keywords:
            matches = _search_table(kw)
            module_candidates.extend(matches)
        # 去重
        seen = set()
        unique = []
        for name, path in module_candidates:
            if name not in seen:
                seen.add(name)
                unique.append({"table": name, "path": path})
        candidates[module_name] = unique

        # 如果模块已指定 table，查参考数据
        table_name = module.get('table')
        if table_name:
            try:
                rows = query_db(f"SELECT * FROM [{table_name}] LIMIT 5")
                sample_data[table_name] = rows
            except Exception:
                sample_data[table_name] = []

    return {
        "knowledge": [
            _load_md('numerical_rules.md'),
            _load_md('locate/rules.md'),
            _load_md('locate/examples.md'),
            _load_md('requirement_structures.md'),
            table_dir,
        ],
        "confirmed_modules": confirmed.get('modules', []),
        "candidates": candidates,
        "sample_data": sample_data,
        "instruction": (
            "对每个确认的模块：\n"
            "1. 查看 candidates 中 hook 已搜到的候选表\n"
            "2. 从候选表或 table_directory.md 选定真实表名\n"
            "3. 字段详情已在 table_directory.md 中（中英文对照）\n"
            "4. 如果需要参考数据，可调 query_db('SELECT * FROM [表名] LIMIT 5')\n"
            "5. 按 rules.md 过滤规则分类字段(fixed/auto/input)\n"
            "6. 输出 locate_result.json:\n"
            "   {modules: [{name, table, fields: [{cn, en, type, default}], next_id}]}\n"
            "7. 写入 data/locate_result.json"
        ),
    }


def _extract_table_keywords(module_name):
    """从模块名提取搜索关键词"""
    keyword_map = {
        '道具': ['Item'],
        '掉落': ['DropGroup'],
        '商城': ['ShopItem'],
        '商店': ['ShopItem', 'Shop'],
        '礼包': ['Item'],
        '奖励': ['Reward', 'DropGroup'],
        '活动': ['Holiday', 'Festival'],
        '抽卡': ['Recruit', 'Gacha'],
        '装备': ['Equipment', 'Equip'],
        '技能': ['Skill'],
        'buff': ['Buff', 'BuffActive'],
        '宝石': ['Gem'],
        '阵法': ['Formation'],
    }
    keywords = []
    for cn, ens in keyword_map.items():
        if cn in module_name:
            keywords.extend(ens)
    if not keywords:
        keywords = [module_name]
    return keywords


def on_exit_locate():
    """
    退出 locate: 用 LLM 给的关键词搜源表，补充参考行候选。
    - 有 _ref_id → 跳过搜索，标 found
    - 有 search_keywords → 搜源表名字列，返回候选
    - 都没有 → 标 not_found
    """
    from table_reader import query_db, get_columns

    locate_result = _load_json(os.path.join(DATA_DIR, 'locate_result.json'))
    if not locate_result:
        return

    for module in locate_result.get('modules', []):
        # LLM 已给 _ref_id → 跳过搜索
        if module.get('_ref_id'):
            module['ref_status'] = 'found'
            continue

        table_name = module.get('table')
        keywords = module.get('search_keywords', [])
        if not table_name or not keywords:
            module['ref_candidates'] = []
            module['ref_status'] = 'not_found'
            continue

        # 找名字/描述列（中文列第二个通常是名字）
        col_info = get_columns(table_name)
        cn_cols = col_info.get('cn', [])
        name_col = cn_cols[1] if len(cn_cols) > 1 else None

        candidates = []
        if name_col:
            for kw in keywords:
                try:
                    rows = query_db(
                        f"SELECT * FROM [{table_name}] WHERE [{name_col}] LIKE ? LIMIT 5",
                        (f"%{kw}%",)
                    )
                    for row in (rows or []):
                        pk_val = str(row.get(cn_cols[0], ''))
                        name_val = str(row.get(name_col, ''))
                        if not any(c['id'] == pk_val for c in candidates):
                            candidates.append({
                                "id": pk_val,
                                "name": name_val,
                                "match_keyword": kw,
                            })
                except Exception:
                    pass

        module['ref_candidates'] = candidates[:10]
        module['ref_status'] = 'found' if candidates else 'not_found'

    _save_json(os.path.join(DATA_DIR, 'locate_result.json'), locate_result)


# ────────────────────────────────────────────
# fill: 展示字段清单，用户填值
# ────────────────────────────────────────────
def on_enter_fill():
    """
    进入 fill:
    读 locate_result.json → 展示过滤后的字段清单
    只展示 need_input 字段，fixed/auto 字段自动填入
    """
    locate_result = _load_json(os.path.join(DATA_DIR, 'locate_result.json'))
    if not locate_result:
        return {"status": "ERROR", "reason": "locate_result.json not found"}

    return {
        "knowledge": [
            _load_md('numerical_rules.md'),
            _load_md('fill/rules.md'),
            _load_md('fill/examples.md'),
            _load_md('requirement_structures.md'),
        ],
        "locate_result": locate_result,
        "instruction": (
            "对每个模块处理参考行和字段填写：\n"
            "1. 读 locate_result.json 的 ref_status：\n"
            "   - found + ref_candidates → 从候选中选最合适的 _ref_id\n"
            "   - found + _ref_id → 已确定，直接使用\n"
            "   - not_found → 告诉用户未找到参考，请提供参考 ID\n"
            "2. 用户提供 ID 后 → 写入 locate_result.json 的 _ref_id → 输出 retry_locate\n"
            "3. 所有模块都有 _ref_id 后，展示 need_input 字段让用户填核心值\n"
            "4. 用户填值后写入 data/filled.json\n"
            "5. 格式: {requirement, tables: {表名: [{_ref_id, _overrides, _note}]}}"
        ),
    }


# ────────────────────────────────────────────
# output: 组装最终 JSON（含 max_id 自动分配 + 字段名统一英文）
# ────────────────────────────────────────────
def on_enter_output():
    """
    进入 output:
    1. 读 filled.json
    2. 对每个表调 max_id 分配主键
    3. 构建 CN→EN 字段映射
    4. 组装标准 output.json（字段统一用 Row6 英文名）
    """
    from table_reader import max_id as get_max_id, get_columns

    filled = _load_json(os.path.join(DATA_DIR, 'filled.json'))

    # 自动分配 ID + 构建字段映射
    allocated_ids = {}
    cn_en_maps = {}
    if filled and 'tables' in filled:
        for table_name in filled['tables']:
            # 获取 Row6 英文字段名
            row6_fields = _get_row6_fields(table_name)
            cn_en_maps[table_name] = row6_fields or []

            # 主键分配（Row6 第一个字段 = 主键）
            row6_fields = cn_en_maps[table_name]
            if row6_fields:
                pk_field_en = row6_fields[0]
                # 用 get_columns 获取 SQLite 中文列名用于 max_id 查询
                col_info = get_columns(table_name)
                cn_cols = col_info['cn']
                pk_field_cn = cn_cols[0] if cn_cols else pk_field_en
                try:
                    current_max = get_max_id(table_name, pk_field_cn) or 0
                    allocated_ids[table_name] = {
                        "pk_field_cn": pk_field_cn,
                        "pk_field_en": pk_field_en,
                        "max_id": current_max,
                        "next_id": current_max + 1,
                    }
                except Exception:
                    allocated_ids[table_name] = {"pk_field_en": pk_field_en, "error": "无法获取 max_id"}

    return {
        "knowledge": [_load_md('numerical_rules.md')],
        "filled_data": filled,
        "allocated_ids": allocated_ids,
        "cn_en_maps": cn_en_maps,
        "instruction": (
            "将用户填好的数据组装为标准 output.json：\n"
            "1. 使用 allocated_ids 中的 next_id 填充主键\n"
            "2. 关联跨表 ID\n"
            "3. ⚠️ 所有字段名必须用 Row6 英文名（参考 cn_en_maps）\n"
            "4. 格式:\n"
            "{\n"
            '  "_schema": "numerical_output",\n'
            '  "task_id": "...",\n'
            '  "requirement": "...",\n'
            '  "reference": "参考的案例",\n'
            '  "tables": { "表名": [{ Row6英文字段: 值 }] }\n'
            "}\n"
            "5. 写入 data/output.json"
        ),
    }


def on_exit_output():
    """退出 output: 验证 output.json + 结构化追加案例"""
    output = _load_json(os.path.join(DATA_DIR, 'output.json'))
    if not output:
        return {"status": "ERROR", "reason": "output.json not found"}

    tables = list(output.get('tables', {}).keys())
    requirement = output.get('requirement', '未知')
    reference = output.get('reference', '无')

    # 追加到 pending（不直接写 examples.md）
    content = f"- 参考: {reference}\n- 涉及表: {', '.join(tables)}\n"
    for tbl, rows in output.get('tables', {}).items():
        row_count = len(rows) if isinstance(rows, list) else 0
        content += f"  - {tbl}: {row_count} 行\n"
    content += "\n"
    append_pending(DATA_DIR, "numerical_examples.md", content)

    return {"status": "OK", "tables": tables, "requirement": requirement}
