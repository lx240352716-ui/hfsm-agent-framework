# 执行策划 — Fill 补值规则

> fill 状态专用。LLM 遇到空字段时，按本文件的降级顺序查值。

## 三重查询降级规则

遇到空字段，**必须按以下顺序**逐级查值，前一级有结果则停止：

### 第 1 级：上游数据

检查数值策划 / 战斗策划的 output.json 是否已提供该字段值。
- 来源：`execute_result.json` 中的 tables 数据
- 如果上游已填 → **直接用**，confidence = high

### 第 2 级：参考行数据（_ref_id 直查）

hook 已通过每张表 L1 输出的 `_ref_id` 直接查到参考行全量数据，作为模板。

**LLM 使用方式**：
1. 整行复制 `reference_rows` 作为基础
2. `_overrides` 里的字段 → 直接覆盖（如 `currencyInfo`、`limitData`）
3. 读 `_note` → 理解要改的内容（名字/描述等），生成新值
4. 参考行为 null → 保持 null，标 uncertain
5. 跨表 ID 替换 → write 阶段自动处理，此阶段不用管

### 第 3 级：标 uncertain

以上都查不到或查到但无法确定是否适用：
- 填建议值（如有）+ 标 `"uncertain": true`
- 附 `"reason"` 说明为什么不确定
- 等 fill_confirm 阶段由用户审核

## 铁规

1. **严禁跳级**：不许跳过第 1、2 级直接盲猜
2. **严禁沉默填 0**：不确定的字段不能悄悄填 0 或空字符串，必须标 uncertain
3. **参考行不是万能的**：如果参考行的值明显不适用（如不同类型实体），应降级到第 3 级
4. **null ≠ 0**：参考行该字段是 null → 填 null（Excel 空单元格），严禁擅自转成 0。0 是显式数值，null 是未设定/走默认，语义完全不同

## draft_filled.json 格式

```json
{
  "requirement": "需求描述",
  "tables": {
    "表名": [{
      "field_a": "确定值",
      "field_b": {"value": "建议值", "uncertain": true, "reason": "参考行无此字段"}
    }]
  }
}
```
