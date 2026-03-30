# -*- coding: utf-8 -*-
"""战斗策划交接数据校验 — 战斗业务层特有的字段完整性检查"""

import os
import sys

SCRIPTS_DIR = os.path.join(REFERENCES_DIR, 'scripts')
sys.path.insert(0, os.path.join(SCRIPTS_DIR, 'core'))
sys.path.insert(0, os.path.join(SCRIPTS_DIR, 'workflow'))

from constants import REQUIRED_FIELDS
from handoff import load_handoff
from whitelist import load_whitelist


def validate_combat_handoff(task_name):
    """校验战斗策划交接数据的设计字段完整性（执行层 Step 1）

    Returns:
        list: 错误列表，空=全部通过
    """
    data = load_handoff(task_name, 'combat')
    if data is None:
        return ['交接文件不存在']

    errors = []
    tables = data.get('tables', {})

    for table_name, required_fields in REQUIRED_FIELDS.items():
        rows = tables.get(table_name, [])
        for i, row in enumerate(rows):
            missing = [f for f in required_fields if f not in row]
            if missing:
                errors.append(f'{table_name} 第{i+1}行缺少设计字段: {missing}')

    # 校验因子在白名单中
    wl = load_whitelist()
    for row in tables.get('_Buff', []):
        factor = row.get('perfactor', '')
        if factor and factor != '0' and factor not in wl:
            errors.append(f'因子 "{factor}" 不在白名单中，需走开荒 SQL 验证')

    if errors:
        print(f'  [VALIDATE FAIL] {len(errors)} 个设计字段错误')
        for e in errors:
            print(f'    ❌ {e}')
    else:
        print(f'  [VALIDATE OK] 战斗策划交接数据设计字段完整')

    return errors
