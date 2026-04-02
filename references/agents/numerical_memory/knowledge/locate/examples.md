# locate 阶段案例

## 案例: 礼包需求（清明节礼包）

需求原文: "做一个清明节礼包，参考觉醒徽章礼盒（沙·鳄鱼），商城参考78"

### 模块 → 表定位 + 参考行来源

| 模块 | 表 | 定位方式 | 理由 |
|---|---|---|---|
| 道具注册 | Item | search_keywords: ["觉醒徽章", "礼盒"] | 用户提到了"参考觉醒徽章礼盒" |
| 掉落配置 | _DropGroup | _ref_id（从 Item 参考行的 params 推理） | 礼包结构: Item.resourceDes → DropGroup |
| 商城上架 | _ShopItem | _ref_id（用户明确说了"商城参考78"） | 用户直接给了 ID |

### 要点

- 用 `requirement_structures.md` 的礼包结构确认需要 Item + _DropGroup + _ShopItem
- _DropGroup 的 _ref_id 可从 Item 参考行的关联字段推理出来
- 如果用户没给明确参考，用 search_keywords 让 hook 搜源表
