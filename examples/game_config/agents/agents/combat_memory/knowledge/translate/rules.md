# 战斗策划 — 翻译层 (Translation)

> 把理解层拆出的自然语言翻译成配置表字段。
> 翻译不了的 → 去例子层找拼接方案 → 例子层也没有 → 向用户讨论实现方案

## ⚠️ 铁规：禁止自编任何映射表

**时机/目标/因子必须从速查表查，不得凭记忆填写：**

| 翻译什么 | 去哪查 |
|---------|-------|
| 时机ID | `combat_memory/condition_map.md` 或 `query_db` 查 FightBuff 表 |
| 目标ID | `combat_memory/condition_map.md` 或 `query_db` 查 FightBuff 表 |
| 因子名 | `scripts/configs/factor_whitelist.json`（唯一权威） |
| 条件 | `query_db` 查 `_BuffCondition` 表或新建 |

## ⚠️ 翻译层必填输出（执行层契约）

> 执行层收到 JSON 后会校验以下字段。**缺一个都打回，不会默认补。**
> buff类型和取百分比由执行层从 `factor_whitelist.json` 自动推导，翻译层不需要填。
> buff分组由执行层从 buffId 自动计算，翻译层不需要填。

### _Buff 每行必填（12个设计字段）

| 字段 | 翻译规则 |
|------|---------|
| PerFactor（Buff因子） | 从 factor_whitelist.json 查，核心字段 |
| IsDebuff（是否减益） | "降低/削减"→1，"提升/增加"→0 |
| DispelAble（可净化） | 默认1，需求说"不可驱散"→0 |
| AfterActionCount（行动后计数） | "持续N回合"→N，无限→0 |
| BeforeActionCount（行动前计数） | 通常0，特殊需求翻译 |
| EffectRound（生效回合） | 通常0，特殊需求翻译 |
| AttackEffectCount（攻击生效次数） | 通常0，特殊需求翻译 |
| DefenseEffectCount（防御生效次数） | 通常0，特殊需求翻译 |
| BattleLimitCount（整场限制次数） | "最多30%"÷单次=N |
| StackLimit（叠加上限） | "最多N层"→N，未说明→99 |
| SpecialData（特殊配置数据） | type=7时必填，格式见例子层 |
| RelatedBuff（关联buff） | 关联的@符号引用，无关联→空 |
| 备注 | "技能名-效果描述" |

### BuffActive 每行必填

| 字段 | 翻译规则 |
|------|---------|
| buffId | 对应 _Buff 的 @引用 |
| grade | 通常1 |
| buff参数1 | 核心参数值（格式见 C 类规则） |
| 参数1升级加成 | 通常0 |

### FightBuff 每行必填

| 字段 | 翻译规则 |
|------|---------|
| buff时机 | 从时机ID速查表查 |
| buff目标 | 从目标ID速查表查 |
| buff条件 | 条件ID或0，&&拼接 |
| buff概率 | 1002=100%固定 |
| buffList | _Buff @引用，&&拼接 |
| buffGradeList | 通常1，&&拼接 |
| 备注 | "技能名-触发描述" |

### _BuffCondition 每行必填

| 字段 | 翻译规则 |
|------|---------|
| 条件类型 | 通常1 |
| 条件参数 | 格式化字符串，见常用条件参考 |
| 注释 | 描述 |

## 踩坑记录（语义澄清）

> 只记录速查表里找不到答案、需要额外解释的歧义。不记录任何ID映射。

| 歧义 | 说明 |
|------|------|
| 回合结束清掉 / 临时buff | 用 `行动后生效计数=1` 实现 |
| 叠加上限未明确说明 | 默认 `id叠加的个数限制=99` |
| 同一时机下先做A再做B | A的FightBuff ID < B的FightBuff ID（按ID升序执行） |

> ⚠️ 教训：红发4件套误用target=101，正确应为102（己方全体）
> 🔴 教训：红发免死护盾误用timing=29，正确应为18或31

## 常用条件参考

| 描述 | 条件参数格式 | 参考ID |
|------|------------|--------|
| 筛选特定阵营 | `src1:target,type1:camp,op:equal,...,const_val:阵营ID` | 80007(大妈团camp=7) |
| 场上某buffId数量>N | `src1:self,type1:TeamTotalBuffNum,param1:buffId,op:more,...,const_val:N` | 参考31350 |
| 施法者在第X排 | `src1:self,type1:row,op:equal,...,const_val:X` | — |
| 使用技能或奥义 | `src1:self,type1:SkillClass,op:more,...,const_val:0` | — |

## 表结构速查

```
FightBuff (组合层)
  ├─ buffList → _Buff (效果层)
  │                └─ buffId → BuffActive (参数层)
  ├─ buff条件 → _BuffCondition (条件层)
  └─ buff概率 → BuffOdds (概率层)
```

## buff类型速查

| 类型 | ID |
|------|---|
| 属性修改 | `1` |
| 持续伤害DOT | `2` |
| 直接伤害 | `3` |
| 免疫/标记 | `5` |
| 清除buff | `6` |
| 特殊机制 | `7` |
| 属性伤害 | `11` |
