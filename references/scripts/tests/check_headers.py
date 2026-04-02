# -*- coding: utf-8 -*-
"""验证 output xlsx 的 UsedRange 是否正确"""
import sys, os, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from table_reader import get_com_excel, close_com_excel

output_dir = glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'output', '清明节礼包*'))[0]
excel = get_com_excel()

for xlsx in glob.glob(os.path.join(output_dir, '*.xlsx')):
    tbl = os.path.splitext(os.path.basename(xlsx))[0]
    wb = excel.Workbooks.Open(os.path.abspath(xlsx))
    ws = wb.ActiveSheet
    used_rows = ws.UsedRange.Rows.Count
    used_cols = ws.UsedRange.Columns.Count
    # 检查每行是否有数据
    print(f"\n{tbl}: UsedRange={used_rows}x{used_cols}")
    for r in range(1, used_rows + 1):
        first_val = ws.Cells(r, 1).Value
        empty = all(ws.Cells(r, c).Value is None for c in range(1, min(used_cols+1, 8)))
        tag = "空行" if empty else f"有数据({first_val})"
        print(f"  Row{r}: {tag}")
    print(f"  → merge读取 range(7, {used_rows+1}) = Row7~Row{used_rows} = {used_rows - 6} 行数据")
    wb.Close(False)

close_com_excel()
