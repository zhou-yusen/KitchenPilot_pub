# KitchenPilot 前端

这是一个零构建的轻量演示前端，用于快速展示 KitchenPilot 后端能力。

## 使用方式

先启动后端：

```powershell
cd backend
uv run uvicorn kitchenpilot.main:app --reload
```

然后打开：

```text
frontend/index.html
```

也可以用前台静态服务打开。该方式会在终端显示访问链接，并且可以用 `Ctrl+C` 停止：

```powershell
cd frontend
.\start_frontend.ps1
```

默认访问：

```text
http://127.0.0.1:5173
```

如果端口被占用：

```powershell
.\start_frontend.ps1 -Port 5174
```

也可以直接使用 Python：

```powershell
cd frontend
python -m http.server 5173
```

访问：

```text
http://127.0.0.1:5173
```

## 当前能力

- 调用 `POST /api/chat` 展示菜谱问答。
- 展示 RAG sources 和 Agent execution trace。
- 调用 `POST /api/recommend/ingredients` 展示食材推荐。
- 调用 `GET /api/recommend/daily/{user_id}` 展示每日推荐。
- 支持修改 Backend Base URL，默认 `http://127.0.0.1:8000`。

## 边界

- 前端只通过 FastAPI 调用后端接口。
- 不直接访问 SQLite、Qdrant、LangGraph 或 LLM 客户端。
- 当前是 demo 页面，不包含登录、路由、构建流程或复杂状态管理。
