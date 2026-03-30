# -*- coding: utf-8 -*-
"""清除测试数据：源表行 + output 目录 + agent 中间数据"""
import sys, os, glob, shutil, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from constants import REFERENCES_DIR, AGENTS_DIR
from table_reader import max_id, get_columns, _get_table_path, refresh_index, get_com_excel, open_workbook, close_com_excel

# ── 清除 output 目录 ──
OUTPUT_DIR = os.path.join(REFERENCES_DIR, 'output')
for d in glob.glob(os.path.join(OUTPUT_DIR, '清明节礼包*')):
    shutil.rmtree(d)
    print(f"  [output] 删除 {os.path.basename(d)}")

# ── 清除 agent 中间数据 ──
AGENT_DATA_DIRS = [
    os.path.join(AGENTS_DIR, 'executor_memory', 'data'),
    os.path.join(AGENTS_DIR, 'qa_memory', 'data'),
]
CLEAN_FILES = [
    'execute_result.json', 'align_result.json', 'draft_filled.json',
    'filled_result.json', 'output.json', 'executor_done.json',
    'qa_result.json', 'merge_result.json',
]
for d in AGENT_DATA_DIRS:
    for f in CLEAN_FILES:
        p = os.path.join(d, f)
        if os.path.exists(p):
            os.remove(p)
            rel = os.path.relpath(p, REFERENCES_DIR)
            print(f"  [data] 删除 {rel}")

expected = {"Item": 16010011, "_DropGroup": 300110, "_ShopItem": 214005}

excel = get_com_excel()

for tbl, exp_max in expected.items():
    col_info = get_columns(tbl)
    pk_cn = col_info['cn'][0]
    current = max_id(tbl, pk_cn)
    while current > exp_max:
        wb, ws = open_workbook(tbl, read_only=False)
        last = ws.UsedRange.Rows.Count
        ws.Rows(last).Delete()
        wb.Save()
        wb.Close(False)
        refresh_index(_get_table_path(tbl), tbl)
        print(f"  [{tbl}] 删除 row {last}, id={current}")
        current = max_id(tbl, pk_cn)

close_com_excel()

print("\n验证:")
for tbl, exp_max in expected.items():
    col_info = get_columns(tbl)
    current = max_id(tbl, col_info['cn'][0])
    status = "✅" if current == exp_max else "❌"
    print(f"  {tbl}: max_id={current} {status}")
