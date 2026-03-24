# 示例：游戏配表自动化

用自然语言描述需求，AI 自动生成可导入的 Excel 配置表。

## 架构

```
用户需求（自然语言）
       │
       ▼
  L0 主策划 ──────── 理解需求、拆分模块、分配任务
       │
  ┌────┴────┐
  ▼         ▼
L1 战斗   L1 数值 ── 领域推理、定位目标表、生成填写方案
  └────┬────┘
       ▼
  L2 执行策划 ────── 读 Excel、分配 ID、填写数据、写入文件
       │
       ▼
  L3 QA ──────────── 数据完整性检查、输出验证报告
       │
       ▼
  📦 可用的 Excel
```

## Agent 说明

| Agent | 目录 | 职责 |
|:------|:-----|:-----|
| 主策划 (L0) | `agents/coordinator_memory/` | 任务规划·分解·派发·评审 |
| 战斗策划 (L1) | `agents/combat_memory/` | 战斗机制分析，Buff/技能因子推理 |
| 数值策划 (L1) | `agents/numerical_memory/` | 定位目标表，生成填写方案 |
| 执行策划 (L2) | `agents/executor_memory/` | 读写 Excel，分配 ID，填写数据 |
| QA (L3) | `agents/qa_memory/` | 数据完整性校验，输出验证报告 |

## 运行

1. 配置 Excel 数据目录
2. 运行 `python scripts/tools/rebuild_registry.py` 建立 SQLite 索引
3. 通过 IDE AI 助手调用 `/design` 启动工作流

## 注意

本示例中的 `agents/` 和 `scripts/` 是完整的业务实现。如果你要做自己的场景，参考这里的结构，替换成你自己的 Agent、Hook 和知识文件。
