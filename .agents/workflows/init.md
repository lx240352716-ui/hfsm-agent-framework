---
description: "初始化项目 — 扫描配表、建索引、学词表，让项目可以工作"
---

# /init — 项目初始化

将裸仓库变成可工作的项目环境。适用于首次 clone 或配表目录更新后。

## 执行步骤

### Step 1: 检查环境

确认项目存在 `knowledge/gamedocs/` 目录且有文档文件：

// turbo

```shell
python -c "import os; d=os.path.join('knowledge', 'gamedata'); files=[f for root,_,fs in os.walk(d) for f in fs if f.endswith('.xlsx') and not f.startswith('~$')]; print(f'knowledge/gamedata/ 下有 {len(files)} 个 xlsx 文件')" 2>&1 || echo "[WARN] knowledge/gamedata/ 目录不存在或为空，请先放入 xlsx 配表文件"
```

如果 `knowledge/gamedata/` 不存在或为空，**停止并提示用户放入文件**。

### Step 2: 运行初始化脚本

// turbo

```shell
python references/scripts/cli/init_project.py
```

脚本会自动完成：

1. 扫描 `knowledge/gamedata/` -> 生成 `table_registry.json`
2. 建 SQLite 索引 -> `table_index.db`
3. 学习词表（中英字段映射）-> `table_vocabulary.json`
4. 创建 Agent `data/` 目录
5. 运行基础验证

### Step 2.3: 解析 gamedocs 生成缓存

// turbo

```shell
python references/scripts/cli/build_cache.py
```

扫描 `knowledge/gamedocs/` 下所有 docx/xlsx/md 文件，解析为 Markdown 并写入 `.cache/`。
如果文件已有缓存且未修改则自动跳过（增量模式）。

> 如果 `knowledge/gamedocs/` 为空，会提示并跳过此步骤。后续放入文档后单独执行即可。

### Step 2.4: 构建 CN-EN 映射

// turbo

```shell
python references/scripts/cli/build_cn_en_map.py
```

脚本从 `table_registry.json` 提取英文分组名。如果输出 `[ACTION]`，
说明需要翻译。**请根据输出的英文分组名列表，将每个翻译为中文游戏术语**，
按格式写入 `knowledge/wiki/cn_en_map.json`。

如果输出 `[OK]` 则映射已完整，无需操作。

### Step 2.5: 编译 Wiki 知识索引

// turbo

```shell
python references/scripts/core/wiki_compiler.py
```

脚本会扫描 `knowledge/gamedocs/.cache/` 生成：

- `knowledge/wiki/entities.md` — 配置表交叉引用
- `knowledge/wiki/concepts.md` — 概念跨文档索引
- `knowledge/wiki/index.md` — Agent 消费入口
- `knowledge/wiki/cn_en_map.json` — 中英映射
- `knowledge/wiki/lint_report.md` — 健康检查报告

> 如果 `knowledge/gamedocs/.cache/` 不存在（还未放入文档），会跳过 wiki 编译。后续放入文档并运行文档解析后，单独执行此步骤即可。

### Step 3: 报告结果

读取初始化脚本的输出，向用户报告：

- 扫描到多少张表
- 索引成功/失败数量
- 词表学习结果
- 是否有需要手动处理的问题

### Step 4: 引导下一步

告诉用户：

1. 填写 `agents/*/knowledge/` 下的知识库文件（如果是新项目）
2. 用 `/design` 启动策划工作流
3. 用 `/lookup` 查表数据
4. 用 `/consult` 咨询设计问题
