# 🚀 新人快速上手指南

> 从零开始，10 分钟搭好你的项目。

---

## 第一步：创建项目目录

在你的电脑上新建一个项目文件夹，比如 `D:\my_game`：

```
D:\my_game\
├── excel\          ← 你的 Excel 配表放这里
└── references\     ← 框架代码放这里（下一步 clone）
```

```powershell
mkdir D:\my_game
mkdir D:\my_game\excel
```

---

## 第二步：下载框架

```powershell
cd D:\my_game
git clone https://github.com/lx240352716-ui/hfsm-agent-framework.git references
```

> 这会把框架代码下载到 `D:\my_game\references\` 目录。

---

## 第三步：放入你的 Excel 文件

把你项目的 Excel 配置表复制到 `excel\` 目录下：

```
D:\my_game\excel\
├── fight\              ← 按功能模块分文件夹（可选）
│   ├── FightBuff.xlsx
│   └── Skill.xlsx
├── recruit\
│   └── Recruit.xlsx
└── Item.xlsx           ← 也可以直接放根目录
```

> **规则**：只要是 `.xlsx` 就行，子目录层级随意，脚本会递归扫描。

---

## 第四步：配置环境变量

```powershell
cd D:\my_game\references
copy .env.example .env
```

用记事本打开 `.env`，把 `WORKSPACE_DIR` 改成你的项目根目录：

```ini
WORKSPACE_DIR=D:\my_game
```

---

## 第五步：一键初始化

```powershell
cd D:\my_game\references
python scripts\tools\init_project.py
```

你会看到：

```
═══ Step 1: 检查环境配置 ═══
  ✅ WORKSPACE_DIR = D:\my_game

═══ Step 2: 检查 Excel 目录 ═══
  ✅ 找到 XX 个 Excel 文件

═══ Step 3: 生成表注册表 ═══
  ✅ table_registry.json 生成成功

═══ Step 4: 生成表目录文档 ═══
  ⚠️ SQLite 数据库不存在（首次正常，后面会生成）

═══ Step 5: 生成 Agent 知识模板 ═══
  ✅ 生成 7 个知识模板
```

> **✅ 到这里，框架骨架就搭好了！**

---

## 第六步：填写知识库（核心步骤）

打开 `agents\` 目录，每个 Agent 的 `knowledge\` 文件夹里有模板 `.md` 文件。  
用你自己项目的规则去填它们：

| 文件 | 你要填什么 |
|------|-----------|
| `coordinator_memory/knowledge/coordinator_rules.md` | 你们项目的评审标准、需求分类规则 |
| `numerical_memory/knowledge/numerical_rules.md` | 数值计算公式、取值范围、填写规范 |
| `executor_memory/knowledge/executor_rules.md` | Excel 行对齐规则、字段默认值 |
| `qa_memory/knowledge/qa_rules.md` | 校验规则、哪些字段绝对不能错 |
| `combat_memory/knowledge/combat_rules.md` | 战斗系统机制（如果有的话） |

> 💡 每个文件里都有注释提示你该写什么格式。先填一点就能跑，后面边用边补。

---

## 第七步：启动

```powershell
cd D:\my_game\references
python scripts\core\hfsm_bootstrap.py
```

或者在 AI 对话里用 `/design` 命令启动状态机。

---

## 目录结构全貌

完成以上步骤后，你的项目长这样：

```
D:\my_game\
├── excel\                        ← 你的 Excel 配表
│   └── (你的 .xlsx 文件)
└── references\                   ← 框架（从 GitHub clone）
    ├── .env                      ← 你的环境配置 ✏️
    ├── agents\                   ← Agent 知识库 ✏️
    │   ├── coordinator_memory\   ← 主策划
    │   ├── numerical_memory\     ← 数值策划
    │   ├── executor_memory\      ← 执行策划
    │   ├── qa_memory\            ← QA
    │   └── combat_memory\        ← 战斗策划
    ├── scripts\
    │   ├── core\                 ← 引擎（不用改）
    │   ├── configs\              ← 自动生成的配置
    │   └── tools\                ← 工具脚本
    ├── domains\                  ← 领域知识 ✏️
    └── design\                   ← 设计参考 ✏️
```

> ✏️ = 需要你填写的部分，其余都是框架自带不用动。

---

## 常见问题

**Q: `python` 命令找不到？**  
A: 确认安装了 Python 3.8+，并且加到了 PATH。

**Q: init_project.py 报 WORKSPACE_DIR 未设置？**  
A: 检查 `.env` 文件，确认 `WORKSPACE_DIR=` 这行没有 `#` 注释符号。

**Q: 想更新框架代码？**  
A: `cd references && git pull origin master`
