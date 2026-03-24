# 执行策划 — 设计层 (Design Patterns)

> 回答"每行怎么填？ID怎么分配？"
> 不知道 → 回理解层确认表结构 → 学到后写回本文件

## ID 分配规则

| 表 | ID规则 |
|---|---|
| Formation | 阵法ID顺延 |
| FormationPos | A列自增ID顺延, B列=新阵法ID, C列=用户指定占位ID |
| FormationLev | 顺延 |
| Item | 顺延 |
| _Buff | 子buff ID顺延(120xxx系列) |
| BuffActive | 自增ID顺延(3000xxx系列) |
| _BuffCondition | max+1顺延(10xxxx系列) |
| FightBuff | 2开头(20xxx) |

## 数据来源规则

| 字段 | 来源 |
|---|---|
| 经验值/助阵人数 | 参考同类型实体(如席卷之阵) |
| 占位ID | **必须向用户确认** |
| buff效果字段 | 来自战斗策划输出 |
| 数值字段 | 来自数值策划输出 |
| 图标 | 向用户确认，格式: item_xxxxxx |

## 行插入位置

**铁规**: 新行紧跟参考实体后面，不追加到文件末尾
- 例: 席卷之阵在第N行 → 凌冽之阵在第N+1行

## Fill 阶段补值

> fill 状态下 LLM 补空字段时的数据来源优先级，详细规则见 `executor_fill_rules.md`

| 优先级 | 数据来源 | 说明 |
|---|---|---|
| 1 | 上游 output.json | 数值/战斗策划已提供的字段，直接用 |
| 2 | 参考行 | query_db 查同表最新行或参考实体行 |
| 3 | 标 uncertain | 以上都查不到 → 标不确定，等用户确认 |
