# -*- coding: utf-8 -*-
"""文件安全操作 — 输出目录管理"""

import os
from constants import OUTPUT_DIR


def get_task_output_dir(task_name):
    """获取当前任务的输出目录，不存在则创建"""
    task_dir = os.path.join(OUTPUT_DIR, task_name)
    os.makedirs(task_dir, exist_ok=True)
    return task_dir
