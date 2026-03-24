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


class Config:
    """框架全局配置"""

    _project_dir = None

    @classmethod
    def init(cls, project_dir=None):
        """初始化项目路径

        Args:
            project_dir: 项目根目录。默认读 HFSM_PROJECT_DIR 环境变量，都没有则用 cwd。
        """
        cls._project_dir = (
            project_dir
            or os.environ.get('HFSM_PROJECT_DIR')
            or os.getcwd()
        )

    @classmethod
    def project_dir(cls):
        if cls._project_dir is None:
            cls.init()
        return cls._project_dir

    @classmethod
    def agents_dir(cls):
        return os.path.join(cls.project_dir(), 'agents')

    @classmethod
    def output_dir(cls):
        return os.path.join(cls.project_dir(), 'output')

    @classmethod
    def agent_paths(cls, agent_name):
        """返回某个 Agent 的标准子目录路径。

        Returns:
            dict: {agent_dir, knowledge_dir, data_dir, process_dir}
        """
        agent_dir = os.path.join(cls.agents_dir(), agent_name)
        return {
            'agent_dir': agent_dir,
            'knowledge_dir': os.path.join(agent_dir, 'knowledge'),
            'data_dir': os.path.join(agent_dir, 'data'),
            'process_dir': os.path.join(agent_dir, 'process'),
        }

    @classmethod
    def load_agents_config(cls, filepath=None):
        """加载 agents.json 配置

        Args:
            filepath: 配置文件路径。默认 {project_dir}/agents.json
        Returns:
            dict: agents 配置
        """
        if filepath is None:
            filepath = os.path.join(cls.project_dir(), 'agents.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
