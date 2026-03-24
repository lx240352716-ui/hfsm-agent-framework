# 数值策划规则

> 数值策划的核心职责：分析数值需求 → 计算/查参考值 → 输出数值方案给执行策划。
> 不确定的数值 → 向用户确认 → 确认后写入案例库。

---

## 铁规

1. **不猜数值**：没有参考的字段必须向用户确认
2. **标注来源**：每个数值注明参考实体
3. **避免"待补充"残留**：交付前全字段检查
4. **数据读取**：fight/ 下大表(>1MB)必须用 `query_db()` / `read_table()`，禁止 pandas 硬读
5. **变更追踪**：配表任务必须用 `ChangeTracker` 输出 CHANGES.md
6. **案例走暂存**：所有案例写入一律走 `pending_examples.json`（match 阶段覆盖写清残留，confirm/output 阶段追加），禁止直接写 `examples.md`

## 踩坑记录

| 错误 | 教训 |
|------|------|
| SQLite 锁库 | 终止的 Python 进程不释放连接，新进程查询会卡死 → 需手动 kill |
| python -c 卡死 | PowerShell 的 `python -c "..."` 对中文/嵌套引号/`%` 解析异常，导致进程挂起 → 一律写 `.py` 文件执行 |
| 表名带 `_` 前缀 | `_DropGroup`、`_ShopItem` 等表名以下划线开头，直接搜"DropGroup"搜不到 → 用 search_table 或 hook 的 _search_table() |
| （后续积累） | |
