# KitchenPilot 后续开发计划

## 当前状态

项目已经完成 FastAPI 后端骨架，并具备可运行的后端 MVP 基础：

- `backend/` 已采用 `uv + pyproject.toml + src layout + tests` 的 Python 工程结构。
- FastAPI 已提供统一 API Router、健康检查、CORS 配置和基础接口。
- LangGraph Agent 主流程已搭建，包含输入解析、用户历史加载、意图路由、菜谱问答、食材推荐、每日推荐、质量检查和修复节点。
- 当前业务链路主要依赖 mock 数据和 mock service。
- SQLite、Qdrant、LLM、Embedding 的工程入口已经预留，但主链路尚未接入真实数据源。
- `frontend/` 仍是占位目录，尚未实现可用界面。
- 项目文档中存在较多中文乱码，后续需要统一编码和重写关键说明。

## 总体目标

下一阶段目标不是继续堆接口，而是把后端从“骨架 + mock 闭环”推进到“真实数据 + 可演示 Agentic RAG 闭环”：

1. 用 SQLite 承接结构化菜谱、食材、步骤和用户历史。
2. 用 Qdrant 承接菜谱 chunk、技巧、失败原因和替代食材等语义检索内容。
3. 用可切换的 LLM Provider 生成问答、解释和质量检查结果。
4. 保持推荐排序、食品安全、接口契约和测试可控。
5. 最后补一个轻量前端或演示界面，把 API 能力完整展示出来。

## 开发原则

- 后端优先，先保证 API、Agent、RAG、推荐和数据链路稳定，再做前端。
- 保持小步改动，优先替换 mock service，而不是大规模重写 Agent。
- API 层只负责请求响应和参数校验，业务逻辑继续放在 service、rag、recommender 和 agent 节点中。
- 所有外部依赖都通过配置切换，避免把 OpenAI、Ollama、Qdrant 地址、SQLite 路径写死在业务代码里。
- 食品安全规则必须有显式规则兜底，不能只依赖 LLM 判断。
- 每个阶段结束都要能运行 `cd backend && uv run pytest`。

## 里程碑 1：整理后端契约与文档

目标：先把现有后端能力、接口契约和已知问题讲清楚，避免后续开发方向漂移。

### 任务

- 修复或重写关键文档中的中文乱码，优先级：
  - `README.md`
  - `Plan.md`
  - `docs/RESUME_PROJECT.md`
  - `docs/TECHNICAL_ARCHITECTURE.md`
  - `docs/PROJECT_PLANNING.md`
- 对齐 API 返回结构，确认以下接口的输入输出字段是否稳定：
  - `POST /api/chat`
  - `POST /api/recommend/ingredients`
  - `GET /api/recommend/daily/{user_id}`
  - `GET /api/recipes/{recipe_id}`
  - `POST /api/history`
- 补充接口示例请求和示例响应。
- 标记哪些字段来自 mock，哪些字段未来来自 SQLite、Qdrant 或 LLM。

### 验收标准

- 文档能正常显示中文。
- 新开发者可以根据 README 启动后端、运行测试、调用 Swagger。
- API 契约在文档中有明确示例。

## 里程碑 2：SQLite 真实数据源接入

目标：把菜谱、食材、步骤、用户历史从 mock 数据推进到 SQLite。

### 任务

- 完善 SQLAlchemy 模型，建议覆盖：
  - `recipes`
  - `ingredients`
  - `recipe_ingredients`
  - `recipe_steps`
  - `recipe_substitutions`
  - `user_cooking_history`
  - `qa_logs`
- 完善数据库 session、初始化和 seed 流程。
- 准备第一批结构化菜谱数据，建议先控制在 10 到 20 道家常菜：
  - 番茄炒蛋
  - 酸辣土豆丝
  - 青椒肉丝
  - 可乐鸡翅
  - 蒜蓉西兰花
  - 红烧肉
  - 蛋炒饭
  - 麻婆豆腐
  - 清炒时蔬
  - 紫菜蛋花汤
- 将 `RecipeService` 从 mock 数据切换为数据库查询。
- 将 `UserMemoryService` 接入真实历史记录。
- 保留 mock fallback，方便测试和无数据库环境运行。

### 验收标准

- seed 后可以通过 API 查询真实菜谱。
- 推荐逻辑读取 SQLite 数据，而不是直接读取 mock 列表。
- 用户历史写入后可以影响每日推荐。
- 相关单元测试和集成测试通过。

## 里程碑 3：推荐服务增强

目标：让食材推荐和每日推荐更像真实产品逻辑，而不是简单关键字匹配。

### 任务

- 明确推荐评分公式，建议包含：
  - 食材匹配度
  - 缺失关键食材数量
  - 新手友好程度
  - 烹饪时间
  - 难度
  - 食材常见度
  - 季节适配
  - 用户历史偏好
  - 最近是否重复推荐
- 输出推荐解释字段：
  - 为什么推荐
  - 已匹配食材
  - 缺少食材
  - 可替代食材
  - 新手注意事项
- 增加过滤条件：
  - 最大烹饪时间
  - 难度
  - 是否新手友好
  - 排除不喜欢食材
- 为推荐排序补充测试，覆盖边界情况。

### 验收标准

- 输入一组食材后，结果排序稳定且可解释。
- 每日推荐能避开近期重复菜品。
- 测试能说明评分规则，不依赖随机输出。

## 里程碑 4：Qdrant 与 RAG 接入

目标：让菜谱问答从 mock 回答升级为真实检索增强生成。

### 任务

- 完善 `rag/chunks.py`，将结构化菜谱拆成可检索 chunk：
  - 菜品简介
  - 食材准备
  - 详细步骤
  - 新手注意事项
  - 常见失败原因
  - 替代食材
  - 安全提醒
- 完善 `seed_qdrant.py`，支持从 SQLite 读取菜谱并写入 Qdrant。
- 在配置中补齐：
  - Qdrant URL
  - collection name
  - embedding provider
  - embedding model
- 实现 RAG 检索服务：
  - query embedding
  - top-k 检索
  - metadata 过滤
  - source citation 输出
- 将 `recipe_qa_node` 接入 RAGService。
- 在无 Qdrant 或无 embedding 配置时，保持可解释降级。

### 验收标准

- “土豆丝怎么炒得脆？”能检索到土豆丝失败原因或技巧 chunk。
- API 返回包含来源信息。
- Qdrant 不可用时，接口返回明确错误或降级结果，而不是静默胡编。
- RAG 检索相关测试通过。

## 里程碑 5：LLM Provider 与质量检查

目标：接入真实 LLM，同时把输出质量和食品安全风险控制住。

### 任务

- 完善 `core/llm.py`，支持通过配置切换：
  - Ollama
  - OpenAI-compatible API
  - 关闭 LLM 的 mock 模式
- 为不同任务设计独立 prompt：
  - 意图识别
  - RAG 问答
  - 推荐解释
  - 质量检查
  - 答案修复
- 质量检查拆成两层：
  - 显式规则检查：危险操作、生熟交叉污染、过敏提醒、变质食材等。
  - LLM 检查：是否跑题、是否遗漏关键步骤、是否符合新手友好表达。
- Pydantic 校验 LLM 结构化输出，失败时给出 fallback。
- 记录 qa_logs，便于复盘问答质量。

### 验收标准

- 配置 Ollama 或 OpenAI-compatible API 后，`POST /api/chat` 能生成真实回答。
- 食品安全高风险内容能被规则拦截或提示。
- LLM 输出格式错误时不会导致接口 500。
- 质量检查和修复节点有可测试用例。

## 里程碑 6：Agent 工作流收敛

目标：让 LangGraph 流程保持可解释、可调试、可展示。

### 任务

- 梳理 `AgentState` 字段，区分：
  - 用户输入
  - 意图
  - 检索结果
  - 推荐结果
  - 质量检查结果
  - 最终回答
  - 执行轨迹
- 将 `nodes/_legacy.py` 中仍有价值的逻辑继续拆分到独立节点或服务。
- 为 Agent 执行过程输出 trace summary，便于前端展示：
  - 识别到的意图
  - 使用的数据源
  - 检索到的来源数量
  - 是否经过修复
- 限制质量检查修复循环次数，避免未来接入 LLM 后出现循环风险。
- 保持 `router.py` 等兼容 re-export，不破坏现有测试。

### 验收标准

- Agent 每次调用都能返回清晰执行摘要。
- 未知意图、RAG 问答、食材推荐、每日推荐四类路径都有集成测试。
- 质量检查不会无限循环。

## 里程碑 7：前端 MVP 或演示界面

目标：做一个能展示后端价值的轻量界面，不追求复杂产品化。

### 推荐方案

优先做一个 React 或 Streamlit MVP，选择标准是：

- 如果目标是简历项目展示和交互体验：优先 React。
- 如果目标是快速验证后端能力：优先 Streamlit。

### 首版页面

- 聊天问答页：
  - 输入问题
  - 显示回答
  - 显示引用来源
  - 显示 Agent 执行摘要
- 食材推荐页：
  - 输入已有食材
  - 设置时间、难度、新手友好过滤
  - 展示推荐卡片
- 每日推荐页：
  - 输入用户 ID
  - 展示今日推荐和推荐理由
- 菜谱详情页：
  - 展示食材、步骤、失败点、替代食材和新手提示

### 验收标准

- 前端只通过 FastAPI 调用后端。
- 后端不可用时前端有明确错误提示。
- 可以完成一条完整演示路径：提问、推荐、查看菜谱、记录历史、再次推荐。

## 里程碑 8：评估、演示和交付包装

目标：把项目整理成可以展示、复盘和继续扩展的状态。

### 任务

- 准备固定评估问题集：
  - 菜谱做法
  - 烹饪技巧
  - 失败原因
  - 替代食材
  - 食材推荐
  - 每日推荐
  - 食品安全
- 增加 demo 脚本，自动跑一组 API 示例。
- README 增加：
  - 项目背景
  - 架构图
  - 技术栈
  - 数据流
  - Agent 工作流
  - RAG 流程
  - 推荐逻辑
  - 本地运行方式
  - API 示例
  - 后续扩展方向
- 更新 `docs/RESUME_PROJECT.md`，提炼简历亮点。
- 准备截图或录屏材料。

### 验收标准

- 新环境按 README 可以启动后端并跑通 demo。
- 测试通过。
- 项目说明能清楚体现 FastAPI、LangGraph、RAG、SQLite、Qdrant、推荐系统和质量检查的分工。

## 建议执行顺序

1. 修复 `Plan.md`、`README.md` 和关键 docs 的乱码。
2. 先接 SQLite，让结构化菜谱和用户历史真实可用。
3. 增强推荐排序，形成不用 LLM 也稳定的核心业务能力。
4. 接 Qdrant 和 RAG，替换 mock 问答。
5. 接真实 LLM，并补齐质量检查和 fallback。
6. 收敛 Agent 状态、trace 和测试。
7. 做轻量前端或演示页面。
8. 做评估集、README、简历文档和演示材料。

## 最近下一步

建议下一次开发从 SQLite 接入开始，具体切入点：

1. 检查并补齐 `backend/src/kitchenpilot/db/models.py`。
2. 设计 seed 数据格式，先落 10 道菜。
3. 改造 `RecipeService`，让 `GET /api/recipes/{recipe_id}` 读取 SQLite。
4. 改造推荐服务，让 `POST /api/recommend/ingredients` 基于 SQLite 菜谱计算。
5. 为数据库查询和推荐排序补测试。

完成这一步后，项目就能从“后端骨架”进入“真实业务数据闭环”。
