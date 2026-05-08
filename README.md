# KitchenPilot

KitchenPilot 是一个面向厨房新手的个性化菜谱 Agentic RAG 助手。项目采用前后端分离的 monorepo 结构，当前以后端原型为主，先跑通 API、Agent 流程、菜谱问答、食材推荐和质量检查链路。

## 当前状态

项目目前处于 **后端 MVP 骨架 + mock 数据闭环阶段**。

已经具备：

- FastAPI 后端工程骨架
- LangGraph Agent 主流程
- mock 菜谱数据
- mock RAG 问答服务
- 食材推荐与每日推荐接口
- 简单安全检查与质量检查
- SQLite / Qdrant 工程化预留
- 后端单元测试和集成测试
- 前端占位目录

尚未完成：

- 真实 SQLite 数据源接入主链路
- 真实 Qdrant 向量检索
- 真实 LLM 回答生成
- 前端页面实现
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
uv run uvicorn kitchenpilot.main:app --reload
```

启动后打开接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/health
```

如果 Windows 下 `Ctrl+C` 无法停止后端，可以在 `backend` 目录执行：

```powershell
.\script\stop_backend.ps1
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
