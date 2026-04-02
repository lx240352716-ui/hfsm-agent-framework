# QA 红线法典 (QA Rules)

> S8.5 私有。校验前必读。自主写入(内部循环发现新漏检) + 主策代写(交付后用户发现遗漏)。

## 业务底线 (Append-Only)

### 规则：主键唯一性检查
- **校验动作**：对每张修改的表，用pandas检查主键列是否有重复值
- **来源**：2026-03-10 UR红发，Item表619365出现2次

### 规则：buffList与odds/grade数量匹配
- **校验动作**：FightBuff中每行的 `buffList`(&&分隔) 数量 = `buff概率`(&&分隔) 数量 = `buff概率-F2`(&&分隔) 数量 = `buffGradeList`(&&分隔) 数量
- **来源**：2026-03-10 UR红发，FightBuff 30263-30278全部不匹配

### 规则：Factor名必须在白名单内
- **校验动作**：_Buff表中 PerFactor（Buff因子）列的值必须存在于 `scripts/configs/factor_whitelist.json`
- **来源**：2026-03-10 UR红发，自造penetration/toughnessAbsorb/DeathShield

## 孤岛防范 (Append-Only)

### 规则：Equipment.boxId外键检查
- **校验动作**：Equipment的col35装备箱子Id必须在EquipBox的普通装备ID列中存在
- **来源**：2026-03-10 UR红发，Equipment的boxId残留路飞值未替换

### 格式
```
### 规则：[描述]
- **校验动作**：[具体检查方式]
```
