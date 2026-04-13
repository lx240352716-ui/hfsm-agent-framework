# Stitch MCP 接入问题记录

> 记录 Stitch MCP 集成过程中遇到的所有问题，供后续优化参考。

---

## AI 侧问题（开发过程中发现）

### 1. Bearer token 认证失败 ✅ 已修

- **现象**: HTTP 401 UNAUTHENTICATED
- **根因**: Stitch API 不接受 `Authorization: Bearer {key}`，正确 header 是 `X-Goog-Api-Key`
- **修复**: 改用 `X-Goog-Api-Key` header

### 2. projectId 格式错误 ✅ 已修

- **现象**: `generate_screen_from_text` 返回 "entity not found"
- **根因**: `create_project` 返回 `projects/6047...`，但 generate 只接受纯数字 `6047...`
- **修复**: 自动 `split('/')[-1]` 取纯数字部分

### 3. HTTP 超时 ✅ 已修

- **现象**: generate 调用在 120s 超时
- **根因**: Stitch 生成一个界面需要 70-90 秒，系统 socket 提前中断
- **修复**: timeout 设为 600s

### 4. 新项目首次生成只返回 designSystem ⚠️ 部分修复

- **现象**: `generate_screen_from_text` 返回 `outputComponents[0].designSystem`，无 screenshot
- **根因**: Stitch 对新项目第一次 generate 自动创建 design system 而非 screen
- **修复**: 支持 `ui_sections.json` 传 `stitch_project_id` 复用已有项目（稳定路径）
- **残留**: warm-up 路径（新建项目）不稳定 — warm-up 后仍可能返回 designSystem
- **建议**: 后续可加 `.env` 的 `STITCH_DEFAULT_PROJECT_ID` 全局共用

### 5. 项目 URL 404 ❌ 未修

- **现象**: `https://stitch.withgoogle.com/project/{id}` 返回 404
- **根因**: 不知道正确的 Web URL 格式
- **影响**: wireframe_result.json 里的 project_url 无效

### 6. git push 网络故障 ❌ 外部问题

- **现象**: `fatal: unable to connect to github.com via 127.0.0.1`
- **根因**: 代理配置问题
- **处理**: commit 在本地，需手动推送

---

## 用户侧问题

### U1. 缺少项目风格解析 ❌ 未做

- **问题**: 直接把原始中文描述丢给 Stitch，没有先理解项目美术风格、知识库内容、本地 asset
- **我的问题**: 跳过了最核心的"理解项目"环节，把 wireframe 做成了无脑转发
- **解决方案**:
  1. wireframe 前加一步 LLM 调用：读 knowledge 美术规范 + 扫描 asset 目录提取风格关键词
  2. 用 Stitch `create_design_system` 注入项目专属风格（色板/字体/圆角等）
  3. 每次 generate 时基于 design system 生成，保证风格统一

### U2. 应生成 5 张图只生成了 1 张 ❌ 未做

- **问题**: draft.md 有 5 个界面章节，实际只生成了 1 张
- **我的问题**: 测试时手动覆盖 `ui_sections.json` 只写了 1 个 section，没有用 `_extract_ui_sections()` 从 draft.md 提取全部界面
- **解决方案**:
  1. wireframe 入口应自动从 draft.md 提取所有 `###` 界面章节
  2. 不依赖手动构造 JSON，流程应该是透明的端到端

### U3. 缺少专门 agent 做 prompt 优化和知识沉淀 ❌ 未做

- **问题**: 纯脚本调用，没有 LLM 参与 prompt 工程、结果评审、知识回写
- **我的问题**: 把 wireframe 做成了工具函数而非 agent 工作流
- **解决方案**:
  1. 新增 L2.wireframe agent（或在 L1.system wireframe 状态加 LLM 循环）
  2. 职责：中文描述 → 优化为 Stitch prompt → 调 Stitch → 评审结果 → 不满意则 edit_screens → 沉淀 prompt 经验到 system_rules.md
  3. agent 应记录每次成功的 prompt 模板作为知识积累

### U4. 开发耗时 40 分钟（实现方法问题）❌ 需改进工作方式

- **问题**: 整个 Stitch 接入耗时过长
- **我的问题**: 没有先充分研究 API 文档和行为，用"写代码 → 跑 → 失败 → 改 → 再跑"试错，每轮 80s 等待，6 轮 = 40 分钟浪费
- **解决方案**:
  1. 先用轻量探测脚本摸清所有 API 行为（工具列表、参数格式、各场景区别）
  2. 确认全部通过后再写生产代码
  3. 不要边写边试

---

## 待解决优先级

- [ ] **U1**: 项目风格解析 + design system 注入（讨论中）
- [ ] **U2**: 全量界面生成
- [ ] **U3**: wireframe agent 工作流
- [ ] **U4**: 改进开发方式（后续执行时注意）
- [ ] AI-4: 新项目 warm-up 稳定性
- [ ] AI-5: 修正 project_url 格式
