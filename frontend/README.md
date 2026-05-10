# KitchenPilot 前端

这是一个零构建的轻量调试前端，用于通过单聊天入口测试 KitchenPilot 后端能力。

## 使用方式

先启动后端：

```powershell
cd backend
uv run python script/start_backend.py
```

然后打开：

```text
frontend/index.html
```

也可以用 Python 前台静态服务打开。该方式会在终端显示访问链接，并且可以用 `Esc` 停止：

```powershell
cd frontend
python start_frontend.py
```

默认访问：

```text
http://127.0.0.1:5173
```

如果端口被占用：

```powershell
python start_frontend.py --port 5174
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

- 调用 `POST /api/chat` 作为唯一主入口。
- 使用 localStorage 保存 session 和 messages，支持新开对话、切换对话和删除对话。
- 支持三类用户画像选择：完全新手、入门用户、技艺高超的老手。
- 输入框支持 Enter 发送、Shift+Enter 换行，发送成功后清空。
- 展示 `intent`、`recommendation_type`、`active_recipe`、`rewritten_query`、recommendations、RAG sources 和 KitchenPilot trace。
- 展示 quality check 和 raw JSON，方便调试 Router/session memory 流程。
- 支持修改 Backend Base URL，默认 `http://127.0.0.1:8000`。

## 边界

- 前端只通过 FastAPI 调用后端接口。
- 不直接访问 SQLite、Qdrant、LangGraph 或 LLM 客户端。
- 当前是 demo 页面，不包含登录、路由、构建流程或复杂状态管理。
