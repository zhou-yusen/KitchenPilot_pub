# KitchenPilot

KitchenPilot 是一个面向厨房新手的个性化菜谱 Agentic RAG 助手。项目采用 FastAPI + LangGraph + SQLite + Qdrant 构建后端能力，支持自然语言意图路由、菜谱问答、RAG 来源追踪、食材推荐、每日推荐和多轮 session memory。

## 核心能力

- FastAPI 后端接口：chat、recommendations、recipes、history、health
- Router-based LangGraph workflow：支持 `recipe_qa / recommendation / fallback`
- SQLite/seed 菜谱数据读取，数据库异常时回落到 seed JSON
- Qdrant RAG seed/search，本地关键词检索 fallback，按问题类型轻量 rerank
- Session memory：支持 `session_id`、`active_recipe`、`rewritten_query` 和多轮追问消解
- 统一推荐接口：`recommendation_type = ingredients / daily`
- 三类 persona 推荐：完全新手、入门用户、熟练用户
- 质量检查、安全提醒和答案修复节点
- 零构建前端调试台：单聊天入口、session 管理、sources、trace、raw JSON 可视化
- 后端单元测试、集成测试和 RAG 评估数据集

## 技术栈

- Python / FastAPI
- LangGraph
- SQLite / SQLAlchemy
- Qdrant
- Pydantic
- Ollama 或 OpenAI-compatible LLM / Embedding provider
- 原生 HTML/CSS/JavaScript 调试前端

## 项目结构

```text
KitchenPilot/
├── backend/              # FastAPI、Agent、RAG、推荐、数据库层
├── frontend/             # 单聊天入口调试前端
├── docs/                 # 技术文档
├── docker-compose.yml
└── README.md
```

## 后端快速启动

```powershell
cd backend
uv sync
uv run python script/start_backend.py
```

启动后打开接口文档：

```text
http://127.0.0.1:8000/docs
```

## 前端快速启动

后端运行后，直接打开：

```text
frontend/index.html
```

也可以启动静态文件服务：

```powershell
cd frontend
python start_frontend.py
```

然后访问：

```text
http://127.0.0.1:5173
```

健康检查：

```text
http://127.0.0.1:8000/health
```

如果需要强制停止 8000 端口上的后端进程，可以在 `backend` 目录执行：

```powershell
.\script\stop_backend.ps1
```

推荐使用 `script/start_backend.py` 启动后端；该脚本支持在终端按 `Esc` 停止服务。

开发时如果需要自动重载，也可以使用：

```powershell
uv run uvicorn kitchenpilot.main:app --reload
```

## 主要接口

- `GET /health`
- `POST /api/chat`
- `POST /api/recommend`
- `GET /api/recipes/{recipe_id}`
- `POST /api/history`

## 测试

```powershell
cd backend
uv run pytest
```

## 文档

- [技术架构](docs/TECHNICAL_ARCHITECTURE.md)
- [RAG 技术细节](docs/RAG_TECHNICAL_DETAILS.md)
- [意图识别技术细节](docs/INTENT_ROUTER_TECHNICAL_DETAILS.md)

## 评测

项目使用 RAGAS 框架对 RAG 系统进行端到端评测，测试集 250 条，覆盖 9 种问题类型。

```powershell
cd backend
uv run python evals/run_ragas_eval.py --limit 3 --collection recipe_chunks_split
```

详见 [evals/README.md](backend/evals/README.md)。
