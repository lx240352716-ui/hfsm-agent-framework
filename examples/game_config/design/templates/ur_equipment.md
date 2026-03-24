# UR装备套装 — 配置模板

> 来源：2026-03-10 UR红发装备实战
> 适用：新增一套UR装备（4件套，含套装效果+增强buff）

## 涉及表清单（13张）

| # | 表 | 行数 | 说明 |
|---|---|---|---|
| 1 | Equipment.xlsx | 4 | 装备本体，⚠️ col35(boxId)必须替换 |
| 2 | EquipSuit.xlsx | 2 | 2件套+4件套，col8(fightBuffId)指向新FightBuff |
| 3 | EquipBox.xlsx | 4 | 装备箱 |
| 4 | _EquipRandProp.xlsx | 1 | 随机属性 |
| 5 | _EquipmentReIdentifyConfig.xlsx | 4 | 洗炼 |
| 6 | EquipmentHoleExpand.xlsx | 12 | 打孔(每件3级) |
| 7 | EquipResonance.xlsx | 8 | 共鸣(每件2条) |
| 8 | EquipUpgrade.xlsx | 16 | 增强(每件4级) |
| 9 | FightBuff.xlsx | 18 | 套装效果+增强buff的组装层 |
| 10 | _Buff.xlsx | 8 | 子buff定义 |
| 11 | BuffActive.xlsx | 20+ | buff参数 |
| 12 | BuffOdds.xlsx | 8+ | 概率梯度 |
| 13 | Item.xlsx | 1 | 装备任选箱(仿青龙619357) |

**不需要新增**：EquipRefine(按部位共享)、变异(共享)、评分/分解(共享)

## 参考行

| 表 | 参考套装 | 参考ID范围 |
|---|---|---|
| Equipment | 路飞解放者 | 504601-504604 |
| EquipSuit | suitId=1063 | — |
| FightBuff | 30241-30260 | — |
| Item(任选箱) | 青龙 | 619357 |

## 常见陷阱

| # | 陷阱 | 铁规 |
|---|---|---|
| 1 | Equipment.col35(boxId)残留路飞值 | 复制后必检 |
| 2 | FightBuff备注列残留路飞描述 | 全列扫描替换 |
| 3 | _Buff因子名自造(penetration等) | 必须查Factor速查表 |
| 4 | FightBuff的buffList/odds/grade数量不匹配 | && 分隔数必须相等 |
| 5 | timing=29≠致死，是"被选中未命中" | 查时机速查表 |
| 6 | dodge的PerFactor=0不是1 | 查design_patterns因子表 |
| 7 | 4件套target应为1(全体)不是101(自身) | 查understanding目标映射 |
| 8 | Item表只需任选箱，装备本体不在Item注册 | — |
| 9 | 脚本重跑导致重复行 | 写后必跑dedup |

## 任选箱模板(Item表)

```
仿照青龙619357，完整拷贝45列，替换：
- col[0] 物品ID → 新ID
- col[4] 名字 → XX装备任选箱
- col[5] 名字文本 → XX装备任选箱
- col[6] 描述 → 使用可以任选一件XX装备
- col[14] 功能扩展 → 1:1200,boxId1,1;1200,boxId2,1;1200,boxId3,1;1200,boxId4,1
```
