# 知识检索与沉淀系统 — 设计方案

> 日期: 2026-04-08 | 对应 TODO: `todo_architecture.md` → "RAG 知识检索"

---

## 一、问题背景

### 现状

项目 `knowledge/` 下有两类知识：

| 类型 | 位置 | 数量 | 状态 |
|------|------|------|------|
| 人工 MD 知识 | `knowledge/*.md` | 17 个 | ✅ AI 可用（prompt_builder 注入） |
| 策划文档 | `knowledge/gamedocs/*.docx` | 18 个 | ❌ AI 无法使用 |
| 配表 Excel | `knowledge/gamedata/*.xlsx` | 285+ 个 | ✅ 可通过 table_reader 查询 |

### 核心痛点

**18 个策划文档（docx）中的知识无法被 AI Agent 利用。**

例如"神秘商店"的限购规则、"装备异化"的配表逻辑——这些信息只存在于 docx 中，
AI 做 `/design` 时查不到，全靠用户人工告知。

---

## 二、我们考虑过的方案

### 方案 A：全量 RAG（RAGFlow / LlamaIndex + ChromaDB）

```
所有文档 → 切片 → Embedding 向量化 → 向量数据库
查询时 → 问题向量化 → Top-K 召回 → 给 LLM
```

**调研结果**：

| 框架 | ⭐ | 结论 |
|------|---|------|
| RAGFlow | 70k | 文档解析最强（DeepDoc），但必须 Docker + ES + MySQL + Redis，太重 |
| LlamaIndex | 46k | 轻量 pip 安装，但引入新框架 = 新学习成本 |
| DeerFlow | 15k | 超级 Agent 运行时，与 HFSM 架构重叠 |

**Pass 原因**：项目只有 18 个 docx，不到 100MB 文本，全量 RAG 像"用大炮打蚊子"。
而且向量检索会"截断上下文"，不如 LLM 直接读完整段落理解更准确。

---

### 方案 B：让 LLM 直接读文档

```
docx → 转纯文本 → 全部塞进 LLM 上下文 → LLM 理解
```

**Pass 原因**：
- 18 个 docx 纯文本约 100-250 万 token，GLM-4 上下文窗口 128k，超出 10 倍
- 即使每次只读 1 个文件，大文件也可能超限
- 每次查询都全量发送 = 高成本 + 高延迟

---

### 方案 C：CC 混合方案 ← **我们选择的方向**

研究了 Claude Code 的做法后提出：

```
核心知识 → 人工/AI 提炼的 *.md（优先读取，零延迟）
边缘知识 → 搜索工具按需查找（需要时再读）
学习闭环 → 新文档 → 提炼为 MD → 自动成为核心知识
```

**为什么 CC 的方式适合我们**：
1. 我们已有 17 个 MD 知识文件 = CC 的 `CLAUDE.md`
2. 我们已有 `prompt_builder.py` 注入知识 = CC 自动加载 CLAUDE.md
3. 我们的文档数量有限（18 个），一次性提炼后就不需要实时 RAG
4. 提炼后的 MD 质量远高于 RAG 切片，AI 理解更准确

---

## 三、CC 混合方案详设

### 理解文档的两种策略

通过调研 CC、RAGFlow、LlamaIndex、DeerFlow 的做法，发现所有系统理解文档的方式殊途同归：

| 策略 | 做法 | 谁用 | 适合 |
|------|------|------|------|
| **直接读** | 文本塞进 LLM 上下文 | CC、DeerFlow | 小/中文件，需要完整理解 |
| **先检索再读** | 切片→向量→Top-K→塞 | RAGFlow、LlamaIndex | 大量文件，只需局部信息 |

**我们的选择**：对文档用"直接读"策略（一次性提炼），对提炼后的 MD 用"搜索"策略（日常查询）。

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    日常使用层                         │
│                                                     │
│  /design 或 /consult 时 AI 需要知识                   │
│         ↓                                           │
│  L1: grep knowledge/*.md ── 直接命中 ──→ 注入 prompt │
│         ↓ 未命中                                     │
│  L2: FTS5 搜索 gamedocs chunk ── 命中 ──→ 注入       │
│                                                     │
├─────────────────────────────────────────────────────┤
│                    学习沉淀层                         │
│                                                     │
│  /learn 工作流（用户主动触发）                         │
│                                                     │
│  docx ──→ Docling 转 MD ──→ LLM 分章节提炼           │
│                         ──→ 用户确认                  │
│                         ──→ 写入 knowledge/*.md       │
│                                                     │
│  提炼后的文档自动成为 L1 优先知识                      │
└─────────────────────────────────────────────────────┘
```

### `/learn` 工作流设计

参考 `/design` 的状态机，`/learn` 对应为：

| 步骤 | `/design` 对应 | `/learn` 做什么 |
|------|---------------|----------------|
| **parse** | L0 理解需求 | Docling 解析 docx → markdown 全文 |
| **extract** | L1 设计方案 | LLM 按章节提炼关键知识（规则、表关系、配表模版） |
| **confirm** | 用户确认设计 | 用户 review 提炼结果 |
| **write** | L2 填表 | 追加到对应 `knowledge/*.md` 或创建新文件 |

```
用户: /learn 神秘商店.docx

→ [parse]   Docling 转为 markdown（本地处理，不调 LLM）
→ [extract] LLM 读全文，按模板提炼为知识条目
→ [confirm] 显示提炼结果，用户确认/修改
→ [write]   写入 knowledge/shop.md（或追加到已有文件）
```

### 需要的组件清单

| 组件 | 职责 | 造/用现成 |
|------|------|---------|
| **Docling** | docx/xlsx → markdown | 开源库 `pip install docling` |
| **FTS5 索引** | 全文关键词搜索 | 已建 (`knowledge_index.py`) |
| **llm_client** | 提炼知识 | 已有 |
| `/learn` 工作流 | 状态机 parse→extract→confirm→write | 需新建 |
| 提炼 prompt 模版 | 控制输出格式 | 需新建 |
| `knowledge_cli.py` | CLI 入口 | 已建（需扩展 `learn` 命令） |

> **不需要**：ChromaDB、Embedding 模型、Docker、任何外部服务

### 提炼 prompt 模版（核心）

LLM 提炼时的指令，控制输出与现有 `*.md` 风格一致：

```markdown
你是游戏策划知识整理员。请将以下文档内容提炼为结构化知识条目。

输出格式要求：
1. 用 ## 标题分系统/模块
2. 用表格列出：涉及的配表名、关键字段、配置规则
3. 用要点列出：业务规则、限制条件、特殊逻辑
4. 忽略：修改记录、目录页、纯图片描述

参考现有知识文件风格：
（附 skill.md 或 buff.md 片段作为 few-shot）
```

---

## 四、与纯 RAG 的对比

| 维度 | 纯 RAG | CC 混合方案 |
|------|--------|-----------|
| **部署** | ChromaDB + Embedding | 零额外服务 |
| **日常查询成本** | 每次调 Embedding API | grep 文件，零成本 |
| **知识质量** | 切片碎片，可能丢上下文 | 人工/AI 提炼的完整知识 |
| **新文档处理** | 自动切片索引 | 需跑 `/learn` 提炼一次 |
| **维护成本** | 低（自动） | 中（需 review 提炼结果） |
| **准确度** | 依赖切片+向量质量 | 高（MD 是经确认的知识） |

---

## 五、待讨论

1. **Docling vs python-docx**：Docling（IBM 30k⭐）输出质量更高但多一个依赖；python-docx 已在用但需手工处理表格。选哪个？

2. **提炼粒度**：一个 docx 对应一个 MD？还是按知识域合并？（如"神秘商店.docx" → 追加到已有的 `knowledge/scene.md`？还是新建 `shop.md`？）

3. **大文档处理**：`个性形象.docx`（4.9MB）超过 LLM 上下文怎么办？分章节多次提炼？

4. **FTS5 索引保留还是去掉？** 如果所有 docx 都提炼为 MD 了，FTS5 搜原始 docx 的价值还大吗？
