# -*- coding: utf-8 -*-
"""
HFSM 运行时数据清理工具
"""

from pathlib import Path
from ..config import Config

def purge_all_runtime_data():
    """
    清空所有 Agent 的 data 目录中的 json 文件，
    防止前序任务的状态残留污染新任务的执行上下文。
    """
    agents_config = Config.load_agents_config()
    for agent_name in agents_config.get('agents', {}).keys():
        paths = Config.agent_paths(agent_name)
        data_dir = Path(paths['data_dir'])
        if data_dir.exists() and data_dir.is_dir():
            for file in data_dir.glob('*.json'):
                try:
                    file.unlink()
                    print(f"[Purge] Deleted: {file}")
                except Exception as e:
                    print(f"[Purge Error] Failed to delete {file}: {e}")
