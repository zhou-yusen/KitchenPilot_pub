# 可视化验证脚本

这个目录用于存放后端开发过程中的 Python 可视化验证脚本、本地演示脚本和少量辅助脚本。

这些脚本不属于生产代码，也不属于自动化测试。生产代码放在 `src/`，自动化测试放在 `tests/`。

这些 Python 接口验证脚本会显式绕过系统代理，避免本地 `127.0.0.1:8000` 请求被代理转发后出现 `502 Bad Gateway`。

## 接口可视化验证

先启动后端：

```powershell
uv run uvicorn kitchenpilot.main:app --reload
```

测试聊天接口：

```powershell
uv run python script/test_chat.py
```

测试食材推荐接口：

```powershell
uv run python script/test_recommendation.py
```

串联验证健康检查、聊天、食材推荐和每日推荐：

```powershell
uv run python script/demo_api_flow.py
```

## 本地 Agent 验证

不启动 HTTP 服务，直接调用 `KitchenPilotAgent`：

```powershell
uv run python script/mytest.py
```

## Provider 直连验证

填入 `.env` 中的 `MIMO_API_KEY` 后，先用最小聊天脚本验证 MiMo 鉴权和返回内容：

```powershell
uv run python script/chat_mimo_loop.py
```

该脚本不依赖 FastAPI、Qdrant 或 Agent 图。MiMo 只负责 chat 时，RAG/Router 仍需要通过 `EMBEDDING_PROVIDER` 配置 Ollama 或 OpenAI embedding。

## HTML 菜谱抽取

从 `script/data/preview_fixed_clickable_links.html` 重建 SQLite/RAG 可直接读取的结构化菜谱 JSON：

```powershell
uv run python script/extract_recipe_preview_html.py
```

默认输出到 `src/kitchenpilot/seed/data/recipes_extracted.json`。也可以通过 `--html` 和 `--output` 指定路径。

## 停止本地后端

Windows 下使用 `uvicorn --reload` 时，可能出现 `Ctrl+C` 无法干净停止后端的情况。可以使用下面的 PowerShell 脚本按端口停止服务：

```powershell
.\script\stop_backend.ps1
```

默认停止 `8000` 端口。

如果后端运行在其他端口：

```powershell
.\script\stop_backend.ps1 -Port 8001
```
