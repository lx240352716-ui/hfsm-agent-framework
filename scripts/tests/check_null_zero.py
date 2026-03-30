# -*- coding: utf-8 -*-
"""比较 output xlsx 的 null/zero 与参考行"""
import sys, os, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
from constants import REFERENCES_DIR
from table_reader import get_com_excel, close_com_excel

output_base = os.path.join(REFERENCES_DIR, 'output')
dirs = sorted(glob.glob(os.path.join(output_base, '清明节礼包*')), key=os.path.getmtime, reverse=True)
output_dir = dirs[0]
print(f"检查: {output_dir}\n")

excel = get_com_excel()

for xlsx in glob.glob(os.path.join(output_dir, '*.xlsx')):
    tbl = os.path.splitext(os.path.basename(xlsx))[0]
    wb = excel.Workbooks.Open(os.path.abspath(xlsx))
    ws = wb.ActiveSheet
    max_col = ws.UsedRange.Columns.Count
    max_row = ws.UsedRange.Rows.Count
    nulls, zeros = [], []
    for c in range(1, max_col + 1):
        h = ws.Cells(1, c).Value
        v = ws.Cells(2, c).Value
        if v is None: nulls.append(str(h))
        elif v == 0 or v == 0.0: zeros.append(str(h))
    print(f"{tbl}: Null({len(nulls)}) Zero({len(zeros)})")
    print(f"  Null: {nulls[:15]}")
    print(f"  Zero: {zeros}")
    wb.Close(False)

excel.Quit()
