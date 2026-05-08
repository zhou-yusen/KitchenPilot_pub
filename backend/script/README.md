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
