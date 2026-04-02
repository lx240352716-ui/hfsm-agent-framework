---
description: "查看当前 HFSM 任务的进度和状态"
allowed-tools: ["Bash", "FileRead"]
whenToUse: "用户问做到哪了、当前进度、任务状态"
---

# 查看任务状态

## 步骤

1. 检查状态文件是否存在：

// turbo
```shell
python scripts/core/hfsm_bootstrap.py
```

2. 根据输出判断：

**如果有进行中的任务**，用表格总结：
- 当前层级（coordinator / design / executor / pipeline）
- 当前 Agent（主策划 / 战斗策划 / 数值策划 / 执行策划 / QA）
- 当前步骤
- 需要加载的知识库文件

**如果没有任务**（`scripts/output/task_state.json` 不存在），告诉用户：
> 当前没有进行中的任务。使用 `/design` 开始新任务。
