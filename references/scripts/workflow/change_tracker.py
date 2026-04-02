# -*- coding: utf-8 -*-
"""变更追踪 — 记录表变更并生成 CHANGES.md"""

import os
import sys
import json
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core'))
from file_ops import get_task_output_dir


class ChangeTracker:
    """追踪任务执行过程中的所有表变更，生成 CHANGES.md 主文档

    用法：
        tracker = ChangeTracker("UR红发装备")
        tracker.track("Equipment.xlsx", 15, "新增", 504701, {"suitId": 50470})
        tracker.save()               # 输出 change_log.json
        tracker.generate_report()    # 输出 CHANGES.md
    """

    def __init__(self, task_name, task_desc=None, design_todos=None):
        self.task_name = task_name
        self.task_desc = task_desc
        self.design_todos = design_todos or []
        self.changes = []
        self._index = {}
        self.tables_involved = set()

    def track(self, table_name, row_num, action, record_id, details=None):
        """记录一次变更（同table+id后来的覆盖先前的）"""
        entry = {
            "table": table_name, "row": row_num, "action": action,
            "id": record_id, "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        key = (table_name, str(record_id))
        if key in self._index:
            self.changes[self._index[key]] = entry
            print(f"  [TRACK] {action} {table_name} id={record_id} (覆盖)")
        else:
            self._index[key] = len(self.changes)
            self.changes.append(entry)
            print(f"  [TRACK] {action} {table_name} id={record_id}")
        self.tables_involved.add(table_name)

    def save(self):
        """保存变更日志为 JSON"""
        task_dir = get_task_output_dir(self.task_name)
        log_path = os.path.join(task_dir, "change_log.json")
        log_data = {
            "task": self.task_name,
            "timestamp": datetime.now().isoformat(),
            "total_changes": len(self.changes),
            "tables_involved": sorted(self.tables_involved),
            "changes": self.changes
        }
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        print(f"  [SAVE] change_log.json ({len(self.changes)} 条变更)")
        return log_path

    def generate_report(self):
        """从变更日志生成 CHANGES.md 主文档"""
        task_dir = get_task_output_dir(self.task_name)
        report_path = os.path.join(task_dir, "CHANGES.md")

        by_table = {}
        for c in self.changes:
            t = c["table"]
            if t not in by_table:
                by_table[t] = []
            by_table[t].append(c)

        lines = []
        lines.append(f"# {self.task_name} — 修改清单\n")
        lines.append(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"涉及表: {len(by_table)} 张")
        lines.append(f"总变更: {len(self.changes)} 条\n")

        if self.task_desc:
            lines.append(f"## 任务描述\n")
            lines.append(f"> {self.task_desc}\n")

        if self.design_todos:
            lines.append(f"## 设计拆解\n")
            for item in self.design_todos:
                st = item.get('status', '⏳')
                sub = item.get('subtask', '')
                mark = '[x]' if st == '✅' else '[ ]'
                lines.append(f"- {mark} {sub}  {st}")
            lines.append("")

        lines.append("## 汇总\n")
        lines.append("| # | 表名 | 新增 | 修改 | 删除 |")
        lines.append("|---|---|---|---|---|")
        for i, (table, rows) in enumerate(by_table.items(), 1):
            add = sum(1 for r in rows if r["action"] == "新增")
            mod = sum(1 for r in rows if r["action"] == "修改")
            delete = sum(1 for r in rows if r["action"] == "删除")
            lines.append(f"| {i} | {table} | {add} | {mod} | {delete} |")
        lines.append("")

        for table, rows in by_table.items():
            lines.append(f"## {table}\n")
            lines.append("| 操作 | 行号 | ID | 关键变更 |")
            lines.append("|---|---|---|---|")
            for r in rows:
                detail_str = ", ".join(f"{k}={v}" for k, v in r["details"].items())
                if len(detail_str) > 60:
                    detail_str = detail_str[:57] + "..."
                lines.append(f"| {r['action']} | {r['row']} | {r['id']} | {detail_str} |")
            lines.append("")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"  [REPORT] CHANGES.md 已生成 ({len(self.changes)} 条变更, {len(by_table)} 张表)")
        return report_path
