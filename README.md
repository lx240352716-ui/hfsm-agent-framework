# GameDesign Skills — 游戏策划工具箱

> 用自然语言配表的 AI 策划助手

---

## 快速开始

### 1. 下载

```bash
git clone https://github.com/lx240352716-ui/gamedesign-skills.git
```

### 2. 放入游戏数据

把你的配置表 Excel 放到 `knowledge/gamedata/` 目录下：

```
knowledge/
├── gamedata/          ← 配置表 Excel 放这里
│   ├── Hero.xlsx
│   ├── _Buff.xlsx
│   ├── FightBuff.xlsx
│   └── ...
└── gamedocs/          ← 策划参考文档（可选）
    └── 数值总表.xlsx
```

### 3. 初始化

在 Claude Code（或类似 IDE）中打开项目目录，运行：

```
/init
```

初始化脚本会自动完成：
- ✅ 检测并安装 Python 依赖
- ✅ 扫描 Excel 文件 → 生成表注册表
- ✅ 建立 SQLite 索引
- ✅ 配置 `.env`（首次需要填写 API Key）

---

## 使用命令

在 AI IDE 中输入斜杠命令即可使用：

| 命令 | 用途 | 使用示例 |
|------|------|----------|
| `/design` | 完整配表流程 | "新增一套 UR 装备" |
| `/quick` | 快速修改 | "把 heroId=5046 的攻击改成 1200" |
| `/lookup` | 查表查数据 | "查 FightBuff 30241 的配置" |
| `/consult` | 设计咨询 | "timing=29 是什么意思" |
| `/status` | 任务状态 | 查看当前进度 |
| `/init` | 初始化 | 首次使用自动安装 |

---

## 目录结构

```
gamedesign-skills/
│
├── knowledge/           ← 📥 输入：你的游戏数据
│   ├── gamedata/        配置表 Excel（1000+ 张）
│   ├── gamedocs/        策划参考文档
│   └── *.md             提炼的系统知识（速查表、表关系等）
│
├── output/              ← 📤 输出：AI 生成的结果
│   └── staging/         待确认的配表产物
│
├── references/          ← ⚙️ 引擎：AI 核心（一般不用动）
│   ├── agents/          5 个 AI 策划角色的记忆和工作流
│   └── scripts/         核心脚本（表读写、状态机、CLI 工具）
│
├── docs/                ← 📖 文档
├── .agents/workflows/   ← 🤖 斜杠命令定义
├── CLAUDE.md            ← AI 行为规则
└── .env                 ← API Key 配置
```

---

## 配置说明

编辑项目根目录下的 `.env` 文件：

| 变量 | 必填 | 说明 | 示例 |
|------|:----:|------|------|
| `DASHSCOPE_API_KEY` | ✅ | 通义千问 API Key | `sk-xxxxxxxx` |
| `LLM_MODEL` | | 模型名称 | `qwen-plus`（默认） |
| `LLM_BASE_URL` | | API 地址 | 默认通义千问 |
| `LLM_TEMPERATURE` | | 温度参数 | `0.7`（默认） |
| `LLM_MAX_TOKENS` | | 最大输出 | `4096`（默认） |

> 💡 也支持 DeepSeek、OpenAI、本地 Ollama — 改 `LLM_BASE_URL` 即可。

---

## AI 策划角色

系统内置 5 个 AI 角色，自动协作完成配表：

| 角色 | 职责 |
|------|------|
| **主策划** | 需求理解 → 模块拆分 → 任务分配 → 最终回顾 |
| **战斗策划** | Buff / Skill / FightBuff 系统设计 |
| **数值策划** | 因子计算、数值平衡、参考行定位 |
| **执行策划** | 查表定位、数据填写、Excel 输出 |
| **QA 策划** | 交叉校验、ID 连续性检查、异常检测 |

---

## 前置条件

- **Python 3.10+**（[下载](https://www.python.org/downloads/)）
- **Claude Code** 或类似 AI IDE
- **游戏配置表 Excel 文件**

> ⚠️ 本工具目前仅支持 **Windows**（因为使用 COM Excel 操作写入）。

---

<p align="center">让 AI 填表，你只管做好玩的游戏。</p>
