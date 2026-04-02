# -*- coding: utf-8 -*-
"""CLI: SQLite 查询 — AI agent 从命令行安全查询数据库。

用法:
    python cli/query.py "SELECT * FROM [_Buff] WHERE [perfactor] LIKE '%element%'"
    python cli/query.py "SELECT count(*) as cnt FROM [_Buff]"
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from table_reader import query_db

if len(sys.argv) < 2:
    print('用法: python cli/query.py "SQL语句"', file=sys.stderr)
    sys.exit(1)

sql = ' '.join(sys.argv[1:])
results = query_db(sql)
print(json.dumps(results, ensure_ascii=False, indent=2))
