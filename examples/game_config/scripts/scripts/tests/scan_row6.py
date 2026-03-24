# -*- coding: utf-8 -*-
"""扫描所有读 Row6 / 字段映射的代码"""
import os, re
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = BASE
KEYWORDS = [
    'cn_to_en_map',
    'build_header_map', 
    'read_headers',
    '_read_headers',
    'english=True',
    'OFFSET 3',
    'OFFSET 2',
    'Row6',
    'Row 6',
    'row6',
    'english=True',
    'get_columns.*english',
]

results = {}

for dirpath, _, filenames in os.walk(ROOT):
    for f in filenames:
        if not f.endswith('.py'):
            continue
        filepath = os.path.join(dirpath, f)
        rel = os.path.relpath(filepath, ROOT)
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
            lines = fh.readlines()
        
        for i, line in enumerate(lines, 1):
            for kw in KEYWORDS:
                if re.search(kw, line, re.IGNORECASE):
                    if rel not in results:
                        results[rel] = []
                    results[rel].append({
                        'line': i,
                        'keyword': kw,
                        'content': line.strip()[:100]
                    })
                    break  # 每行匹配一个就够

print("=" * 70)
print("所有读 Row6 / 字段映射相关代码")
print("=" * 70)

for filepath, matches in sorted(results.items()):
    print(f"\n📄 {filepath}")
    for m in matches:
        print(f"  L{m['line']:>4}  [{m['keyword']:<20}]  {m['content']}")

print(f"\n共 {len(results)} 个文件, {sum(len(v) for v in results.values())} 处匹配")
