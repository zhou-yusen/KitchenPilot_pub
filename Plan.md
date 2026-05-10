# KitchenPilot 后续开发计划

## 当前状态

KitchenPilot 已经推进到 **简历项目 MVP 阶段**。当前闭环包含 FastAPI API、Router-based LangGraph workflow、SQLite/seed 菜谱数据、Qdrant RAG、本地 fallback、session memory、统一推荐接口、三类 persona 推荐和零构建前端调试台。

已经完成：

- FastAPI 后端工程和主要 API 已具备，包括 chat、recipe、recommendation、history 等基础接口。
- LangGraph Agent 主流程已接入，包含输入解析、session memory、用户画像加载、意图路由、菜谱问答、统一推荐、质量检查、答案修复和最终回答。
- SQLite 初始菜谱数据、JSON loader、SQLite seed 和 `RecipeService` 数据库读取已接入；数据库异常或坏数据时回落到 seed JSON。
- LLM chat provider 与 embedding provider 已拆分，支持 Ollama 与 OpenAI-compatible API 的配置切换。
- 意图识别已支持规则、embedding 相似度和低置信度 LLM fallback；无法判断时返回 `fallback` 澄清问题。
- 菜谱已按 `overview / ingredients / step / failure / substitution / safety` 六类生成语义 chunk。
- Qdrant seed、chunk payload upsert、Qdrant search 和本地关键词 fallback 已有最小实现。
- RAG 服务已具备基本流程：优先 Qdrant 检索，失败时降级本地检索；检索结果会按问题意图轻量 rerank；LLM 失败时返回基于 source 的模板化回答。
- 推荐服务已有规则评分逻辑，考虑食材匹配、新手友好、难度、耗时、近期重复和 persona 权重。
- 轻量静态前端已实现，以单聊天窗口作为主入口，并展示 session、intent、recommendation_type、active_recipe、rewritten_query、recommendations、RAG sources 与 Agent trace。
- `demo_qdrant_rag.py`、`preview_recipe_chunks.py` 和相关单元/集成测试已覆盖当前关键路径。

## 当前风险与缺口

- 真实 Qdrant + embedding seed/search 已初步跑通，但还需要更多问题集验证稳定性。
- 固定样例的 top-k chunk 类型已基本符合预期，但仍需要扩大样例覆盖。
- RAG answer prompt 仍偏基础，source 引用、防幻觉和回答结构还需要增强。
- 推荐服务仍是规则 MVP，不是生产级个性化推荐系统。
- 用户画像是三类预设 persona，尚未从真实长期行为学习。
- 项目中仍有中文乱码/编码风险，需要后续统一排查和修复。

## 下一阶段目标

下一阶段主线是 **巩固简历项目展示**。核心 MVP 已可演示，后续优先做文档、演示路径、代码整理和小范围质量增强。

目标顺序：

1. 保持后端 API schema 稳定，后续优化只扩展不破坏当前 demo。
2. 按 `docs/DEMO_GUIDE.md` 固定演示路径。
3. 保留 Qdrant、embedding 或 LLM 不可用时的本地 fallback。
4. 将 RAG prompt、真实长期用户画像和正式前端工程化放入后续 backlog。

## 里程碑

### 里程碑 1：真实 Qdrant 检索验证（基础完成）

任务：

- 已运行 Qdrant seed，确认 256 个 chunk 可写入 collection。
- 已使用 `demo_qdrant_rag.py --seed` 展示 chunk 数量、collection 状态、写入数量和 top-k 结果。
- 已对固定验收问题逐条检查 top-k source 的菜名、chunk 类型、chunk 内容和 score。

验收标准：

- Qdrant collection 可被检测到。
- seed 脚本能输出生成 chunk 数和 upsert 数。
- point id 稳定，可重复 upsert。
- Qdrant 不可用时 API 不返回 500，并能降级到本地检索。
- 固定样例问题至少能命中相关 recipe 或相关 chunk。

### 里程碑 2：RAG 检索质量增强（基础完成）

任务：

- 对检索结果进行人工样例验证，重点观察 chunk 类型是否符合问题意图。
- 已加入轻量 rerank：
  - “失败、为什么、腥味、脆”类问题优先 `failure` 或相关 `step`。
  - “没有、替代、换成”类问题优先 `substitution`。
  - “安全、熟、处理、虾、肉类”类问题优先 `safety`。
  - “怎么做、步骤、火候”类问题优先 `step`。
- rerank 规则保持可解释，不引入复杂模型依赖。

验收标准：

- `土豆丝怎么炒得脆？` 优先命中 `failure` 或相关 `step` chunk。
- `没有蚝油怎么办？` 优先命中 `substitution` chunk。
- `鸡翅为什么有腥味？` 命中失败原因或处理技巧。
- `白灼虾怎么处理安全？` 优先命中 `safety` chunk。

### 里程碑 3：统一推荐 intent 与轻量前端调试台（基础完成）

任务：

- 顶层 intent 统一为 `recipe_qa / recommendation / fallback`。
- 推荐子类型通过 `recommendation_type` 区分 `ingredients / daily`，后续可扩展。
- 使用原生 HTML/CSS/JS 实现零构建调试页面。
- 前端只调用 `POST /api/chat` 作为主入口。
- 展示回答、intent、recommendation_type、quality check、RAG sources、Agent execution trace、推荐结果和 raw JSON。
- API 失败时显示可读错误。

验收标准：

- 后端运行时，前端聊天能显示 answer、sources 和 trace。
- 输入 `我有鸡蛋和土豆，推荐一道菜` 能显示 recommendation / ingredients 和推荐结果。
- 输入 `今天吃什么？` 能显示 recommendation / daily 和推荐结果。
- 页面长中文能换行，桌面宽度下无明显重叠。

### 里程碑 4：文档与演示收口（基础完成）

任务：

- 更新 README、backend README 和前端 README，使其反映当前 MVP 能力。
- 补充 `docs/DEMO_GUIDE.md`：启动后端、打开前端、演示问题、预期结果、回归命令。
- 整理项目说明，突出 FastAPI、LangGraph、SQLite、Qdrant、LLM、Embedding、RAG 和轻量前端展示的分工。

验收标准：

- 新环境按 README 可以启动后端和前端 demo。
- `cd backend && uv run pytest` 通过。
- 项目说明准确体现当前实现状态，不夸大真实模型效果。

### 里程碑 5：后续优化 Backlog

任务：

- 优化 RAG prompt，使回答明确基于检索依据。
- 明确并记录推荐评分公式。
- 加入更强的历史偏好、近期去重和推荐个性化。
- 根据需要迁移到 React/Vue 等正式前端工程。
- 统一排查中文乱码和编码问题。

验收标准：

- 优化项不阻塞当前轻量 demo 交付。
- 每次后端行为改动继续保持 `uv run pytest` 通过。

## 最近下一步

当前最近下一步是固定 git 版本并做演示验收：

1. 启动后端。
2. 打开 `frontend/index.html` 或 `http://127.0.0.1:5173`。
3. 用固定问题测试聊天、sources 和 trace。
4. 输入 `我有鸡翅，推荐一道菜` 测试食材推荐。
5. 切换新手/老手画像，输入 `推荐一道菜` 测试 persona 推荐差异。
6. 运行 `uv run pytest` 完成后端回归。

固定验收问题：

- `土豆丝怎么炒得脆？`
- `没有蚝油怎么办？`
- `鸡翅为什么有腥味？`
- `白灼虾怎么处理安全？`

## 常用命令

```powershell
cd backend
uv run python -m kitchenpilot.seed.seed_sqlite
uv run python -m kitchenpilot.seed.seed_qdrant
uv run python script/preview_recipe_chunks.py
uv run python script/demo_qdrant_rag.py --seed
uv run pytest
```
