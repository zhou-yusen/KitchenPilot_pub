# KitchenPilot 后端

后端负责提供 FastAPI 接口、Agent 工作流、菜谱问答、食材推荐、质量检查，以及后续的 SQLite / Qdrant / LLM 集成。

当前版本主要是 mock 数据驱动的后端 MVP，用于验证接口和 Agent 流程。

## 安装依赖

```powershell
uv sync --extra dev
```

## 启动服务

```powershell
uv run uvicorn kitchenpilot.main:app --reload
```

启动后访问接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```text
http://127.0.0.1:8000/health
```

## 停止服务

正常情况下可以用 `Ctrl+C` 停止服务。

如果 Windows 下 `Ctrl+C` 无法停止 `uvicorn --reload`，可以按端口停止：

```powershell
.\script\stop_backend.ps1
```

自定义端口：

```powershell
.\script\stop_backend.ps1 -Port 8001
```

## 测试

```powershell
uv run pytest
```

## 当前实现内容

- Agent 意图路由
- 菜谱问答 mock 流程
- 食材推荐 mock 流程
- 每日推荐 mock 流程
- 安全检查和质量检查
- FastAPI 接口
- SQLite 数据模型预留
- Qdrant 检索服务预留
- seed 脚本预留

## 目录结构

```text
backend/
├── src/kitchenpilot/
│   ├── api/              # FastAPI 路由
│   ├── agent/            # Agent 状态、图、节点
│   ├── core/             # 配置和 LLM 客户端
│   ├── db/               # 数据库模型和会话
│   ├── rag/              # RAG 检索和问答
│   ├── recommender/      # 推荐逻辑
│   ├── schemas/          # 请求响应和业务 schema
│   ├── services/         # mock 数据、安全检查、用户记忆
│   └── seed/             # 初始化脚本
├── tests/                # 单元测试和集成测试
└── script/               # 可视化验证和本地辅助脚本
```

## 已知问题

- 中文字符串目前存在乱码，需要修复编码和测试数据。
- RAG、数据库、LLM 仍处于骨架或 mock 阶段。
- 前端尚未实现。
