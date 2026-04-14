# 架构 TODO

> 所有架构/系统级待办在此维护。完成项归档到 done.md。
> 每次对话开始先读此文件，结束时更新。

---

## Phase 3: Stitch MCP 接入（wireframe 状态）✅ 已完成（2026-04-13）

### 实现细节

- 接入方式：Stitch MCP JSON-RPC 2.0（`https://stitch.googleapis.com/mcp`）
- 认证：`X-Goog-Api-Key: STITCH_API_KEY`（存于 `.env`）
- 每个界面约 75-90 秒生成，PNG 下载至 `data/wireframes/`
- 支持复用现有项目（`ui_sections.json.stitch_project_id`）跳过预热

### 已验证

- `赢家岛通吃` 游戏主界面：78.9s，87.9KB PNG ✅

### 子任务（全部完成）

- [x] 研究 Stitch MCP server 的接口和认证方式
- [x] 实现 wireframe hooks：ui_sections.json → Stitch → PNG
- [x] 测试：生成 1 个界面线框图
- [x] 推送到 GitHub

---

## [SHELVED] Phase 4: Wireframe 自动生成（2026-04-13 ~ 04-14，已搁置）

> 尝试了多种方案，均不满足项目需求，暂停。

- 方案1: LLM Vision → SVG 线框图 — 组件风格不统一
- 方案2: 组件规范 + SVG 拼装 — 还原度不够
- 方案3: LLM Vision → HTML 线框 — 手写还原度有限
- 方案4: screenshot-to-code（开源工具） — 已部署测试，效果不理想
- 结论：当前 LLM 生图/转码还原度不足以满足游戏 UI 线框需求

### 保留文件（仅参考）

- `knowledge/wireframes/` — 测试生成的 SVG/HTML 线框
- `references/tools/screenshot-to-code/` — 开源工具（可删）
- `references/scripts/tools/generate_wireframes.py` — 批量生成脚本

---

## 已完成（归档见 done.md）

- System Designer L1 Agent 完整实现（2026-04-10）
- HFSM L1.system 注册（2026-04-10）
- 全量代码 review + 14 项修复（2026-04-13）
- 推送 GitHub `85bbcb4`（2026-04-13）
