# KitchenPilot

KitchenPilot 是一个面向厨房新手的个性化食谱 Agentic RAG 助手。项目采用前后端分离的 monorepo 结构，后端以 LangGraph、LangChain、FastAPI、SQLite 和 Qdrant 为核心。

## Current Status

当前仓库已包含：

- 标准后端工程骨架：`backend/src/kitchenpilot`
- mock 版 LangGraph Agent 主流程
- mock RAG、推荐和安全检查服务
- FastAPI 初版接口
- SQLite / Qdrant 工程化占位
- 前端独立目录占位
- 项目规划、技术选型和简历写法文档

## Repository Layout

```text
KitchenPilot/
├── backend/        # FastAPI, Agent, RAG, recommender, DB layer
├── frontend/       # Frontend placeholder
├── docs/           # Planning and resume docs
├── docker-compose.yml
├── Plan.md
└── README.md
```

## Backend Quick Start

```powershell
cd backend
uv sync
uv run uvicorn kitchenpilot.main:app --reload
```

If `uv` is not installed:

```powershell
pip install uv
```

## API Preview

- `POST /api/chat`
- `POST /api/recommend/ingredients`
- `GET /api/recommend/daily/{user_id}`
- `GET /api/recipes/{recipe_id}`
- `POST /api/history`

## Docs

- [项目规划](docs/PROJECT_PLANNING.md)
- [技术选型与架构规划](docs/TECHNICAL_ARCHITECTURE.md)
- [简历项目写法](docs/RESUME_PROJECT.md)
- [实现计划](Plan.md)

