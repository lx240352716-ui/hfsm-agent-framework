# -*- coding: utf-8 -*-
"""locate 环节：查 3 个模块的真实表字段 + 过滤"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts', 'core'))
from table_reader import get_columns, query_db

tables = {
    '道具注册': ('Item', '%礼包%'),
    '掉落配置': ('_DropGroup', None),
    '商城上架': ('_ShopItem', None),
}

for module, (table, like_pattern) in tables.items():
    print(f"\n{'='*60}")
    print(f"模块: {module} → 表: {table}")
    print(f"{'='*60}")

    # 1. 拿字段
    try:
        cols_cn = get_columns(table)
        cols_en = get_columns(table, english=True)
        # 过滤 EmptyKey
        pairs = [(cn, en) for cn, en in zip(cols_cn, cols_en) if not cn.startswith('EmptyKey')]
        print(f"\n字段 ({len(pairs)} 列):")
        for cn, en in pairs:
            print(f"  {cn:30s} | {en}")
    except Exception as e:
        print(f"  字段获取失败: {e}")
        continue

    # 2. 查参考数据做过滤
    try:
        if like_pattern:
            rows = query_db(f"SELECT * FROM [{table}] WHERE [名字] LIKE ?", (like_pattern,))
        else:
            rows = query_db(f"SELECT * FROM [{table}] LIMIT 10")

        if rows and len(rows) >= 3:
            fixed, empty, vary = [], [], []
            for cn, en in pairs:
                vals = [str(r.get(cn, '')) for r in rows[:5]]
                unique = set(vals)
                if len(unique) == 1:
                    if vals[0] in ('', 'None', '0', 'nan', 'none'):
                        empty.append(cn)
                    else:
                        fixed.append((cn, en, vals[0]))
                else:
                    vary.append((cn, en, vals[:3]))

            print(f"\n── fixed (自动填) ──")
            for cn, en, v in fixed:
                print(f"  {cn:25s} = {v}")
            print(f"\n── empty (不展示, {len(empty)}个) ──")
            print(f"  {empty}")
            print(f"\n── input (需用户填, {len(vary)}个) ──")
            for cn, en, vals in vary:
                print(f"  {cn:25s} ({en}) 示例: {vals}")
        else:
            print(f"\n  参考数据不足 ({len(rows) if rows else 0} 行)，展示全部字段")
    except Exception as e:
        print(f"  参考数据查询失败: {e}")
