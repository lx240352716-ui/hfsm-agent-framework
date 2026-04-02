---
description: "初始化项目 — 扫描 Excel、建索引、学词表，让项目可以工作"
---

# /init — 项目初始化

将裸仓库变成可工作的项目环境。适用于首次 clone 或 excel 目录更新后。

## 执行步骤

### Step 1: 检查环境

确认项目根目录存在 `excel/` 目录且有 xlsx 文件：

// turbo
```shell
python -c "import os; d=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath('references/scripts/core/constants.py'))), 'excel'); files=[f for f in os.listdir(d) if f.endswith('.xlsx')]; print(f'excel/ 下有 {len(files)} 个 xlsx 文件')" 2>&1 || echo "❌ excel/ 目录不存在或为空，请先放入 Excel 配表文件"
```

如果 excel/ 不存在或为空，**停止并提示用户放入文件**。

### Step 2: 运行初始化脚本

// turbo
```shell
python references/scripts/tools/init_project.py
```

脚本会自动完成：
1. 📋 扫描 `excel/` → 生成 `table_registry.json`
2. 🗃️ 建 SQLite 索引 → `table_index.db`
3. 📖 学习词表（中英字段映射）→ `table_vocabulary.json`
4. 📁 创建 Agent `data/` 目录
5. ✅ 运行基础验证

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
