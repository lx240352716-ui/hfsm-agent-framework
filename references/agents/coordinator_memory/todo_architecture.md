# 项目 TODO（唯一权威文件）

> **规则**：所有待办只在本文件维护。已完成项移入 `done.md`。
> 最后更新: 2026-03-31 (v2.0 全部代码完成)

---

## v2.0 — 独立服务化 + IM 接入

### Phase 1: LLM 抽象层 ✅

- [x] `scripts/core/llm_client.py` — OpenAI 兼容模式客户端
- [x] `scripts/core/prompt_builder.py` — 知识文件 → system prompt 构建器
- [x] `.env.example` 新增 `DASHSCOPE_API_KEY` / `LLM_MODEL` 配置
- [x] `scripts/tests/test_llm.py` — Prompt Builder 4/4 通过
- [ ] ⚠️ 阿里云账号欠费（Arrearage），充值后重跑 test_llm.py 验证

### Phase 2: HFSM Controller ✅

- [x] `scripts/server/hfsm_controller.py` — 状态机控制器
- [x] 多用户会话管理（get_controller / reset_controller）
- [x] 三类状态驱动（llm → LLM API / pause → 等用户 / script → 执行 hook）

### Phase 3: 钉钉接入 ✅

- [x] `scripts/server/dingtalk_bot.py` — Stream SDK 消息监听
- [x] `scripts/server/app.py` — FastAPI 入口（--dingtalk / --http 双模式）
- [x] /reset 和 /status 命令
- [ ] 钉钉开放平台创建应用 + 配置机器人（需要手动操作）
- [ ] 端到端验证：钉钉群 @机器人 → HFSM 处理 → 回复

### Phase 4: 一键安装 ✅

- [x] `setup.bat` — Windows 一键安装脚本
- [x] `requirements.txt` 新增 openai / fastapi / uvicorn / dingtalk-stream
- [ ] 更新 QUICKSTART.md（加入服务启动说明）

### 待用户操作

- [ ] 阿里云百炼控制台充值 / 获取有效 API Key
- [ ] 钉钉开放平台创建应用 → 获取 AppKey/AppSecret
- [ ] 将 Key 填入 .env → 跑 test_llm.py 验证

---

## v3.0 — Skill 体系升级 ✅

> 设计原则：从策划使用场景出发，5 个动词覆盖日常工作：**做、改、问、查、看**
> Workflows 位置：`.agents/workflows/`

### `/design` — 做（复杂需求）
- [x] `.agents/workflows/design.md` — 完整 HFSM 工作流入口

### `/quick` — 改（快速修改）
- [x] `.agents/workflows/quick.md` — S_Express 模式
- [x] 改造 S_Express：通过 `--start-at` 从 L1 开始
- [x] `hfsm_bootstrap.py` 加 `--start-at` 参数
- [x] 验证 `--start-at L1.combat`

### `/consult` — 问（设计咨询）
- [x] `.agents/workflows/consult.md`
- [x] 读 coordinator_rules.md 分类，加载对应知识库

### `/lookup` — 查（查资料）
- [x] `.agents/workflows/lookup.md`
- [x] 合并 query.py + check_factor.py + search_table.py 统一入口

### `/status` — 看（查进度）
- [x] `.agents/workflows/status.md`
- [x] 调用 hfsm_bootstrap.py 报告状态
