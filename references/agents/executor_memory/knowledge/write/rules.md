# 跨表 ID 引用关系

> write 状态专用。分配新 ID 后，按本文件同步所有引用字段。

## 引用关系图

```
Item.itemId ──→ _DropGroup.param（道具ID出现在掉落参数中）
Item.params ──→ _DropGroup.groupId（道具功能扩展字段引用掉落组ID）
Item.itemId ──→ _ShopItem.itemInfo（商品信息中包含道具ID）

_Buff.buffId ──→ FightBuff.buffList（战斗buff引用子buff列表）
_Buff.buffId ──→ BuffActive.id（buff激活表关联buffId）

FightBuff.id ──→ EquipSuit.fightBuffId（套装效果引用战斗buff）
FightBuff.id ──→ EquipUpgrade.增强FightBuffId（装备强化引用战斗buff）

EquipSuit.suitId ──→ Equipment.suitId（装备引用套装ID）
Equipment.equipId ──→ EquipUpgrade.装备id

_BuffCondition.conditionId ──→ FightBuff.buff条件（战斗buff触发条件）

Formation.阵法ID ──→ FormationPos.阵法ID（阵法占位）
Formation.阵法ID ──→ FormationLev.阵法ID（阵法升级）
```

## 同步规则

1. 分配新 ID 后，全局扫描所有表的所有字段，将旧占位 ID 替换为新 ID
2. 替换使用字符串匹配（因为部分字段如 `buffList` 是 `"id1&&id2"` 格式）
3. 替换顺序：先替换长 ID 再替换短 ID（避免子串误替换）

## 注意事项

- `_ShopItem.itemInfo` 格式复杂（如 `"1:itemId,count;2:itemId,count"`），替换时注意不要破坏格式
- `FightBuff.buffList` 使用 `&&` 分隔多个 buffId
- `FormationPos` 每个阵法对应 5 行，A列是自增ID不是阵法ID

## fill 阶段跨表参考查找规则

> fill 状态查参考行时，参考实体的 ID 可能不是目标表的主键，而是藏在复合字段里。

### 逗号分隔字段解析

许多字段使用逗号分隔存储多个值（如 `itemInfo = "1001,619021,1"`）。查找时：

1. **先按主键查** — `WHERE [主键] = 参考ID`
2. **主键查不到 → 扫描所有列** — 用 `LIKE '%参考ID%'` 初筛
3. **初筛命中 → 精确验证** — 将字段值按 `,` 和 `;` 拆分，检查拆分后的子值是否精确等于参考 ID（避免子串误匹配，如 ID `100` 匹配到 `1001`）
4. **命中则用该行作参考行**

### 常见复合字段格式

| 字段 | 分隔符 | 示例 |
|---|---|---|
| `_DropGroup.param` | `,` | `"1001,76000017,1,100"` |
| `_ShopItem.itemInfo` | `,` | `"1001,76000017,1"` |
| `_ShopItem.currencyInfo` | `,` | `"1,0,100"` |
| `FightBuff.buffList` | `&&` | `"1001&&1002"` |
| `_ShopItem.limitData` | `,` | `"0,0,3,5,0"` |
