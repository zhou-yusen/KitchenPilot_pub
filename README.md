# KitchenPilot

KitchenPilot 是一个面向厨房新手的个性化菜谱 Agentic RAG 助手。项目采用前后端分离的 monorepo 结构，当前以后端 MVP 和轻量前端 demo 为主，先跑通 API、Agent 流程、菜谱问答、食材推荐、RAG 来源展示和质量检查链路。

## 当前状态

项目目前处于 **后端 MVP + 轻量前端 demo 阶段**。

已经具备：

- FastAPI 后端工程
- LangGraph Agent 主流程
- SQLite 菜谱数据读取，数据库不可用时 fallback mock 数据
- Qdrant RAG seed/search 和本地关键词 fallback
- 食材推荐与每日推荐接口
- 简单安全检查与质量检查
- 轻量静态前端 demo
- 后端单元测试和集成测试

尚未完成：

- RAG 回答质量深度优化
- 推荐个性化增强
- 正式前端工程化
- 中文乱码修复

## 项目结构

```text
KitchenPilot/
├── backend/              # FastAPI、Agent、RAG、推荐、数据库层
├── frontend/             # 前端占位目录
├── docs/                 # 项目规划和架构文档
├── docker-compose.yml
├── Plan.md
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
- `POST /api/recommend/ingredients`
- `GET /api/recommend/daily/{user_id}`
- `GET /api/recipes/{recipe_id}`
- `POST /api/history`

## 测试

```powershell
cd backend
uv run pytest
```

## 文档

- [项目规划](docs/PROJECT_PLANNING.md)
- [技术架构](docs/TECHNICAL_ARCHITECTURE.md)
- [简历项目说明](docs/RESUME_PROJECT.md)
- [实现计划](Plan.md)
