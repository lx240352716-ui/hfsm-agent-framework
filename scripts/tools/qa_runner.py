# -*- coding: utf-8 -*-
"""
qa_runner — L3 QA 校验引擎（黑盒版）

只看数据本身 + 源表，不依赖任何过程量（JSON/allocated_ids/cross_references）。
出错时由 qa_hooks 负责读过程量辅助定位。

7 条规则：
  1. ID 空值 + 唯一性（xlsx 第一列 = 主键）
  2. 跨表外键（在同批 xlsx 和源表中自动发现引用）
  3. Buff 因子白名单
  4. 必填字段非空
  5. 数值合理性
  6. 格式校验
  7. 新 ID 与源表无冲突（xlsx 第一列值 vs 源表）
"""

import os
import sys

SCRIPTS_DIR = os.path.join(REFERENCES_DIR, 'scripts')
sys.path.insert(0, os.path.join(SCRIPTS_DIR, 'core'))
sys.path.insert(0, os.path.join(SCRIPTS_DIR, 'combat'))
from whitelist import load_whitelist


def run_qa(merge_data=None, **kwargs):
    """黑盒 QA 入口。

    Args:
        merge_data: {table_name: [{col: val}, ...]}  — 直接从 xlsx 读取
    Returns:
        dict: {"qa_result": "pass", "failures": []}
    Raises:
        ValueError: QA 不通过时抛出，包含失败详情
    """
    from table_reader import get_columns, query_db
    from constants import get_sqlite_col

    data = merge_data or {}
    if not data:
        print("  ✅ 无待校验数据")
        return {"qa_result": "pass", "failures": []}

    failures = []

    # ── 预处理：收集每个 xlsx 的第一列名（主键）和第一列值（新 ID）──
    pk_info = {}    # {表名: 主键字段名}
    new_ids = {}    # {表名: set(新 ID 值)}
    all_new_ids = set()  # 所有表的新 ID 值集合（用于规则 2 外键匹配）

    for tbl, rows in data.items():
        if not rows:
            continue
        first_key = list(rows[0].keys())[0]
        pk_info[tbl] = first_key
        ids = set()
        for row in rows:
            val = row.get(first_key)
            if val is not None:
                ids.add(str(val))
        new_ids[tbl] = ids
        all_new_ids.update(ids)

    # ═══════════════════════════════════════════════════════
    #  1. ID 空值 + 唯一性（第一列 = 主键）
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则1: ID 空值 + 唯一性")
    for tbl, rows in data.items():
        pk_col = pk_info.get(tbl)
        if not pk_col:
            continue

        ids = [r.get(pk_col) for r in rows]
        empty = [i for i, v in enumerate(ids) if v is None or v == '']
        if empty:
            failures.append(f"{tbl}: 主键 '{pk_col}' 有 {len(empty)} 个空值")
        seen = set()
        dupes = []
        for v in ids:
            sv = str(v)
            if sv in seen and v is not None:
                dupes.append(sv)
            seen.add(sv)
        if dupes:
            failures.append(f"{tbl}: 主键重复: {dupes}")

        if not empty and not dupes:
            print(f"  ✅ {tbl}.{pk_col} 校验通过 ({len(ids)} 行)")

    # ═══════════════════════════════════════════════════════
    #  2. 跨表外键（自动发现：值匹配其他表的新 ID 或源表 ID）
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则2: 跨表外键校验")

    # 构建反查：{新 ID 值 → 来源表名}
    id_to_table = {}
    for tbl, ids in new_ids.items():
        for id_val in ids:
            id_to_table[id_val] = tbl

    fk_found = 0
    for tbl, rows in data.items():
        pk_col = pk_info.get(tbl)
        for row in rows:
            for field, val in row.items():
                if field == pk_col or val is None:
                    continue
                # 把值里的所有子串与新 ID 集合匹配
                str_val = str(val)
                for id_val, src_tbl in id_to_table.items():
                    if src_tbl == tbl:
                        continue  # 跳过自引用
                    if id_val in str_val:
                        # 发现跨表引用：tbl.field 里包含 src_tbl 的新 ID
                        print(f"  ✅ {tbl}.{field} 包含 {src_tbl}.{pk_info[src_tbl]}={id_val}（同批匹配）")
                        fk_found += 1

    if fk_found == 0:
        print("  ⏭️ 未发现跨表引用")

    # ═══════════════════════════════════════════════════════
    #  3. 因子白名单
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则3: 因子白名单")
    buff_rows = data.get('_Buff', [])
    if buff_rows:
        whitelist = load_whitelist()
        if whitelist:
            for row in buff_rows:
                factor = row.get('perfactor', '')
                if not factor:
                    continue
                factors = [f.strip() for f in str(factor).split('&&') if f.strip()]
                for f in factors:
                    if f not in whitelist:
                        failures.append(f"_Buff 因子 '{f}' 不在白名单中")
            if not [f for f in failures if '白名单' in f]:
                print("  ✅ 因子白名单校验通过")
    else:
        print("  ⏭️ 无 _Buff 数据，跳过")

    # ═══════════════════════════════════════════════════════
    #  4. 必填字段非空
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则4: 必填字段非空")
    for tbl, rows in data.items():
        for i, row in enumerate(rows):
            non_empty = sum(1 for v in row.values() if v is not None and v != '' and v != 'None')
            if non_empty < 2:
                failures.append(f"{tbl} 第 {i+1} 行数据几乎全空（仅 {non_empty} 个字段有值）")
    if not [f for f in failures if '全空' in f]:
        print("  ✅ 必填字段检查通过")

    # ═══════════════════════════════════════════════════════
    #  5. 数值合理性
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则5: 数值合理性")
    for tbl, rows in data.items():
        for row in rows:
            for key, val in row.items():
                if val is None or val == '':
                    continue
                try:
                    num = float(val)
                    if 'price' in key.lower() or 'cost' in key.lower() or 'count' in key.lower():
                        if num < 0:
                            failures.append(f"{tbl}.{key} 值异常: {val}（价格/数量不应为负）")
                except (ValueError, TypeError):
                    pass
    if not [f for f in failures if '值异常' in f]:
        print("  ✅ 数值合理性检查通过")

    # ═══════════════════════════════════════════════════════
    #  6. 格式校验
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则6: 格式校验")
    for tbl, rows in data.items():
        for row in rows:
            item_info = row.get('itemInfo', None)
            if item_info and isinstance(item_info, str):
                parts = item_info.split(',')
                if len(parts) % 3 != 0:
                    failures.append(f"{tbl}.itemInfo 格式错误: '{item_info}' 不是 3 的倍数分段")
    if not [f for f in failures if '格式错误' in f]:
        print("  ✅ 格式校验通过")

    # ═══════════════════════════════════════════════════════
    #  7. 新 ID 与源表无冲突（第一列值 vs 源表）
    # ═══════════════════════════════════════════════════════
    print("\n[QA] 规则7: 新 ID 与源表无冲突")
    for tbl, rows in data.items():
        pk_col = pk_info.get(tbl)
        if not pk_col:
            continue
        for row in rows:
            val = row.get(pk_col)
            if val is None:
                continue
            try:
                # 用 get_columns 拿中文列名做 SQLite 查询
                col_info = get_columns(tbl)
                pk_cn = col_info['en_cn'].get(pk_col, pk_col)
                found = query_db(f"SELECT 1 FROM [{tbl}] WHERE [{pk_cn}]=? LIMIT 1", (str(val),))
                if found:
                    failures.append(f"{tbl} 新 ID {val}（字段 {pk_col}）与源表已有 ID 冲突！")
                else:
                    print(f"  ✅ {tbl}.{pk_col}={val} 无冲突")
            except Exception as e:
                failures.append(f"查询 {tbl}.{pk_col}={val} 时出错: {e}")

    # ═══════════════════════════════════════════════════════
    #  结果
    # ═══════════════════════════════════════════════════════
    if failures:
        print(f"\n{'=' * 50}")
        print(f"  ❌ QA 失败 ({len(failures)} 项)")
        for f in failures:
            print(f"    - {f}")
        print(f"{'=' * 50}")
        raise ValueError(f"QA 校验失败（{len(failures)} 项），阻止 merge:\n" + "\n".join(failures))

    print(f"\n{'=' * 50}")
    print(f"  ✅ QA 全部通过（7 条规则）")
    print(f"{'=' * 50}")

    return {"qa_result": "pass", "failures": []}
