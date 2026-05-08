# KitchenPilot 标准前后端分离实现计划

## Summary

采用前后端分离的 monorepo 结构，后端先作为核心开发对象，前端暂时只保留独立目录，后续再决定 Streamlit、React 或其他方案。

后端使用标准 Python 工程结构：`uv + pyproject.toml + src layout + tests`。LangChain 能直接提供的接口优先直接使用，例如 `ChatOllama`、`ChatOpenAI`、Embedding、Retriever、Qdrant VectorStore，不额外重写 LangChain 底层接口。

## Project Structure

```text
KitchenPilot/
├── backend/
│   ├── pyproject.toml
│   ├── README.md
│   ├── .env.example
│   ├── src/
│   │   └── kitchenpilot/
│   │       ├── main.py
│   │       ├── api/
│   │       ├── agent/
│   │       ├── core/
│   │       ├── db/
│   │       ├── rag/
│   │       ├── recommender/
│   │       ├── schemas/
│   │       ├── services/
│   │       └── seed/
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/
│   └── README.md
├── docs/
│   ├── PROJECT_PLANNING.md
│   ├── TECHNICAL_ARCHITECTURE.md
│   └── RESUME_PROJECT.md
├── docker-compose.yml
├── Plan.md
└── README.md
```

## Implementation Plan

### 第一阶段：Agent 核心流程

- 初始化 `backend/` 为标准 Python 项目，使用 `uv + pyproject.toml` 管理依赖。
- 使用 `src/kitchenpilot/` 作为后端源码根目录。
- 基于 LangGraph 搭建核心 Agent 流程：
  - 用户输入解析
  - 用户历史加载
  - 意图识别 Router
  - 菜谱问答子图
  - 食材推荐子图
  - 每日推荐子图
  - 质量检查节点
  - 答案修复节点
- 第一阶段使用 mock 数据和 mock service，先跑通完整 Agent 状态流转。
- 定义 `AgentState`、意图枚举、推荐结果、质量检查结果等 Pydantic Schema。

### 第二阶段：RAG + 推荐工具

- 直接使用 LangChain 官方接口实现模型和检索能力。
- LLM 调用优先使用：
  - 本地模型：`langchain-ollama` 的 `ChatOllama`
  - 在线模型：`langchain-openai` 的 `ChatOpenAI`
- Embedding 调用优先使用 LangChain 已支持的 embedding 类，不重写底层接口。
- 实现 `rag/` 模块：
  - chunk 构造
  - retriever 封装
  - RAG prompt
  - 带来源回答生成
- 实现 `recommender/` 模块：
  - 食材匹配
  - 缺失食材计算
  - 难度、耗时、新手友好度排序
  - 用户历史去重
- 实现安全和质量检查。

### 第三阶段：SQLite + Qdrant 工程化

- 使用 SQLAlchemy 管理 SQLite 数据模型。
- SQLite 存储菜谱、食材、步骤、用户历史和问答日志。
- 使用 Qdrant 存储向量数据。
- 直接使用 LangChain Qdrant VectorStore 或官方 Qdrant 客户端，不自建向量检索协议。
- 提供 seed 脚本初始化家常菜数据、用户历史样例、RAG chunk 和 embedding。
- 第三阶段结束时，将 mock service 替换为真实 SQLite + Qdrant 数据源。

### 第四阶段：FastAPI 后端

- 在 `api/` 中实现后端接口。
- 初版接口：
  - `POST /api/chat`
  - `POST /api/recommend/ingredients`
  - `GET /api/recommend/daily/{user_id}`
  - `GET /api/recipes/{recipe_id}`
  - `POST /api/history`
- API 层只负责请求响应和参数校验，不直接写推荐、RAG 或 Agent 逻辑。
- 返回结果包含最终回答、意图类型、推荐菜品、引用来源、质量检查结果和 Agent 执行摘要。

### 第五阶段：前端展示

- 前端架构后续再决定，当前只保留 `frontend/` 独立目录。
- 初版前端目标只定义能力，不锁定技术。
- 前端必须通过 FastAPI 调用后端，不直接访问数据库、Qdrant 或 LangGraph。

### 第六阶段：评估、部署、README 包装

- 准备评估问题集，覆盖菜谱问答、技巧解释、失败原因、替代食材、食材推荐、每日推荐和安全检查。
- 编写 Router、推荐排序、RAG 检索、API 和安全检查测试。
- 使用 Docker Compose 管理 Qdrant，后续可加入 backend 和 frontend。
- README 展示项目背景、技术架构、Agent 工作流、SQLite + Qdrant 分工、RAG 流程、推荐逻辑、API 示例和简历亮点。

## Test Plan

- 单元测试覆盖：
  - `AgentState` 数据校验
  - 意图识别 Router
  - 推荐排序规则
  - 安全检查规则
  - RAG prompt 输入输出格式
- 集成测试覆盖：
  - Agent 从用户输入到最终回答的完整流程
  - SQLite 查询与推荐服务联动
  - Qdrant 检索与 RAG 回答生成
  - FastAPI 接口请求响应
- 手动演示用例：
  - “土豆丝怎么炒得脆？”
  - “我有鸡蛋、番茄、土豆，推荐一道简单菜。”
  - “没有生抽可以用什么替代？”
  - “新手做红烧肉要注意什么？”
  - “给我一个今日推荐。”

## Assumptions

- 后端项目管理使用 `uv + pyproject.toml`。
- 项目采用前后端分离 monorepo。
- 前端架构暂不决定，只预留独立目录和接口边界。
- LangChain 能直接提供的接口优先直接使用，不重写底层 OpenAI 或 Ollama 调用。
- 本地模型优先使用 `ChatOllama`；如需 OpenAI-compatible 方式，再通过配置 `base_url` 接入 Ollama。
- MVP 暂不实现一周菜单规划和菜谱录入。

