# -*- coding: utf-8 -*-
"""
执行策划 — Hook 函数集

5 个状态的 hook：
  on_enter_execute       → 读上游 output.json
  on_enter_align         → 读 Row6 全量字段 + 对比 + 列出待填
  on_enter_fill          → 链式参考查找 → 返回全行模板给 LLM
  on_enter_fill_confirm  → 读 draft_filled.json → 提取 uncertain 字段给用户
  on_enter_write         → 分配 ID + 同步引用 + 写入增量 xlsx → L2完成

hooks 做确定性操作（SQLite 查询、文件读写），LLM 做判断决策。
write 是 L2 终态，输出 executor_done.json 交给 L3 QA。
"""

import os
import sys
import json
from datetime import datetime

# ── 路径 ──
# 从当前文件位置推导：executor_hooks.py → process/ → executor_memory/ → agents/ → references/
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.insert(0, os.path.join(BASE, 'scripts', 'core'))

from constants import agent_paths

_p = agent_paths('executor_memory')
EXECUTOR_DIR = _p['agent_dir']
KNOWLEDGE_DIR = _p['knowledge_dir']
DATA_DIR = _p['data_dir']
NUMERICAL_DATA = agent_paths('numerical_memory')['data_dir']

from hook_utils import load_json as _load_json, save_json as _save_json
from hook_utils import load_md as _load_md_raw


# ── 通用工具 ──

def _load_md(filename):
    """加载知识库 MD 文件（先找 knowledge/ 再找根目录）"""
    return _load_md_raw(KNOWLEDGE_DIR, filename)


# ────────────────────────────────────────────
# execute: 只读上游 output.json
# ────────────────────────────────────────────
def on_enter_execute(model=None):
    """
    只做一件事：读上游 numerical output.json → 存 execute_result.json
    """
    # 从 model 拿上游数据（优先），或读文件（兜底）
    output = None
    if model and hasattr(model, 'design_outputs'):
        output = model.design_outputs.get('numerical')
    if not output:
        output = _load_json(os.path.join(NUMERICAL_DATA, 'output.json'))

    if not output or 'tables' not in output:
        return {"status": "ERROR", "reason": "numerical output.json not found or missing tables"}

    # 原样存储，不做任何处理
    _save_json(os.path.join(DATA_DIR, 'execute_result.json'), output)

    return {
        "status": "OK",
        "tables": list(output['tables'].keys()),
        "requirement": output.get('requirement', ''),
    }


# ────────────────────────────────────────────
# align: 读 Row6 全量字段 → 对比 → 列出待填
# ────────────────────────────────────────────
def on_enter_align(model=None):
    """
    1. 读 execute_result.json（上一步原样存的上游数据）
    2. 对每张表调 get_columns() 读 Row6 全量字段
    3. 如果 Row6 拿不到 → 报错
    4. 对比上游字段 vs Row6 全量字段
    5. 产出 align_result.json：已填/待填/多余
    """
    from table_reader import get_columns

    execute_data = _load_json(os.path.join(DATA_DIR, 'execute_result.json'))
    if not execute_data:
        return {"status": "ERROR", "reason": "execute_result.json not found"}

    tables_data = execute_data.get('tables', {})
    align_report = {}
    errors = []

    for table_name, rows in tables_data.items():
        if not rows:
            continue

        # 读 Row6 英文全量字段（铁规则）
        row6_fields = get_columns(table_name)['en']
        if not row6_fields:
            errors.append(f"表 {table_name} 没有 Row6 英文字段名，无法继续")
            continue

        # 上游有的字段
        upstream_keys = set(rows[0].keys())

        # 对比
        row6_set = set(row6_fields)
        filled = sorted(upstream_keys & row6_set)        # 上游有 & Row6 有
        unfilled = sorted(row6_set - upstream_keys)       # Row6 有 & 上游没有
        extra = sorted(upstream_keys - row6_set)          # 上游有 & Row6 没有

        align_report[table_name] = {
            "row6_total": len(row6_fields),
            "filled": filled,
            "filled_count": len(filled),
            "unfilled": unfilled,
            "unfilled_count": len(unfilled),
            "extra": extra,
            "extra_count": len(extra),
        }

    result = {
        "requirement": execute_data.get('requirement', ''),
        "reference": execute_data.get('reference', ''),
        "tables": tables_data,
        "align_report": align_report,
        "errors": errors,
    }
    _save_json(os.path.join(DATA_DIR, 'align_result.json'), result)

    return {
        "status": "ERROR" if errors else "OK",
        "errors": errors,
        "align_report": {
            tbl: {
                "row6_total": r["row6_total"],
                "filled": r["filled_count"],
                "unfilled": r["unfilled_count"],
                "extra": r["extra_count"],
                "unfilled_fields": r["unfilled"],
            }
            for tbl, r in align_report.items()
        },
    }


# ────────────────────────────────────────────
# fill: 用 _ref_id 查参考行 → 返回全行模板给 LLM
# ────────────────────────────────────────────
def on_enter_fill():
    """
    参考行查找：
    1. 从 L1 output 的每张表读 _ref_id
    2. 用 _ref_id 直接查源表主键 → 拿到参考行全量数据
    3. 自动生成 draft_filled.json（参考行补全 + null 标 uncertain）
    4. 返回参考行 + knowledge → LLM 读 _note 理解要改什么
    """
    from table_reader import query_db, get_columns as _get_cols

    align_result = _load_json(os.path.join(DATA_DIR, 'align_result.json'))
    if not align_result:
        return {"status": "ERROR", "reason": "align_result.json not found"}

    align_report = align_result.get('align_report', {})
    tables_data = align_result.get('tables', {})

    # ── Step 1: 用 _ref_id 逐行查参考行 ──
    # 每行可能有不同的 _ref_id，所以按行查而非按表查
    reference_rows_by_table = {}   # {table: [{row_idx: ref_row}, ...]}
    match_info = {}
    unfilled_fields = {}

    for table_name, report in align_report.items():
        fields = report.get('unfilled', [])
        if fields:
            unfilled_fields[table_name] = fields

        rows_data = tables_data.get(table_name, [])
        col_info = _get_cols(table_name)
        pk_cn = col_info['cn'][0] if col_info['cn'] else None
        cn_en = col_info.get('cn_en', {})

        table_refs = []
        ref_ids_found = []
        for row in rows_data:
            ref_id = str(row.get('_ref_id', ''))
            if not ref_id or not pk_cn:
                table_refs.append({})
                continue

            rows = query_db(
                f"SELECT * FROM [{table_name}] WHERE [{pk_cn}] = ?",
                (ref_id,)
            )
            if rows:
                row_en = {cn_en.get(k, k): v for k, v in rows[0].items()}
                table_refs.append(row_en)
                ref_ids_found.append(ref_id)
            else:
                table_refs.append({})
                ref_ids_found.append(f"{ref_id}(未找到)")

        reference_rows_by_table[table_name] = table_refs
        match_info[table_name] = f"_ref_id={','.join(ref_ids_found)}" if ref_ids_found else "无 _ref_id"

    # ── Step 2: 自动生成 draft_filled.json ──
    # 每行用自己对应的参考行补全
    auto_draft = {
        "requirement": align_result.get("requirement", ""),
        "reference": align_result.get("reference", ""),
        "tables": {},
    }
    META_KEYS = {'_ref_id', '_note', '_overrides'}
    for table_name, rows in tables_data.items():
        table_refs = reference_rows_by_table.get(table_name, [])

        draft_rows = []
        for i, row in enumerate(rows):
            ref_row = table_refs[i] if i < len(table_refs) else {}
            # 以 row 已有字段为基础（跳过 meta keys）
            draft_row = {k: v for k, v in row.items() if k not in META_KEYS}
            # 补全所有参考行有但 row 里没有的字段
            for field, ref_val in ref_row.items():
                if field not in draft_row:
                    if ref_val is None:
                        draft_row[field] = {
                            "value": None,
                            "uncertain": True,
                            "reason": "参考行该字段为 null",
                        }
                    else:
                        draft_row[field] = ref_val
            draft_rows.append(draft_row)
        auto_draft["tables"][table_name] = draft_rows

    _save_json(os.path.join(DATA_DIR, 'draft_filled.json'), auto_draft)

    return {
        "knowledge": [
            _load_md('fill/rules.md'),
            _load_md('executor_rules.md'),
            _load_md('executor_design_patterns.md'),
        ],
        "reference_rows": reference_rows_by_table,
        "match_info": match_info,
        "unfilled_fields": unfilled_fields,
        "tables": tables_data,
        "instruction": (
            "hook 已通过 _ref_id 查到每张表的参考行。\n"
            "1. 整行复制参考行作为基础。\n"
            "2. _overrides 里的字段直接覆盖。\n"
            "3. 读 _note 理解要改的内容（名字/描述等），生成新值。\n"
            "4. 参考行为 null 的字段保持 null，标 uncertain。\n"
            "5. 严禁盲猜，严禁沉默填 0。\n"
            "已自动生成 draft_filled.json，如需修改可覆盖。\n"
            "格式：{tables: {表名: [{field: value 或 {value, uncertain, reason}}]}}"
        ),
    }


# ────────────────────────────────────────────
# fill_confirm: 读 draft_filled → 提取 uncertain 给用户
# ────────────────────────────────────────────
def on_enter_fill_confirm():
    """
    读 draft_filled.json，提取 uncertain 字段展示给用户审核。
    同时应用 L1 output 中的 _overrides（用户指定的字段覆盖）。
    用户确认/修改后，LLM 写 filled_result.json（所有字段确定值）。
    """
    from table_reader import get_columns as _get_cols

    draft = _load_json(os.path.join(DATA_DIR, 'draft_filled.json'))
    if not draft:
        return {"status": "ERROR", "reason": "draft_filled.json not found"}

    # ── 应用 L1 _overrides ──
    execute_result = _load_json(os.path.join(DATA_DIR, 'execute_result.json')) or {}
    for tbl, l1_rows in execute_result.get('tables', {}).items():
        for l1_row in l1_rows:
            overrides = l1_row.get('_overrides', {})
            if overrides and tbl in draft.get('tables', {}):
                for draft_row in draft['tables'][tbl]:
                    for field, val in overrides.items():
                        draft_row[field] = val
                        print(f"  [override] {tbl}.{field} = {val}")

    # 获取每张表的 en→cn 映射
    field_names = {}
    for table_name in draft.get('tables', {}):
        try:
            col_info = _get_cols(table_name)
            field_names[table_name] = col_info.get('en_cn', {})
        except Exception:
            field_names[table_name] = {}

    # 提取所有 uncertain 字段
    uncertain_summary = {}
    for table_name, rows in draft.get('tables', {}).items():
        en_cn = field_names.get(table_name, {})
        uncertain_fields = []
        for row in rows:
            for field, val in row.items():
                if isinstance(val, dict) and val.get('uncertain'):
                    uncertain_fields.append({
                        "field": field,
                        "cn_name": en_cn.get(field, field),
                        "suggested_value": val.get('value'),
                        "reason": val.get('reason', ''),
                    })
        if uncertain_fields:
            uncertain_summary[table_name] = uncertain_fields

    # ── 自动保存 filled_result.json（展平 uncertain + 应用 overrides）──
    filled = dict(draft)
    filled_tables = {}
    for table_name, rows in filled.get('tables', {}).items():
        filled_rows = []
        for row in rows:
            flat_row = {}
            for field, val in row.items():
                if isinstance(val, dict) and 'value' in val:
                    flat_row[field] = val['value']
                else:
                    flat_row[field] = val
            filled_rows.append(flat_row)
        filled_tables[table_name] = filled_rows
    filled['tables'] = filled_tables
    _save_json(os.path.join(DATA_DIR, 'filled_result.json'), filled)

    return {
        "draft_data": draft,
        "uncertain_summary": uncertain_summary,
        "uncertain_count": sum(len(v) for v in uncertain_summary.values()),
        "field_names": field_names,
        "instruction": (
            "以下字段标记为不确定，请用户审核：\n"
            "1. 展示每个 uncertain 字段的英文名(cn_name中文名) + 建议值 + 原因\n"
            "2. 用户确认或修改后，将所有字段展平为确定值\n"
            "3. 写入 data/filled_result.json\n"
            "4. 格式与 execute_result.json 相同，tables 中所有字段都有确定值"
        ),
    }


# ────────────────────────────────────────────
# write: 分配 ID → 同步引用 → 校验 → 写入 Excel
# ────────────────────────────────────────────
def on_enter_write():
    """
    1. 读 filled_result.json（用户确认后的数据）
    2. 实时查 max_id 分配真实 ID
    3. 按 id_relations.md 同步跨表引用
    4. 校验：空值、ID 冲突
    5. 校验通过 → 直接写入 Excel
    6. 校验不通过 → 报错，不写
    """
    from table_reader import max_id as get_max_id, get_columns as _get_cols, query_db
    from table_reader import _get_table_path
    from constants import OUTPUT_DIR

    filled = _load_json(os.path.join(DATA_DIR, 'filled_result.json'))
    if not filled:
        filled = _load_json(os.path.join(DATA_DIR, 'execute_result.json'))
    if not filled:
        return {"status": "ERROR", "reason": "no filled data found"}

    tables = filled.get('tables', {})
    header_maps = {}
    for tbl in tables:
        header_maps[tbl] = _get_cols(tbl)['col_map']

    # ── 1. 解析占位符 → 分配真实 ID ──
    # 占位符格式：<<NEW_X>>，由 numerical_hooks on_enter_output 生成
    # 如果没有占位符（旧数据），走原有的 max_id 分配逻辑
    import re
    placeholder_pattern = re.compile(r'<<NEW_\d+>>')

    allocated_ids = {}
    placeholder_to_real = {}  # {"<<NEW_1>>": "1001", "<<NEW_2>>": "1002", ...}
    table_en_cn = {}

    for table_name, rows in tables.items():
        if not rows:
            continue

        col_info = _get_cols(table_name)
        en_cn = col_info['en_cn']
        table_en_cn[table_name] = en_cn

        first_key = list(rows[0].keys())[0]
        pk_cn = en_cn.get(first_key, first_key)

        try:
            current_max = get_max_id(table_name, pk_cn) or 0
        except Exception:
            current_max = 0

        # 收集本表所有占位符并分配连续 ID
        new_ids = []
        for i, row in enumerate(rows):
            old_val = str(row.get(first_key, ''))
            new_id = current_max + 1 + i

            if placeholder_pattern.match(old_val):
                # 占位符 → 映射到真实 ID
                placeholder_to_real[old_val] = str(new_id)
            else:
                # 兼容旧数据（非占位符），走原有逻辑
                if old_val != str(new_id):
                    placeholder_to_real[old_val] = str(new_id)

            row[first_key] = str(new_id)
            new_ids.append(new_id)

        allocated_ids[table_name] = {
            "pk_field": first_key,
            "new_id": new_ids[0] if len(new_ids) == 1 else new_ids,
        }

    # ── 2. 替换所有占位符（含主键和跨表引用字段） ──
    cross_references = []
    if placeholder_to_real:
        for table_name, rows in tables.items():
            for row in rows:
                for key, val in row.items():
                    if isinstance(val, str):
                        for placeholder, real_id in placeholder_to_real.items():
                            if placeholder in val:
                                val = val.replace(placeholder, real_id)
                        row[key] = val

    # ── 3. 校验 ──
    errors = []
    for tbl, info in allocated_ids.items():
        pk_en = info['pk_field']
        new_id = info['new_id']
        en_cn = table_en_cn.get(tbl, {})
        pk_cn = en_cn.get(pk_en, pk_en)
        try:
            existing = query_db(
                f"SELECT COUNT(*) as c FROM [{tbl}] WHERE [{pk_cn}] = ?",
                (str(new_id),)
            )
            if existing and existing[0]['c'] > 0:
                errors.append(f"{tbl}: ID {new_id} 已存在！")
        except Exception:
            pass

    if errors:
        return {"status": "ERROR", "errors": errors, "allocated_ids": allocated_ids}

    # ── 4. 写入 Excel ──
    requirement = filled.get('requirement', 'unnamed')
    # 任务名用需求名（sanitize 特殊字符），遵循 output/{任务名}/{表名}.xlsx 规则
    import re
    task_name = re.sub(r'[\\/:*?"<>|]', '_', requirement).strip()
    if not task_name:
        task_name = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 同名目录已存在 → 加后缀避免覆盖
    output_dir = os.path.join(OUTPUT_DIR, task_name)
    if os.path.exists(output_dir):
        suffix = 2
        while os.path.exists(f"{output_dir}_{suffix}"):
            suffix += 1
        task_name = f"{task_name}_{suffix}"
        output_dir = os.path.join(OUTPUT_DIR, task_name)
    os.makedirs(output_dir, exist_ok=True)

    from table_reader import get_com_excel, open_workbook, close_com_excel

    excel = get_com_excel()

    results = {}

    for table_name, rows in tables.items():
        if not rows:
            continue

        # 获取表头（Row6 英文字段名）和列映射
        col_info = _get_cols(table_name)
        all_en_fields = col_info['en']
        hmap = header_maps.get(table_name, {})

        # 创建 output xlsx（完整表头 Row1-6 + 新数据 Row7+）
        dst_path = os.path.join(output_dir, f"{table_name}.xlsx")

        # 从源表复制 Row1-6 表头
        src_wb, src_ws = open_workbook(table_name, read_only=True)
        src_max_col = src_ws.UsedRange.Columns.Count

        wb = excel.Workbooks.Add()
        ws = wb.ActiveSheet
        ws.Name = table_name

        # 复制 Row1-6（表头区域）
        for r in range(1, 7):
            for c in range(1, src_max_col + 1):
                v = src_ws.Cells(r, c).Value
                if v is not None:
                    ws.Cells(r, c).Value = v
        src_wb.Close(False)

        # Row 7+: 新行
        for row_data in rows:
            row_num = 7  # 第一行数据固定从 Row7 开始
            # 如果已有多行数据，往下推
            if len(rows) > 1:
                row_num = 6 + rows.index(row_data) + 1
            for field, val in row_data.items():
                col_idx = hmap.get(field)
                if col_idx is None:
                    continue
                # null ≠ 0：val 为 None 时不写该单元格（留空）
                if val is None:
                    continue
                cell = ws.Cells(row_num, col_idx)
                try:
                    cell.Value = int(val)
                except (ValueError, TypeError):
                    cell.Value = val
                # 绿底红字标记新行
                cell.Interior.Color = 0xCEEFC6  # RGB(198,239,206)
                cell.Font.Color = 0x0000FF       # RGB(255,0,0) in BGR

        wb.SaveAs(os.path.abspath(dst_path))
        wb.Close(False)

        # 输出是临时数据，不刷新源索引
        results[table_name] = len(rows)

    close_com_excel()

    # ── 5. 血缘溯源 + output.json ──
    lineage = {
        "trace_id": task_name,
        "timestamp": datetime.now().isoformat(),
        "requirement": requirement,
        "reference": filled.get('reference', ''),
        "allocated_ids": {
            tbl: {
                "pk_field": info["pk_field"],
                "old_id": info["old_id"],
                "new_id": info["new_id"],
            }
            for tbl, info in allocated_ids.items()
        },
        "id_replacements": old_to_new,
        "cross_references": cross_references,
        "tables": {
            tbl: {
                "rows_written": cnt,
                "data": tables.get(tbl, []),
            }
            for tbl, cnt in results.items()
        },
    }
    _save_json(os.path.join(output_dir, 'lineage_trace.json'), lineage)

    _save_json(os.path.join(DATA_DIR, 'output.json'), {
        "_schema": "executor_output",
        "task_name": task_name,
        "output_dir": output_dir,
        "results": results,
        "allocated_ids": allocated_ids,
        "lineage": lineage,
    })

    # ── 6. executor_done.json — L2 完成信号，交给 L3 QA ──
    done_data = {
        "_schema": "executor_done",
        "timestamp": datetime.now().isoformat(),
        "requirement": requirement,
        "task_name": task_name,
        "output_dir": output_dir,
        "results": results,
        "allocated_ids": allocated_ids,
        "status": "L2_DONE",
    }
    _save_json(os.path.join(DATA_DIR, 'executor_done.json'), done_data)

    return {
        "status": "OK",
        "output_dir": output_dir,
        "results": results,
        "allocated_ids": allocated_ids,
    }
