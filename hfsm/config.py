# -*- coding: utf-8 -*-
"""
HFSM 框架配置管理

通过环境变量或配置文件设置项目路径，消除硬编码。

使用方式：
    # 方式 1：环境变量
    export HFSM_PROJECT_DIR=/path/to/project

    # 方式 2：代码设置
    from hfsm.config import Config
    Config.init("/path/to/project")

    # 方式 3：自动检测（当前目录）
    from hfsm.config import Config
    Config.init()  # 默认使用 os.getcwd()
"""

import os
import json
from pathlib import Path

class Config:
    """框架全局配置"""
    _project_root = None

    @classmethod
    def init(cls, project_dir=None):
        """初始化项目路径"""
        if not project_dir:
            project_dir = os.environ.get('HFSM_PROJECT_DIR') or os.getcwd()
        cls._project_root = Path(project_dir).resolve()

    @classmethod
    def get_root(cls) -> Path:
        if not cls._project_root:
            cls.init()
        return cls._project_root

    @classmethod
    def project_dir(cls):
        # 兼容老代码的字符串返回
        return str(cls.get_root())

    @classmethod
    def get_agent_dir(cls, agent_name: str) -> Path:
        """动态获取 Agent 目录: {root}/agents/{agent_name}"""
        return cls.get_root() / "agents" / agent_name

    @classmethod
    def get_agent_data_dir(cls, agent_name: str) -> Path:
        return cls.get_agent_dir(agent_name) / "data"

    @classmethod
    def agent_paths(cls, agent_name: str):
        """返回某个 Agent 的标准子目录路径字典（兼容旧格式）。"""
        agent_dir = cls.get_agent_dir(agent_name)
        return {
            'agent_dir': str(agent_dir),
            'knowledge_dir': str(agent_dir / 'knowledge'),
            'data_dir': str(agent_dir / 'data'),
            'process_dir': str(agent_dir / 'process'),
        }

    @classmethod
    def load_agents_config(cls, filepath=None) -> dict:
        """加载 agents.json 配置"""
        config_path = Path(filepath) if filepath else cls.get_root() / "agents.json"
        if not config_path.exists():
            return {}
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
