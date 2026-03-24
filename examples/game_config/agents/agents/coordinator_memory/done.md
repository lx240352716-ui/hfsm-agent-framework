# 已完成归档

> 从 todo_architecture.md 拆出的已完成项

---

## 架构优化（2026-03-11 ~ 03-12）

- [x] P0★ 战斗模块状态机重构 — Pipeline → Workflow 重命名，17/17 测试通过
- [x] P0 文件命名规范整理 — naming_convention.md + 批量重命名
- [x] P2 因子白名单 — factor_whitelist.json(30因子) + validate_factor() + register_factor()
- [x] P0★ Express 快车道模式 — S_Express 流程 + 脚本防呆

## Workflow 重构（2026-03-13）

- [x] 分层 Workflow — 子状态机 + SYSTEM_HANDOFF + 越权处理
- [x] combat_fill → `agents/执行策划/fill.py` 迁移初版
- [x] table_schemas.json + filling_rules.md + scan_tables.py + table_registry.json(1237表)

## 执行策划 Workflow 统一（2026-03-16）

### 主线A: execution.json 7步工作流
- [x] `execution.json`（resolve→align→fill_defaults→assign_ids→resolve_refs→check→staging）
- [x] `execution_hooks.py` — 6个纯函数 hook（零副作用，幂等重试安全）
- [x] `table_validator.py` — 纯逻辑校验器（零IO，执行策划+QA共用）
- [x] `table_reader.read_headers()` — 通用读表头函数
- [x] combat.json 砍至3步（split→categorize→translate）
- [x] standard.json execute→sub_workflow:execution.json
- [x] workflow.py _resolve_hook 搜索路径增强
- [x] 测试 18/18 通过（含新增 test_from_json_execution）
- [x] 删除 `fill.py` + `table_schemas.json`

### 主线B: 知识存储统一
- [x] `agents/执行策划/memory/` 私有知识库（filling_rules/table_defaults/id_ranges/id_rules）
- [x] `table_registry.json` + `scan_tables.py` 迁到 `scripts/configs/`（公共）
- [x] 代码路径引用全部更新

### 主线C: 写入保底
- [x] excel_writer.write_source 三层保底（锁检测+强制备份+写后校验）

### 主线D: 清理
- [x] 删除 `combat_fill.py`（511行死代码）
- [x] 删除 `test_express.py`（过时测试）

## 技能配表（2026-03-06 ~ 03-11）

- [x] 如影随形被动技能 — 全流程 S1-S9 走通 + 填表
- [x] 大妈灵魂技能 — 写入完成（14+14+5+7行），发现10个问题（见 walkthrough）

## 项目基建（2026-03-06）

- [x] SKILL.md 本地路径适配
- [x] scripts/ 目录重构 — core/combat/tools/tests/archive

## QA + Merge + 全面审计（2026-03-16）

### P0: merge 阶段
- [x] 两阶段提交、备份、回滚、写后校验
- [x] merge 改为写到 `output/<任务名>/`（不动源 Excel），打印路径告知用户检查

### P0.5: qa 阶段
- [x] standard.json 调整顺序：execute → qa → merge（先校验再写入）
- [x] qa 跨表外键校验 + 因子白名单 + ID 唯一性

### P0.8: read_headers 统一重构
- [x] 删旧 `read_headers`/`get_headers`（openpyxl），统一为 `get_columns()` 走 SQLite

### P0.9: 全面审计（6 维度）
- [x] **Import 链**: 删 5 处死引用（excel_writer/db_writer/registry 参数）
- [x] **重复造轮子**: qa_runner 444→178 行，删 FIRST_COL_FALLBACK
- [x] **Workflow 数据流**: check_hook 适配接口，task_name 加入 understand 输出
- [x] **MD 防幻觉**: 删硬编码 SQL 模板 + 孤儿 id_rules.md
- [x] **孤儿文件**: 删 14 个废弃脚本 + 2 个废弃 CLI
- [x] **数据流形变**: merge_data 全链路结构一致

## Row6 英文字段名全链路迁移（2026-03-16）

- [x] `get_columns` 调用方全部改为 `english=True`
- [x] 删除 `COLUMN_NAME_MAP` 翻译字典
- [x] 删除 `KEY_COLS_FALLBACK`
- [x] `constants.py` KEY_COLS/REQUIRED_FIELDS 改英文
- [x] `table_defaults.json` / `id_ranges.json` key 改英文
- [x] `resolve/fill_defaults/assign_ids/staging` 全面重构
- [x] 关键节点加清晰报错
- [x] `test_row6_compliance.py` + `test_stale_refs.py` 检测脚本

## 架构级防御与健康检查（2026-03-16）

- [x] 边界与异常防御（SQL 注入防护、库损自纠）
- [x] 状态机制与数据流一致性（幂等性、上下文沙盒、缓存过期）
- [x] 性能与资源收敛（GC、句柄保护）
- [x] 架构设计解耦度（Core 层净化、类型安全协议）
- [x] 可观测性与可溯源性（结构化日志、数据血缘）
