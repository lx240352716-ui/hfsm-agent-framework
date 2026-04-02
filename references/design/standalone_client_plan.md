# 独立客户端方案 — 游戏策划 AI 工作流

> 状态：📌 待启动 | 记录日期：2026-03-10

## 目标

将当前 Claude Desktop 绑定的 game-planning-workflow skill 封装为独立本地应用，支持：
- 用户自配 Excel 路径
- 用户自配 API Key + 模型选择（Claude / GPT / DeepSeek / 本地）
- 不绑定任何特定 AI 平台

## 架构

```
前端 (Tauri/Electron)
├── 配置面板（路径、API、模型）
├── 对话窗口
├── 状态机可视化
└── 记忆面板

后端 (Python)
├── 状态机引擎（S1~S9）
├── LLM Adapter（OpenAI 兼容格式统一接口）
├── Prompt 管理（6角色 md → system prompt）
├── Excel 工具层（copy_row / reorder_insert → function calling）
└── 记忆管理器（读/写/去重判定）
```

## 技术选型

| 模块 | 推荐 | 原因 |
|---|---|---|
| 前端 | Tauri | 打包小(~5MB)、性能好 |
| 后端 | Python | COM Excel 写入 + SQLite 读取 |
| LLM | OpenAI 兼容格式 | Claude/GPT/DeepSeek 都支持 |
| 状态 | JSON 文件 | 中断可恢复 |

## MVP 路线

1. Python CLI + config.yaml（2-3天）
2. 加 Tauri UI 壳（3-5天）
3. 状态机可视化 + 记忆面板（5-7天）

## 关键挑战

1. Function Calling 适配：Excel 操作注册为工具
2. 上下文窗口：大表分块处理
3. Prompt 迁移：适配不同模型的 system prompt 格式
