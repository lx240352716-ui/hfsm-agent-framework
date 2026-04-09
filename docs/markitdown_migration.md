# MarkItDown vs table_reader — 一比一函数对照

> MarkItDown xlsx 实现原理：`pd.read_excel(sheet_name=None)` → `to_html()` → HTML→Markdown

---

## table_reader.py 每个函数 vs MarkItDown

| # | 函数 | 行数 | 做什么 | MarkItDown 能替代？ | 原因 |
|---|------|------|--------|-------------------|------|
| 1 | `get_com_excel()` | 17 | 获取 COM Excel 单例 | ❌ | MarkItDown 只读不写，COM 是写入用的 |
| 2 | `close_com_excel()` | 9 | 关闭 COM | ❌ | 配套写入 |
| 3 | `open_workbook()` | 14 | COM 打开工作表 | ❌ | 配套写入 |
| 4 | `_get_conn()` | 31 | 获取 SQLite 连接 | ❌ | MarkItDown 无数据库 |
| 5 | `query_db()` | 19 | SQL 查询 `SELECT * FROM [_Buff] WHERE ...` | ❌ | MarkItDown 不能做条件查询 |
| 6 | `refresh_index()` | 25 | xlsx→SQLite 索引 | ❌ | MarkItDown 不建索引 |
| 7 | `_get_table_path()` | 15 | 表名→文件路径 | ❌ | 路径映射逻辑 |
| 8 | `_ensure_indexed()` | 22 | 自动确保索引存在 | ❌ | 配套索引 |
| 9 | `detect_project_vocabulary()` | 94 | 自动学习元数据关键词 | ❌ | MarkItDown 无此功能 |
| 10 | `_classify_row()` | 34 | 判断行类型(cn/en/type/data) | ❌ | MarkItDown 无此功能 |
| 11 | `detect_row_schema()` | 59 | 自动检测哪行是表头 | **⚠️ 部分替代** | MarkItDown 默认第一行为表头 |
| 12 | `get_columns()` | 92 | 获取字段元数据（中英名、类型、列号） | **⚠️ 部分替代** | MarkItDown 只输出表内容，不提取元数据结构 |
| 13 | `max_id()` | 28 | 查最大 ID | ❌ | 需要 SQL 聚合 |
| 14 | 辅助函数(5个) | ~50 | 缓存/正则/CJK判断 | ❌ | 内部工具 |

---

## 关键发现

### MarkItDown 的 xlsx 转换原理

```python
# MarkItDown 的 XlsxConverter 核心逻辑（简化）
sheets = pd.read_excel(file, sheet_name=None, engine='openpyxl')  # 读全部sheet
for name, df in sheets.items():
    html = df.to_html(index=False)    # DataFrame → HTML表格
    md = html_to_markdown(html)       # HTML → Markdown
    output += f"## {name}\n{md}\n"
```

**它做的事：文件 → 全部 sheet → markdown 表格文本**

### 你的 table_reader 做的事

```python
# 1. 建索引（把 xlsx 存到 SQLite）
refresh_index("gamedata/_Buff.xlsx", "_Buff")

# 2. 结构化查询（精确查某行某列）
rows = query_db("SELECT * FROM [_Buff] WHERE perfactor = ?", ('speed',))

# 3. 字段元数据（知道哪个字段是什么意思）
cols = get_columns("_Buff")  
# → {cn_en: {'攻击': 'attack', ...}, en_type: {'attack': 'int'}, col_map: {'attack': 3}}

# 4. 写入（COM Excel 操作源表）
wb, ws = open_workbook("_Buff")
ws.Cells(row, col).Value = new_value
```

---

## 真正的对比结论

| 操作 | MarkItDown | table_reader | 谁更适合 |
|------|-----------|--------------|---------|
| **"读懂这个表讲什么"** | ✅ 一行搞定 | ❌ 需要 SQL + 手动拼 | **MarkItDown** |
| **"查 _Buff 表里 perfactor=speed 的行"** | ❌ 不支持 | ✅ SQL 秒查 | **table_reader** |
| **"这个表有哪些字段，中文名是什么"** | ⚠️ 能看到但不结构化 | ✅ 返回 dict | **table_reader** |
| **"往 _Buff 表第 100 行写入数据"** | ❌ 只读 | ✅ COM Excel | **table_reader** |
| **"把 神秘商店.docx 转成 AI 能读的文本"** | ✅ 一行搞定 | ❌ 不支持 docx | **MarkItDown** |

---

## 所以该怎么改？

**不是"替换"，是"分工"：**

```
MarkItDown  →  "读懂"层：把任意文件变成 AI 能理解的 markdown
table_reader →  "操作"层：对配表做精确查询 + 写入

两者并存，各管各的。
```

### 但是！table_reader 里有一部分"读懂"的功能确实可以用 MarkItDown 替代：

| table_reader 中的"读懂"功能 | 现在怎么做 | 可以换成 |
|---------------------------|-----------|---------|
| `detect_row_schema()` — 检测哪行是中文名/英文名/类型 | 94行手写采样逻辑 | MarkItDown 转 markdown + LLM 理解 |
| `detect_project_vocabulary()` — 学习元数据关键词 | 94行自动词表 | 一次性用 MarkItDown 输出给 LLM 提炼 |
| `get_columns()` 的"理解"部分 — 字段含义 | 59行复杂解析 | MarkItDown 输出 + LLM 总结 |

**但这些函数同时被 28 个文件的"操作"场景调用，不能直接删掉。**

---

## 最终建议

| 改什么 | 怎么改 | 工时 |
|--------|--------|------|
| `doc_reader.py` | 用 MarkItDown 重写（已确认） | 15分钟 |
| `table_reader.py` | **不改代码，但新增 MarkItDown 作为"理解"通道** | 0 |
| `/learn` 工作流 | 用 MarkItDown 读文档 → LLM 提炼知识 | 新建 |
| `/design` 工作流 | table_reader 继续做精确操作 | 不变 |

```
/learn 流程：MarkItDown.convert(任意文件) → markdown → LLM 提炼 → knowledge/*.md
/design 流程：table_reader.query_db() → 精确数据 → 执行策划填表
```

**不是 A 替换 B，是 A 和 B 在不同场景各司其职。**
