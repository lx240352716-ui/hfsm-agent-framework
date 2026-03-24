# 如影随形被动技能设计复盘 (2026-03-11)

## 1. 流程踩坑与规则补全

- **子句拆解遗漏"清除"维度**：首次设计只覆盖了"触发+效果+限制"3类，完全忽略了"清除"类子句（#4技能攻击后清1层、#6行动结束全清）。6个子句只实现了3个打了一半。根因是没有强制四要素覆盖检查。已在 `combat_rules.md` 规则1中强化，并在 `clause_checklist.md` 模板里写死四分类栏位，缺一不可。
- **导出碎片文件引发三值冲突**：`write_new_rows()` 只能生成"新增行"格式的 xlsx，子任务3需要**修改已有行**的字段值，被迫生成名叫"新增"实为"修改"的碎片文件。最终同一个 `行动后生效计数` 字段在 handoff JSON(=1)、大表副本(=0)、修正文件(=99) 三处出现三个不同值，执行策划完全无法判断该信谁。已新增 `write_output()` upsert 函数（主键存在→整行替换），每张表只保留一份 xlsx，写入 `combat_rules.md` 规则4。
- **`python -c` 内联命令在 PowerShell 中反复挂死**：中文列名和引号嵌套导致命令行解析失败或无限等待，浪费大量排查时间。已写入 `combat_rules.md` 规则5：所有数据查询必须写 .py 文件执行，禁止内联。

## 2. 工具链能力升级

- **`write_output()` upsert 导出（新增）**：替代 `write_new_rows()`，output 目录下每张表始终只一份 `{表名}.xlsx`。文件不存在则创建，主键已存在则整行替换，不存在则追加。从根源消除了碎片文件冲突问题。`write_new_rows()` 已标记废弃并加 DeprecationWarning。
- **`copy_to_output()` 大表硬拦截（新增）**：源文件超过 1MB 直接 raise ValueError，防止再出现把 15000 行的 `_Buff.xlsx` 整表复制到 output 的情况。
- **`save_handoff()` 字段透传（修复）**：原来只传 `tables`，现在透传 data 中所有字段（包括 `design_check`），战斗策划不再需要绕过函数手写 JSON。
- **`ChangeTracker` 按主键去重（修复）**：同一 `(table, id)` 后来的 track 覆盖先前的，`CHANGES.md` 只反映最终状态，不再堆积中间过程值。

## 3. 性能优化

- **延迟加载 pandas/openpyxl**：`import utils` 从 0.66s 降到 0.035s（19倍）。pandas 和 openpyxl 只在实际调用到读写 Excel 的函数时才 import，绝大多数脚本只用 SQLite 查询，不再为用不到的库付启动代价。
- **`read_table` / `find_row_by_id` 自动走 SQLite**：对已索引的大表（_Buff/FightBuff/BuffActive 等），自动路由到 SQLite 秒查，不再每次用 pandas 解析 xlsx。`read_table(_Buff)` 从 6.07s 降到 0.68s，`find_row_by_id` 从 ~6s 降到 0.004s（1500倍）。
- **SQLite 连接缓存**：`query_db()` 不再每次调用都 open/close 连接，同一进程内复用同一个 connection 对象。连续查询场景下第二次调用开销为 0。

## 4. 质量保障体系补全

- **持久化回归测试 `test_utils.py`（新增）**：16 个断言覆盖 write_output 新建/upsert、ChangeTracker 去重、save_handoff 透传、copy_to_output 大表拦截、query_db 连接缓存。后续改动 `utils.py` 跑一遍即可回归。
- **`qa_runner.py` 规则5 output 导出校验（新增）**：`check_output_files()` 自动扫描 output 目录，检查每张表是否只有一份 xlsx、是否存在大表副本（>5000行）、handoff JSON 格式是否完整。之前 QA 只校验源表，导出错了也不会被拦住，现在补上了。
- **`handoff_contract.md` 文档补充（新增）**：新增 xlsx 导出规则说明和 `design_check` 字段 schema，让执行策划知道收到的 JSON 应该长什么样。
