# Factor速查表

**用途**：快速查找BUFF效果因子


---

## 按效果分类

### 属性加成 (buffClass=1)

| Factor | 说明 | 常用参数 |
|--------|------|----------|
| atk | 攻击力加成 | buffParam1 |
| def | 防御力加成 | buffParam1 |
| hp | 生命值加成 | buffParam1 |
| maxHp | 生命上限加成 | buffParam1 |
| speed | 速度加成 | buffParam1 |
| hit | 命中率加成 | buffParam1 |
| cri | 暴击率加成 | buffParam1 |
| dodge | 闪避率加成 | buffParam1 |
| damageadd | 技能伤害加成 | buffParam1 |
| elementAll | 属性伤害加成（全属性） | buffParam1 |
| damagereduce | 伤害减免 | buffParam1 |

> **"所有伤害加成"** = `damageadd`(技能伤害) + `elementAll`(属性伤害)，需拆成2个_Buff

### 坚韧相关 (buffClass=1/7)

| Factor | 说明 | 常用参数 |
|--------|------|----------|
| toughnessDamage1 | 破韧效率 | buffParam1 |
| toughnessDamage2 | 破韧最终加成 | buffParam1 |
| toughnessCri | 坚韧暴击率 | buffParam1 |
| AddToughness | 增加坚韧值 | buffParam1/2/3 |
| AddToughnessDef | 坚韧防御 | buffParam1 |
| AddToughnessProp | 坚韧属性转换 | someData=属性ID |

### 控制效果 (buffClass=5)

| Factor | 说明 | 备注 |
|--------|------|------|
| Dizzy | 眩晕 | 普通眩晕 |
| ExtremeDizzy | 究极眩晕 | 永不可被免疫 |
| MustHit | 必中 | 攻击必定命中 |
| MustDodge | 必须闪避 | 强制闪避 |
| CannotRecoverHp | 禁疗 | 无法恢复生命 |
| CanNotRevive | 无法复活 | 战败后无法复活 |
| NoSkillDamage1 | 免疫技能伤害 | 免疫技能伤害 |
| ForbidActiveAndUltimateSkill2 | 究极麻痹 | 永不可被免疫 |

### 清除类 (buffClass=6)

| Factor | 说明 | 常用参数 |
|--------|------|----------|
| ClearSomeBuffId | 清除指定BUFF | SomeData=BUFFID |
| ClearSomeNumBuffId | 清除N层BUFF | SomeData=BUFFID |
| ClearSomeBuffType | 清除类型BUFF | SomeData=BuffType |
| ClearRandomBuffTypeByNum | 随机清除 | SomeData=类型,数量 |
| ImmuneSomeBuffId | 免疫指定BUFF | SomeData=BUFFID |
| ImmuneSomeBuffFactor | 免疫类型效果 | SomeData=因子名 |
| ChangeSkillActive | 技能切换 | 时机必须用62 |

### 特殊效果 (buffClass=7)

| Factor | 说明 | 常用参数 |
|--------|------|----------|
| countBuffIdAddBuff | BUFF数量叠加 | SomeData=格式 |
| BuffGradeMulti | 一键多层 | SomeData=格式 |
| OneMoreSkill | 额外技能 | buffParam1=技能ID |
| CreateFightBuff | 创建战斗BUFF | SomeData=FightBuffID |
| ResetActioned | 刷新行动 | - |
| PosChange2 | 位置变化 | - |
| StopCurrentAction | 停止行动 | - |
| DelPercentHp | 百分比生命伤害 | buffParam1 |
| ElementDamage | 元素伤害 | SomeData=格式 |
| ElementCanCri | 属伤可暴击 | buffParam1=1 |

### 护盾相关 (buffClass=7)

| Factor | 说明 | 常用参数 |
|--------|------|----------|
| ShieldToHp | 护盾转生命 | SomeData=格式 |
| PropToShield | 属性转护盾 | SomeData=格式 |
| GetShiledBuffValue | 获取护盾值 | buffParam1 |

### 组合因子

| Factor | 说明 | 常用参数 |
|--------|------|----------|
| speed&&dodge | 速度+闪避 | buffParam1/2 |
| speed&&hit | 速度+命中 | buffParam1/2 |
| ap&&anger | 行动点+怒气 | buffParam1/2 |
| speed&&hit&&hp | 速度+命中+生命 | buffParam1/2/3 |
| maxHp&&atk&&block | 生命+攻击+格挡 | buffParam1/2/3 |

---

## 按BuffClass分类

### buffClass=1 数值类

```
atk, def, hp, maxHp, speed, hit, cri, dodge,
damageadd, damagereduce, toughnessDamage1,
toughnessCri, real, ap, limitSkillDurationMinusHp
```

### buffClass=5 控制类

```
Dizzy, ExtremeDizzy, MustHit, MustDodge,
CannotRecoverHp, CanNotRevive, NoSkillDamage1,
ForbidActiveAndUltimateSkill2, InvalidSomeBuff,
ToughnessCalc
```

### buffClass=6 清除类

```
ClearSomeBuffId, ClearSomeNumBuffId, ClearSomeBuffType,
ClearRandomBuffTypeByNum, ImmuneSomeBuffId,
ImmuneSomeBuffFactor, ChangeSkillActive, ClearFactor,
CreateBuffTransferParamBySource
```

### buffClass=7 坚韧/特殊类

```
AddToughness, AddToughnessShield, AddToughnessMax,
AddToughnessDef, AddToughnessPreShield, AddToughnessProp,
DelPercentToughness, LockToughness, ToughnessDamage,
AddToughnessCri, AddToughnessCriDamage,
DelaySettleByCondition, DamageOverFlowSave,
RecoverLostHp, DelPercentHp, OtherUnitDoubleDamage,
ShieldToHp, PropToShield, GetShiledBuffValue,
CreateBuffByBuffValue, CountCampBuffIdAddBuff,
countBuffIdAddBuff, OneMoreSkill, ElementDamage,
ExtremeImmuneSomeDamageType, ExpendAPExtraNotEffectAnger,
ExpendAPExtra, CreateFightBuff, ResetActioned,
BuffGradeMulti, StopCurrentAction, PosChange2,
ReleaseSpecialSkill
```

---

## 快速查询

### 想要加属性 → 用这些Factor

| 效果 | Factor |
|------|--------|
| 加攻击 | atk |
| 加速度 | speed |
| 加生命 | hp |
| 加闪避 | dodge |
| 加命中 | hit |
| 加暴击 | cri |
| 加伤害 | damageadd |
| 真实伤害加成 | real (buffClass=1) |

### 想要控制 → 用这些Factor

| 效果 | Factor |
|------|--------|
| 眩晕 | Dizzy |
| 必中 | MustHit |
| 禁疗 | CannotRecoverHp |
| 无法复活 | CanNotRevive |
| 无敌 | MustDodge + ImmuneSomeBuffId |

### 想要清除/免疫 → 用这些Factor

| 效果 | Factor |
|------|--------|
| 清除BUFF | ClearSomeBuffId |
| 清除N层 | ClearSomeNumBuffId |
| 免疫BUFF | ImmuneSomeBuffId |
| 免疫类型 | ImmuneSomeBuffFactor |

### 想要坚韧 → 用这些Factor

| 效果 | Factor |
|------|--------|
| 破韧效率 | toughnessDamage1 |
| 坚韧攻击 | AddToughnessProp(71) |
| 坚韧防御 | AddToughnessDef |
| 坚韧护盾 | AddToughnessPreShield |

---

## 配置示例

```yaml
# 攻击力+100
- buff_id: 58701
  buff_class: 1
  factor: "atk"
  buff_param1: "100"

# 速度+20%
- buff_id: 58702
  buff_class: 1
  factor: "speed"
  per_factor: "1"
  buff_param1: "0.2"

# 眩晕2回合
- buff_id: 58710
  buff_class: 5
  factor: "Dizzy"
  round: 2

# 破韧效率+10%
- buff_id: 58720
  buff_class: 1
  factor: "toughnessDamage1"
  buff_param1: "0.1"
```

---

- 配置Buff: [../06_指令模板/配置Buff.md](../06_指令模板/配置Buff.md)
