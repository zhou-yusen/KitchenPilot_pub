# KitchenPilot 后端

后端负责提供 FastAPI 接口、LangGraph Agent 工作流、菜谱问答、统一推荐、Session memory、RAG 检索、质量检查、SQLite/seed 数据读取、Qdrant/LLM 集成。

当前版本是可演示的后端 MVP。菜谱数据来自 SQLite 或 seed JSON，推荐使用规则排序和 persona 画像，LLM/embedding 默认面向 Ollama，可在测试中显式切换 mock provider。

## 安装依赖

```powershell
uv sync --extra dev
```

## 启动服务

```powershell
uv run python script/start_backend.py
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

推荐使用 `script/start_backend.py` 启动服务，并按 `Esc` 停止。

如果需要按端口停止：

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

## RAG 评测

```powershell
# 快速验证（3 条）
uv run python evals/run_ragas_eval.py --limit 3 --collection recipe_chunks_split

# 全量评测（250 条，约 3-4 小时）
uv run python evals/run_ragas_eval.py --collection recipe_chunks_split
```

详见 [evals/README.md](evals/README.md)。

## 当前实现内容

- Agent 意图路由：`recipe_qa / recommendation / fallback`
- Session memory：追问识别、`active_recipe` 和 `rewritten_query`
- 菜谱问答 RAG：Qdrant 优先，本地检索 fallback
- 统一推荐：`ingredients / daily`
- 三类 persona：完全新手、入门用户、技艺高超的老手
- 安全检查和质量检查
- FastAPI 接口
- SQLite 数据模型和 seed 脚本
- Qdrant chunk seed/search

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
│   ├── services/         # 菜谱服务、安全检查、用户画像、session memory
│   └── seed/             # 初始化脚本和数据
├── evals/                # RAGAS 评测框架、测试集和报告
├── tests/                # 单元测试和集成测试
└── script/               # 可视化验证和本地辅助脚本
```

## 已知问题

- RAG prompt 和 source 引用仍可继续优化。
- 推荐仍是规则 MVP，不是生产级个性化推荐系统。
- 用户画像是三类预设 persona，尚未从真实长期行为学习。
- 前端定位是调试台，不是正式产品 UI。
