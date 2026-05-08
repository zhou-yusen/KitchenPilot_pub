# KitchenPilot 后续开发计划

## 当前状态

KitchenPilot 已经从 FastAPI 后端骨架推进到可运行的后端 MVP：

- FastAPI API、LangGraph Agent 主流程、Recipe/Recommendation/History 基础接口已具备。
- SQLite 初始菜谱数据、JSON loader、SQLite seed 和 `RecipeService` 数据库读取已接入。
- LLM chat 与 embedding provider 已拆分为独立接口，支持 Ollama 与 OpenAI-compatible API。
- 意图识别已支持规则、embedding 相似度和低置信度 LLM fallback。
- unknown 意图已支持澄清问题，避免模糊输入被强行路由。
- 菜谱已按 `overview / ingredients / step / failure / substitution / safety` 六类生成语义 chunk。
- 当前 RAG 问答仍保留本地关键词检索 fallback，下一阶段重点是打通 Qdrant 向量检索闭环。

## 下一步目标

下一阶段目标是完成 **Qdrant RAG 最小闭环**：

1. 从 SQLite/RecipeService 读取菜谱。
2. 派生语义 chunk。
3. 使用 embedding provider 批量生成向量。
4. 写入 Qdrant collection。
5. RAGService 优先从 Qdrant 检索 source chunks。
6. Qdrant 不可用时降级到本地关键词检索。
7. LLM 基于检索到的 source chunks 生成可溯源回答。

## 里程碑

### 里程碑 1：Qdrant Seed 闭环

- 使用 `build_recipe_chunks()` 生成所有菜谱 chunk。
- 使用 `build_embedding_provider()` 批量生成 embedding。
- 创建或复用 `QDRANT_COLLECTION`。
- upsert chunk vector 和 payload。
- payload 至少包含 `recipe_id`、`recipe_name`、`chunk_type`、`content`、`metadata`。

验收标准：

- seed 脚本能输出生成 chunk 数和 upsert 数。
- Qdrant collection 可被检测到。
- chunk point id 稳定，可重复 upsert。

### 里程碑 2：RAGService 优先查 Qdrant

- `RAGService.retrieve()` 优先执行 query embedding + Qdrant search。
- Qdrant 返回结果转换为 `SourceChunk`。
- 每个 source 包含 score 和 retrieval source metadata。
- Qdrant 或 embedding 不可用时自动降级本地检索。

验收标准：

- “土豆丝怎么炒得脆？”能命中 `failure` 或相关 `step` chunk。
- “没有蚝油怎么办？”能命中 `substitution` chunk。
- “白灼虾怎么处理安全？”能命中 `safety` chunk。
- Qdrant 未启动时 API 不返回 500。

### 里程碑 3：RAG 问答质量增强

- 优化 RAG prompt，使回答明确引用检索依据。
- 控制 source 数量，避免同一道菜过度占用上下文。
- 为失败排查、替代食材、安全提醒问题增加检索测试。
- 保留规则安全检查作为兜底，不完全依赖 LLM。

验收标准：

- `POST /api/chat` 返回 answer、sources、execution_trace。
- 回答能基于 sources 解释步骤、失败原因、替代方案或安全提醒。
- LLM 调用失败时仍能返回基于 source 的模板化 fallback。

### 里程碑 4：推荐服务增强

- 明确推荐评分公式。
- 加入时间、难度、新手友好、历史偏好、近期重复等因素。
- 推荐解释保持规则可解释，LLM 只用于自然语言润色。

验收标准：

- 食材推荐排序稳定。
- 每日推荐能避开近期重复菜品。
- 推荐结果包含已匹配食材、缺少食材和推荐理由。

### 里程碑 5：演示与交付

- 补充 demo 脚本展示 Qdrant seed、RAG retrieve、API chat。
- 更新 README 和关键 docs。
- 之后再决定是否实现轻量前端。

验收标准：

- 新环境按 README 可以启动后端、seed 数据、seed Qdrant、运行 demo。
- `cd backend && uv run pytest` 通过。
- 项目说明能清楚体现 FastAPI、LangGraph、SQLite、Qdrant、LLM、Embedding 和 RAG 的分工。

## 最近下一步

当前最近下一步是继续完善 Qdrant RAG：

1. 用真实 Ollama embedding 模型确认 seed 写入 Qdrant 成功。
2. 用 `demo_qdrant_rag.py --seed` 跑通 chunk upsert。
3. 用示例问题验证 Qdrant 检索结果是否优于本地关键词检索。
4. 根据检索效果再决定是否增加简单 rerank。

## 运行与验证

常用命令：

```powershell
cd backend
uv run python -m kitchenpilot.seed.seed_sqlite
uv run python -m kitchenpilot.seed.seed_qdrant
uv run python script/preview_recipe_chunks.py
uv run python script/demo_qdrant_rag.py --seed
uv run pytest
```
