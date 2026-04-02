# -*- coding: utf-8 -*-
"""
项目初始化脚本 — /init workflow 调用此脚本。

功能：
  1. 扫描 excel/ → 生成 table_registry.json
  2. 建 SQLite 索引 → table_index.db
  3. 学习词表 → table_vocabulary.json
  4. 创建 Agent data/ 目录
  5. 基础验证
"""

import os
import sys
import time
import json

# 路径设置
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
sys.path.insert(0, CORE_DIR)

from constants import BASE_DIR, EXCEL_DIR, REFERENCES_DIR, AGENTS_DIR, CONFIGS_DIR, DB_PATH


def step(n, total, msg):
    print(f"\n[{n}/{total}] {msg}")
    print("-" * 50)


def main():
    total_steps = 5
    t0 = time.time()

    print("=" * 60)
    print("  🚀 项目初始化")
    print("=" * 60)
    print(f"  项目根目录: {BASE_DIR}")
    print(f"  Excel 目录: {EXCEL_DIR}")

    # ── Step 1: 检查 Excel 目录 ──
    step(1, total_steps, "检查 Excel 目录")
    if not os.path.exists(EXCEL_DIR):
        os.makedirs(EXCEL_DIR, exist_ok=True)
        print(f"  ⚠️ excel/ 目录不存在，已创建。请放入 xlsx 文件后重新运行。")
        return

    xlsx_files = []
    for root, dirs, files in os.walk(EXCEL_DIR):
        for f in files:
            if f.endswith('.xlsx') and not f.startswith('~$'):
                xlsx_files.append(os.path.join(root, f))
    
    if not xlsx_files:
        print(f"  ⚠️ excel/ 目录为空，请放入 xlsx 文件后重新运行。")
        return
    
    print(f"  ✅ 发现 {len(xlsx_files)} 个 xlsx 文件")

    # ── Step 2: 生成 table_registry.json ──
    step(2, total_steps, "生成表注册表 (table_registry.json)")
    registry_path = os.path.join(CONFIGS_DIR, 'table_registry.json')
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    
    registry = {}
    for xlsx_path in xlsx_files:
        basename = os.path.splitext(os.path.basename(xlsx_path))[0]
        rel_path = os.path.relpath(xlsx_path, EXCEL_DIR)
        registry[basename] = rel_path
    
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ 注册 {len(registry)} 张表 → {os.path.relpath(registry_path, BASE_DIR)}")

    # ── Step 3: 建 SQLite 索引 ──
    step(3, total_steps, "建 SQLite 索引 (table_index.db)")
    
    from table_reader import refresh_index
    t_idx = time.time()
    # refresh_index 需要逐表调用: refresh_index(xlsx_path, table_name, header_row=1)
    # 只索引 >1MB 的大表（小表直接读更快）
    indexed, skipped = 0, 0
    for tbl_name, rel_path in registry.items():
        xlsx_path = os.path.join(EXCEL_DIR, rel_path)
        if not os.path.exists(xlsx_path):
            continue
        size_mb = os.path.getsize(xlsx_path) / (1024 * 1024)
        if size_mb > 1.0:
            try:
                refresh_index(xlsx_path, tbl_name, header_row=1)
                indexed += 1
            except Exception as e:
                print(f"  ⚠️ {tbl_name} 索引失败: {e}")
        else:
            skipped += 1
    idx_time = time.time() - t_idx
    print(f"  ✅ 索引完成: 已索引 {indexed} 张大表, 跳过 {skipped} 张小表, 耗时 {idx_time:.1f}s")

    # ── Step 4: 学习词表 ──
    step(4, total_steps, "学习词表 (table_vocabulary.json)")
    
    from table_reader import detect_project_vocabulary
    t_vocab = time.time()
    vocab = detect_project_vocabulary()
    vocab_time = time.time() - t_vocab
    
    if vocab:
        print(f"  ✅ 词表学习完成: {len(vocab)} 个元数据关键词, 耗时 {vocab_time:.1f}s")
    else:
        print(f"  ⚠️ 词表学习无结果（可能表结构特殊）")

    # ── Step 5: 创建 Agent data/ 目录 + 验证 ──
    step(5, total_steps, "创建目录 + 基础验证")
    
    agents = ['coordinator_memory', 'combat_memory', 'numerical_memory', 'executor_memory', 'qa_memory']
    for agent in agents:
        data_dir = os.path.join(AGENTS_DIR, agent, 'data')
        os.makedirs(data_dir, exist_ok=True)
    print(f"  ✅ {len(agents)} 个 Agent data/ 目录已创建")
    
    # 基础验证
    from table_reader import get_columns, query_db
    test_table = list(registry.keys())[0] if registry else None
    if test_table:
        try:
            cols = get_columns(test_table)
            cn_count = len(cols.get('cn', []) or [])
            en_count = len(cols.get('en', []) or [])
            print(f"  ✅ get_columns('{test_table}'): cn={cn_count} 列, en={en_count} 列")
        except Exception as e:
            print(f"  ⚠️ get_columns('{test_table}') 失败: {e}")
        
        try:
            rows = query_db(f"SELECT COUNT(*) as cnt FROM [{test_table}]")
            cnt = rows[0]['cnt'] if rows else '?'
            print(f"  ✅ query_db('{test_table}'): {cnt} 行")
        except Exception as e:
            print(f"  ⚠️ query_db('{test_table}') 失败: {e}")
    
    # ── 总结 ──
    total_time = time.time() - t0
    print("\n" + "=" * 60)
    print(f"  🎉 初始化完成！耗时 {total_time:.1f}s")
    print("=" * 60)
    print(f"\n  📋 表注册表: {len(registry)} 张表")
    print(f"  🗃️ SQLite 索引: {os.path.relpath(DB_PATH, BASE_DIR)}")
    print(f"  📖 词表: {os.path.relpath(os.path.join(CONFIGS_DIR, 'table_vocabulary.json'), BASE_DIR)}")
    print(f"\n  下一步:")
    print(f"    1. 填写 agents/*/knowledge/ 下的知识库文件")
    print(f"    2. 用 /design 启动策划工作流")
    print(f"    3. 用 /lookup 查表, /consult 咨询")


if __name__ == "__main__":
    main()
