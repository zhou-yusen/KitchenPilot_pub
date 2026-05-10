# KitchenPilot Demo Guide

本文用于快速演示当前 MVP。演示目标是展示：自然语言入口、Router 路由、RAG 问答、session memory、个性化推荐和调试面板。

## 1. 启动

后端：

```powershell
cd backend
uv run python script/start_backend.py
```

前端：

```powershell
cd frontend
python start_frontend.py
```

默认地址：

```text
后端文档：http://127.0.0.1:8000/docs
前端调试台：http://127.0.0.1:5173
```

两个启动脚本都支持按 `Esc` 停止。

## 2. 演示问题

### 菜谱问答

输入：

```text
土豆丝怎么炒得脆？
```

预期：

- `intent = recipe_qa`
- 右侧展示 RAG sources
- trace 中出现 RAG 检索和质量检查

### 多轮追问

同一个 session 中依次输入：

```text
咸蛋黄鸡翅怎么做？只告诉我步骤就好，不要太多的符号
```

再输入：

```text
料酒和生抽要下多少？还需要别的调料吗？
```

预期：

- 第二轮 `is_follow_up = true`
- `active_recipe = 咸蛋黄鸡翅`
- `rewritten_query` 包含菜名
- 仍走 `recipe_qa`，不会误判成推荐

### 食材推荐

输入：

```text
我有鸡翅，推荐一道菜
```

预期：

- `intent = recommendation`
- `recommendation_type = ingredients`
- 推荐结果包含鸡翅相关菜，例如可乐鸡翅或板栗鸡翅煲

### Persona 推荐

切换用户画像为“完全新手”，输入：

```text
推荐一道菜
```

预期偏向：

```text
番茄炒蛋、蛋炒饭、酸辣土豆丝
```

切换用户画像为“技艺高超的老手”，输入同样问题。

预期偏向：

```text
番茄牛腩炖土豆、芥末罗氏虾、白灼虾
```

### Fallback 澄清

新 session 中输入：

```text
用不用下盐？
```

预期：

- 没有上下文时进入 `fallback`
- 系统询问“你是在追问哪道菜？”

## 3. 调试面板看点

- `intent`：顶层路由结果
- `recommendation_type`：推荐子类型
- `session_id`：当前对话
- `active_recipe`：当前 session 正在讨论的菜
- `rewritten_query`：追问改写后的完整问题
- `execution_trace`：LangGraph 节点执行过程
- `sources`：RAG 证据
- `raw JSON`：完整 API 响应

## 4. 回归验证

```powershell
cd backend
uv run pytest
```

前端语法检查：

```powershell
node --check frontend/app.js
```

## 5. 简历表述边界

可以表述为：

> 基于 FastAPI + LangGraph + Qdrant 的 Agentic RAG 食谱问答与个性化推荐 MVP，支持自然语言路由、可溯源问答、多轮追问消解、规则推荐排序和调试可视化。

不建议表述为：

> 生产级个性化推荐系统。
