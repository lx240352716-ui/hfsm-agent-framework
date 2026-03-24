# 破绽被动技能 — 总结报告

**日期**: 2026-03-11  
**任务名**: buff_破绽  
**涉及表**: 3 张（_Buff / BuffActive / FightBuff）


## 需求描述

> 自己每回合释放的首个技能命中目标时，为目标添加【破绽】效果。
> - 抗爆伤属性降低 50%
> - 持续 2 回合
> - 每被技能暴击 2 次，降低 6% 最大生命值
> - 最多降低 30%


## 配置总览

### _Buff（4 行新增 → rows 15956-15959）

| buffId | Buff因子 | 关键配置 | 作用 |
|--------|----------|----------|------|
| 3100020 | cridamage | 百分比=-0.5, 行动后计数=2 | 主buff，爆伤-50%，2回合 |
| 3100021 | 0 | 叠加不限, 行动后计数=2 | 被暴击计数标记（纯标记） |
| 3100022 | countBuffIdAddBuff | 数据=3100021,2&&3100023,1 | 每2层标记→触发削HP |
| 3100023 | DelPercentHp | 整场限制=5 | 削减6%最大生命（上限30%） |

### BuffActive（4 行新增 → rows 18877-18880）

| buffId | buff参数1 | 含义 |
|--------|-----------|------|
| 3100020 | -0.5 | 爆伤降低50% |
| 3100021 | 0 | 计数标记 |
| 3100022 | 1 | 计数器 |
| 3100023 | 0.06 | 削减6%HP |

### FightBuff（2 行新增 → rows 2479-2480）

| fightBuffId | 时机 | 目标 | buffList | 作用 |
|-------------|------|------|----------|------|
| 1900120 | 7(命中) | 1(技能目标) | 3100020 | 首个技能命中施加破绽 |
| 1900121 | 10(被暴击) | 101(自己) | 3100021 | 被暴击时叠加标记 |


## Buff 链路

```
技能命中(FightBuff 1900120)
    ↓
施加【破绽】主buff(3100020, cridamage -50%, 2回合)
    ├── 关联 → 计数标记(3100021)
    └── 关联 → 计数器(3100022, countBuffIdAddBuff)
                    ↓ 每2层标记
              触发 DelPercentHp(3100023, 6%, 上限5次=30%)

被暴击时(FightBuff 1900121)
    ↓
叠加计数标记(3100021) +1层
```


## 验证结果

| 检查项 | 结果 |
|--------|------|
| _Buff 4行数据 (3100020-3100023) | ✅ 通过 |
| BuffActive 4行参数值 | ✅ 通过 |
| FightBuff 2行触发 (1900120-1900121) | ✅ 通过 |
| ID唯一性（不与现有冲突） | ✅ 通过 |
| 绿底红字样式 | ✅ 已应用 |
| SQLite索引更新 | ✅ 42070 rows indexed |
| 源表备份 | ✅ snapshot/ 已创建 |


## 输出文件清单

| 路径 | 说明 |
|------|------|
| `references/output/buff_破绽/_Buff.xlsx` | 独立增量 xlsx |
| `references/output/buff_破绽/BuffActive.xlsx` | 独立增量 xlsx |
| `references/output/buff_破绽/FightBuff.xlsx` | 独立增量 xlsx |
| `references/output/buff_破绽/handoff_combat.json` | 完整交接数据 |
| `references/output/buff_破绽/CHANGES.md` | 修改清单 |
| `references/output/buff_破绽/change_log.json` | 变更日志 |
| `references/output/buff_破绽/snapshot/` | 源表备份 |


## 过程记录

1. 从 `buff_如影随形` 的 handoff JSON 学习配表模式
2. 通过 SQLite 快查(`query_db`)检索现有配置，确认因子名：
   - `cridamage` = 暴击伤害（负值=降低）
   - `countBuffIdAddBuff` = 按层数触发添加buff
   - `DelPercentHp` = 百分比最大生命削减
3. 生成全部数据并填写到源表
4. 修复 `_Buff` 第一列 ID 映射问题（源表第一列无表头名）
5. 重建 SQLite 索引，验证全部通过
