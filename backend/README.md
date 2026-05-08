# KitchenPilot Backend

KitchenPilot 后端负责 FastAPI 接口、LangGraph Agent 工作流、RAG 检索、推荐排序、SQLite 结构化数据和 Qdrant 向量数据。

## Setup

```powershell
uv sync --extra dev
uv run uvicorn kitchenpilot.main:app --reload
```

## Environment

Copy `.env.example` to `.env` and adjust values when using real LLM or vector database services.

## Current Implementation

当前版本先实现 mock 数据闭环：

- Agent Router
- 菜谱问答
- 食材推荐
- 每日推荐
- 安全和质量检查
- FastAPI 接口

SQLite 和 Qdrant 模块已经预留，后续可以把 mock service 替换为真实数据源。

