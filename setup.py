# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="hfsm-agent-framework",
    version="0.1.0",
    description="分层状态机 + Hook 驱动的多 Agent 框架",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "hfsm=cli.hfsm_cli:main",
        ],
    },
)
