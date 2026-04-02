# -*- coding: utf-8 -*-
"""
L3 QA Agent — Hook 函数集（黑盒版）

QA 检查 = 黑盒：只读 output xlsx + 源表，不依赖任何 JSON 数据。
QA 定位 = 出错时看 lineage_trace.json / allocated_ids 等过程量。

3 个状态的 hook：
  on_enter_qa    → 读 output xlsx → 跑 7 条规则 → 通过自动进 merge
  on_enter_merge → COM Excel 写入源表 + 刷新 SQLite 索引
  on_enter_done  → 输出最终结果 + 变更日志
"""

import os
import sys
import json
import glob
from datetime import datetime

# ── 路径設置 ──
sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'core'))
sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'combat'))
sys.path.insert(0, os.path.join(r'G:\op_design', 'references', 'scripts', 'tools'))

from constants import agent_paths
from hook_utils import load_json as _load_json, save_json as _save_json

EXECUTOR_DATA_DIR = agent_paths('executor_memory')['data_dir']
QA_DATA_DIR = agent_paths('qa_memory')['agent_dir']


def _read_xlsx_data(output_dir):
    """
    黑盒读取：扫描 output_dir/*.xlsx，用 COM Excel 读取表头+数据行。
    返回: {table_name: [{col_name: value, ...}, ...]}
    """
    from table_reader import get_com_excel, close_com_excel

    xlsx_files = glob.glob(os.path.join(output_dir, '*.xlsx'))
    if not xlsx_files:
        return {}

    excel = get_com_excel()

    merge_data = {}

    for xlsx_path in xlsx_files:
        table_name = os.path.splitext(os.path.basename(xlsx_path))[0]
        wb = excel.Workbooks.Open(os.path.abspath(xlsx_path))
        ws = wb.ActiveSheet

        max_row = ws.UsedRange.Rows.Count
        max_col = ws.UsedRange.Columns.Count

        # Row 6 = 英文字段名表头
        headers = []
        for c in range(1, max_col + 1):
            h = ws.Cells(6, c).Value
            if h:
                headers.append(str(h).strip())
            else:
                headers.append(f"col_{c}")

        # Row 7+ = 数据行
        rows = []
        for r in range(7, max_row + 1):
            row_data = {}
            for c, h in enumerate(headers, 1):
                val = ws.Cells(r, c).Value
                # COM 返回的 float 如果是整数则转 int 再转 str
                if isinstance(val, float) and val == int(val):
                    val = str(int(val))
                elif val is not None:
                    val = str(val).strip() if isinstance(val, str) else val
                row_data[h] = val
            rows.append(row_data)

        wb.Close(False)
        merge_data[table_name] = rows

    close_com_excel()
    return merge_data


# ────────────────────────────────────────────
# qa: 读 output xlsx → 跑 7 条规则
# ────────────────────────────────────────────
def on_enter_qa():
    """
    黑盒 QA：
    1. 从 executor_done.json 只读 output_dir 路径
    2. 直接读 output_dir/*.xlsx 获取待 merge 数据
    3. 调 qa_runner.run_qa() 校验（纯数据 + 源表）
    4. 通过 → qa_result: pass; 不通过 → rollback JSON
    """
    from qa_runner import run_qa

    # 只用 executor_done.json 获取 output_dir 路径
    executor_done = _load_json(os.path.join(EXECUTOR_DATA_DIR, 'executor_done.json'))
    if not executor_done:
        return {"status": "ERROR", "reason": "executor_done.json not found"}

    output_dir = executor_done.get('output_dir', '')
    if not output_dir or not os.path.exists(output_dir):
        return {"status": "ERROR", "reason": f"output_dir not found: {output_dir}"}

    # 黑盒：直接读 xlsx
    print("\n" + "=" * 50)
    print("  L3 QA 自动校验（黑盒：读 xlsx + 查源表）")
    print("=" * 50)

    merge_data = _read_xlsx_data(output_dir)
    if not merge_data:
        return {"status": "ERROR", "reason": "output_dir 内无 xlsx 文件"}

    print(f"  读取 {len(merge_data)} 个 xlsx: {list(merge_data.keys())}")

    # 跑 QA — 只传数据，不传任何过程量
    try:
        qa_result = run_qa(merge_data=merge_data)
    except ValueError as e:
        # QA 失败 → 生成 rollback JSON（这时才读过程量帮定位）
        output_data = _load_json(os.path.join(EXECUTOR_DATA_DIR, 'output.json')) or {}
        rollback = {
            "_schema": "qa_rollback",
            "timestamp": datetime.now().isoformat(),
            "from": "qa_agent",
            "to": "executor",
            "error_log": str(e),
            "original_output": output_data,
            "failed_checks": str(e).split('\n')[1:] if '\n' in str(e) else [str(e)],
            "retry_hint": "请根据以上报错修正数据后重新 write",
        }
        rollback_path = os.path.join(output_dir, 'rollback_qa_executor.json')
        _save_json(rollback_path, rollback)

        return {
            "status": "QA_FAILED",
            "qa_result": "fail",
            "error_log": str(e),
            "rollback_path": rollback_path,
            "instruction": (
                "QA 校验不通过，已生成打回数据。\n"
                "请审核报错信息，确认后打回执行策划修改。"
            ),
        }

    # QA 通过
    _save_json(os.path.join(QA_DATA_DIR, 'qa_result.json'), {
        "_schema": "qa_result",
        "timestamp": datetime.now().isoformat(),
        "result": "pass",
        "output_dir": output_dir,
    })

    return {
        "status": "OK",
        "qa_result": "pass",
        "output_dir": output_dir,
    }


# ────────────────────────────────────────────
# merge: COM Excel 写入源表 + 刷新索引
# ────────────────────────────────────────────
def on_enter_merge():
    """
    增量合并：
    1. 读 executor output.json 获取 output_dir 和每张表的写入行数
    2. 从 output xlsx 读增量行 → 追加到源 Excel 末尾
    3. 刷新源文件 SQLite 索引
    4. 输出 merge_result.json
    """
    from table_reader import _get_table_path, refresh_index, get_com_excel, open_workbook, close_com_excel

    output_data = _load_json(os.path.join(EXECUTOR_DATA_DIR, 'output.json'))
    if not output_data:
        return {"status": "ERROR", "reason": "output.json not found"}

    output_dir = output_data.get('output_dir', '')
    results = output_data.get('results', {})

    excel = get_com_excel()

    merge_results = {}

    for table_name, rows_written in results.items():
        if rows_written <= 0:
            continue

        src_path = _get_table_path(table_name)
        out_path = os.path.join(output_dir, f"{table_name}.xlsx")

        if not os.path.exists(out_path):
            merge_results[table_name] = {"status": "SKIP", "reason": "output xlsx not found"}
            continue

        # 从 output xlsx 读增量行（跳过表头 Row1-6，读 Row7+）
        out_wb = excel.Workbooks.Open(os.path.abspath(out_path))
        out_ws = out_wb.ActiveSheet
        out_max_row = out_ws.UsedRange.Rows.Count
        max_col = out_ws.UsedRange.Columns.Count

        incremental_rows = []
        for r in range(7, out_max_row + 1):
            row_data = []
            for c in range(1, max_col + 1):
                row_data.append(out_ws.Cells(r, c).Value)
            incremental_rows.append(row_data)
        out_wb.Close(False)

        # 打开源 Excel 追加
        src_wb, src_ws = open_workbook(table_name, read_only=False)
        src_new_start = src_ws.UsedRange.Rows.Count + 1

        for row_idx, row_data in enumerate(incremental_rows):
            target_row = src_new_start + row_idx
            for col_idx, val in enumerate(row_data, 1):
                if val is not None:
                    src_ws.Cells(target_row, col_idx).Value = val

        src_wb.Save()
        src_wb.Close(False)

        # 刷新源文件索引
        refresh_index(src_path, table_name)

        merge_results[table_name] = {
            "status": "OK",
            "rows_merged": rows_written,
            "source_file": src_path,
            "new_start_row": src_new_start,
        }

    close_com_excel()

    # 保存 merge_result.json
    merge_data = {
        "_schema": "merge_result",
        "timestamp": datetime.now().isoformat(),
        "output_dir": output_dir,
        "tables": merge_results,
    }
    _save_json(os.path.join(QA_DATA_DIR, 'merge_result.json'), merge_data)

    return {
        "status": "OK",
        "merge": merge_results,
    }


# ────────────────────────────────────────────
# done: 最终结果 + 变更日志
# ────────────────────────────────────────────
def on_enter_done():
    """
    L3 完成：
    1. 汇总 QA + merge 结果
    2. 输出 l3_done.json（全链路完成信号）
    """
    qa_result = _load_json(os.path.join(QA_DATA_DIR, 'qa_result.json')) or {}
    merge_result = _load_json(os.path.join(QA_DATA_DIR, 'merge_result.json')) or {}
    executor_done = _load_json(os.path.join(EXECUTOR_DATA_DIR, 'executor_done.json')) or {}

    done_data = {
        "_schema": "l3_done",
        "timestamp": datetime.now().isoformat(),
        "requirement": executor_done.get('requirement', ''),
        "task_name": executor_done.get('task_name', ''),
        "qa": qa_result.get('result', 'unknown'),
        "merge": merge_result.get('tables', {}),
        "allocated_ids": executor_done.get('allocated_ids', {}),
        "status": "ALL_DONE",
    }
    _save_json(os.path.join(QA_DATA_DIR, 'l3_done.json'), done_data)

    print("\n" + "=" * 50)
    print("  ✅ L3 全流程完成")
    print("=" * 50)
    print(f"  需求: {done_data['requirement']}")
    for tbl, info in done_data['merge'].items():
        print(f"  {tbl}: {info.get('rows_merged', 0)} rows merged")

    return {
        "status": "ALL_DONE",
        "l3_done": done_data,
    }
