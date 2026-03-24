# -*- coding: utf-8 -*-
"""CLI: 因子白名单校验/注册 — AI agent 查询或注册因子。

用法:
    python cli/check_factor.py speed                           # 查询因子
    python cli/check_factor.py --register name "描述" 7 0      # 注册新因子
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'references', 'scripts', 'combat'))
from whitelist import validate_factor, register_factor, load_whitelist

if len(sys.argv) < 2:
    print('用法: python cli/check_factor.py <factor_name>', file=sys.stderr)
    print('      python cli/check_factor.py --register <name> <desc> [type] [pct]', file=sys.stderr)
    sys.exit(1)

if sys.argv[1] == '--register':
    if len(sys.argv) < 4:
        print('用法: python cli/check_factor.py --register <name> <desc> [type] [pct]', file=sys.stderr)
        sys.exit(1)
    name = sys.argv[2]
    desc = sys.argv[3]
    buff_type = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    pct = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    register_factor(name, desc, buff_type, pct)

elif sys.argv[1] == '--list':
    wl = load_whitelist()
    print(json.dumps(wl, ensure_ascii=False, indent=2))

else:
    name = sys.argv[1]
    result = validate_factor(name)
    if result:
        print(json.dumps({name: result}, ensure_ascii=False, indent=2))
    else:
        print(f'❌ 因子 "{name}" 不在白名单中')
        sys.exit(1)
