# KitchenPilot RAG 技术细节

本文记录 KitchenPilot 当前 RAG 链路的工程实现，重点说明食谱数据如何切分为 chunk、如何写入 Qdrant、如何召回和重排，以及 Qdrant 或 LLM 不可用时如何降级。

## 1. RAG 在系统中的位置

RAG 负责菜谱问答类问题，包括做法步骤、失败原因、替代食材和安全提醒。用户请求进入 FastAPI 后，由 LangGraph Router 判断为 `recipe_qa`，再进入 `recipe_qa_node` 调用 `RAGService.answer()`。

当前主链路：

```text
用户问题
-> Intent Router 判断为 recipe_qa
-> recipe_qa_node
-> RAGService.retrieve()
-> Qdrant 向量检索或本地关键词 fallback
-> 轻量 rerank
-> RAGService.answer()
-> LLM 基于 sources 生成回答，或使用 source-based 模板回答
-> 返回 answer + sources + execution_trace
```

相关代码：

- `backend/src/kitchenpilot/agent/nodes/recipe_qa_node.py`
- `backend/src/kitchenpilot/rag/service.py`
- `backend/src/kitchenpilot/rag/chunks.py`
- `backend/src/kitchenpilot/rag/qdrant_store.py`

## 2. 数据来源

RAG 的原始数据来自 `RecipeService().list_recipes()`。

`RecipeService` 优先读取 SQLite：

- `recipes`
- `recipe_ingredients`
- `recipe_steps`
- `recipe_failures`
- `recipe_substitutions`
- `recipe_safety_notes`

如果 SQLite 不可用、查询异常或检测到坏数据，则回退到 seed JSON：

```text
backend/src/kitchenpilot/seed/data/recipes_initial.json
```

最终进入 RAG 的统一数据结构是 Pydantic `Recipe` schema，核心字段包括：

- `id`
- `name`
- `description`
- `difficulty`
- `time_minutes`
- `beginner_friendly`
- `cuisine`
- `seasons`
- `ingredients`
- `steps`
- `common_failures`
- `substitutions`
- `safety_notes`

这层设计让 RAG 不直接依赖数据库表结构，而是依赖稳定的业务 schema。

## 3. Chunk 切分策略

chunk 生成入口是：

```python
build_recipe_chunks(recipes: list[Recipe]) -> list[SourceChunk]
```

当前每道菜会被切成六类语义 chunk：

| chunk_type | 数量策略 | 作用 |
| --- | --- | --- |
| `overview` | 每道菜 1 条 | 支持菜名、难度、耗时、新手友好等概览型问题 |
| `ingredients` | 每道菜 1 条 | 支持已有食材、缺失食材、食材清单相关问题 |
| `step` | 每个步骤 1 条 | 支持“怎么做”“火候”“步骤顺序”等问题 |
| `failure` | 每个常见失败点 1 条 | 支持“为什么失败”“太甜”“不脆”“腥味”等问题 |
| `substitution` | 每个替代项 1 条 | 支持“没有某食材怎么办”“能不能替代”等问题 |
| `safety` | 每条安全提醒 1 条 | 支持“怎么处理安全”“熟没熟”“烫伤风险”等问题 |

这种切法不是按固定字数切分，而是按食谱业务结构切分。原因是做菜问题通常有明确意图：问步骤、问失败、问替代、问安全时，需要优先命中对应类型的知识片段。

### 3.1 Chunk 内容格式

每个 chunk 的 `content` 是面向检索和 LLM 上下文的中文文本，包含菜名、类型和当前 chunk 的核心内容。

示例：`step` chunk 会包含：

```text
菜谱：番茄炒蛋
类型：制作步骤
步骤 3：热锅倒油，倒入蛋液，炒到刚凝固成大块后盛出。
新手提示：鸡蛋不要炒到完全干硬，后面还会回锅。
风险提示：倒蛋液前确认锅中没有明显水分，避免热油飞溅。
相关食材：番茄、鸡蛋、小葱、蒜、食用油、盐、白糖
```

示例：`substitution` chunk 会包含：

```text
菜谱：番茄炒蛋
类型：食材替代
原食材：小葱
替代方案：可用香菜或不放。
```

### 3.2 Chunk 元数据

每个 `SourceChunk` 除了 `content` 外，还带有稳定 metadata：

```json
{
  "chunk_id": "recipe:1:step:3:v1",
  "content_hash": "...",
  "schema_version": 1,
  "difficulty": "easy",
  "beginner_friendly": true,
  "time_minutes": 15,
  "cuisine": "家常菜",
  "seasons": ["spring", "summer", "autumn", "winter"],
  "ingredients": ["番茄", "鸡蛋", "小葱", "蒜", "食用油", "盐", "白糖"],
  "step_order": 3
}
```

关键设计：

- `chunk_id`：由菜谱 ID、chunk 类型、序号和 schema version 组成，用于生成稳定 Qdrant point id。
- `content_hash`：对 chunk 文本做 SHA-256，用于后续判断内容是否变化。
- `schema_version`：当前为 `1`，后续调整 chunk 结构时可以升级。
- `difficulty / beginner_friendly / time_minutes / ingredients`：保留结构化属性，后续可用于 Qdrant payload filter 或结果解释。
- `step_order / failure_order / substitution_order / safety_order`：保留原始业务顺序。

## 4. Qdrant 存储方法

Qdrant 存储的是 chunk embedding 和 payload。当前 collection 名默认是：

```text
recipe_chunks
```

配置来自 `Settings`：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `qdrant_url` | `http://localhost:6333` | Qdrant 服务地址 |
| `qdrant_collection` | `recipe_chunks` | collection 名称 |
| `qdrant_vector_size` | `1024` | 默认向量维度 |
| `qdrant_timeout` | `5.0` | 请求超时 |
| `rag_use_qdrant` | `True` | 是否优先使用 Qdrant |

### 4.1 Point id

Qdrant point id 由 `chunk_id` 通过 UUID v5 生成：

```python
uuid5(NAMESPACE_URL, chunk_id)
```

这样同一个 chunk 重复 seed 时 point id 不变，可以重复 upsert，不会因为每次生成随机 ID 导致重复数据膨胀。

### 4.2 Payload 结构

写入 Qdrant 的 payload 结构如下：

```json
{
  "recipe_id": 1,
  "recipe_name": "番茄炒蛋",
  "chunk_type": "step",
  "content": "菜谱：番茄炒蛋\n类型：制作步骤\n步骤 3：...",
  "metadata": {
    "chunk_id": "recipe:1:step:3:v1",
    "content_hash": "...",
    "schema_version": 1,
    "difficulty": "easy",
    "beginner_friendly": true,
    "time_minutes": 15,
    "cuisine": "家常菜",
    "seasons": ["spring", "summer", "autumn", "winter"],
    "ingredients": ["番茄", "鸡蛋"]
  }
}
```

payload 的作用：

- 返回给前端作为 RAG sources。
- 给 LLM answer prompt 提供上下文。
- 支持后续做 metadata filter，例如只查某道菜、某类 chunk、某些食材或新手友好菜。

当前代码已保存 metadata，但实际查询暂未使用 Qdrant filter，主要走向量召回后再轻量 rerank。

## 5. Seed 和 Upsert 流程

Qdrant seed 入口：

```powershell
cd backend
uv run python -m kitchenpilot.seed.seed_qdrant
```

内部流程：

```text
RecipeService.list_recipes()
-> build_recipe_chunks(recipes)
-> embedding_provider.embed([chunk.content])
-> ensure_collection(vector_size)
-> chunk_to_point(chunk, vector)
-> Qdrant upsert
```

`QdrantRecipeStore.upsert_chunks()` 会按 batch 处理，默认 `batch_size=32`。

collection 创建策略：

- 如果 collection 已存在，直接复用。
- 如果不存在，用第一批 embedding 的向量维度创建 collection。
- 距离函数使用 `COSINE`。

当前 embedding provider 支持：

- Ollama embedding
- OpenAI-compatible embedding
- Mock embedding，用于测试

## 6. 查询和召回流程

RAG 查询入口：

```python
RAGService.retrieve(query: str, top_k: int = 4)
```

### 6.1 优先 Qdrant 语义检索

当 `settings.rag_use_qdrant=True` 时，系统优先调用：

```python
QdrantRecipeStore.search(query, top_k)
```

流程：

```text
用户 query
-> embedding_provider.embed([query])
-> Qdrant query_points(collection, vector, limit=top_k, with_payload=True)
-> source_chunk_from_payload(payload, score)
-> SourceChunk[]
```

返回的每个 `SourceChunk` 会带上：

```json
{
  "retrieval_source": "qdrant"
}
```

### 6.2 本地关键词 fallback

如果以下任一情况发生，会降级到本地检索：

- `rag_use_qdrant=False`
- Qdrant 服务不可用
- embedding 调用失败
- Qdrant 查询异常
- Qdrant 返回空结果

本地 fallback 使用启动时生成的 `_chunks`，即：

```python
self._chunks = build_recipe_chunks(self.recipe_service.list_recipes())
```

本地评分逻辑：

- 将 query 拆成英文/数字 token 和中文单字集合。
- 对 chunk 的 `recipe_name + content` 做同样拆分。
- 计算交集数量作为基础分。
- 如果菜名直接出现在 query 中，加 5 分。
- 如果问题和内容同时包含关键烹饪词，加 2 分。

当前增强关键词包括：

```text
脆、替代、失败、太甜、新手、注意、怎么做、安全
```

本地检索返回的 metadata 会带：

```json
{
  "retrieval_source": "local"
}
```

这保证 Qdrant 或 embedding 不可用时，API 不会直接 500，仍能返回基于本地 source chunks 的答案。

## 7. 轻量 Rerank 策略

Qdrant 的原始向量分数不一定能精确区分“用户到底在问步骤、替代、失败还是安全”。因此 `RAGService.retrieve()` 在 Qdrant 或本地召回后都会执行 `_rerank()`。

当前 rerank 不是模型 rerank，而是基于中文关键词的 chunk type 优先级调整。

| 问题线索 | 优先 chunk_type |
| --- | --- |
| `没有`、`替代`、`代替`、`换成`、`可不可以不用` | `substitution -> ingredients -> step` |
| `安全`、`熟`、`处理`、`过敏`、`生熟` | `safety -> step -> failure` |
| `失败`、`为什么`、`腥味`、`太甜`、`太咸`、`不脆`、`粘锅`、`糊` | `failure -> step -> safety` |
| `怎么做`、`步骤`、`火候`、`多久`、`怎么炒`、`怎么煮` | `step -> safety -> failure` |

排序 key：

```text
(chunk_type_priority, original_score)
```

这类 rerank 的优点是可解释、低成本、容易测试；缺点是覆盖范围依赖关键词，面对复杂表达时仍可能误判。

## 8. Answer 生成策略

`RAGService.answer()` 先调用 `retrieve()` 获取 sources。

如果没有 sources，返回：

```text
知识库里暂时没有找到足够依据。建议换一个具体菜名、食材或失败现象再问。
```

如果有 sources，优先调用 LLM：

```text
system: 你是 KitchenPilot，一个面向厨房新手的做菜助手...
user: 用户问题 + 最近对话 + sources context
```

当前 prompt 约束：

- 只能根据给定资料和必要的最近对话上下文回答。
- 不要编造精确用量。
- 优先输出可执行步骤、用量、火候和安全风险。
- 默认用朴素中文和编号列表。
- 不展开思考过程。

如果 LLM 不可用或调用失败，则使用模板化 fallback：

```text
根据知识库中关于“{main_recipe}”的内容，建议如下：{sources 前 3 条内容}。
新手操作时优先控制火候、按步骤处理食材，并注意安全提示。
```

## 9. Sources 返回和前端调试

RAG sources 使用 `SourceChunk` schema 返回：

```json
{
  "recipe_id": 1,
  "recipe_name": "番茄炒蛋",
  "chunk_type": "step",
  "content": "...",
  "score": 0.83,
  "metadata": {
    "chunk_id": "recipe:1:step:3:v1",
    "retrieval_source": "qdrant"
  }
}
```

在 Agent state 中，这些 sources 会写入：

```text
retrieved_context
```

前端调试台可以展示：

- answer
- sources
- intent
- active_recipe
- execution_trace
- raw JSON

这让 RAG 命中内容可以被人工检查，也便于排查检索、重排和回答生成中的问题。

## 10. 当前验证命令

预览 chunk 生成结果：

```powershell
cd backend
uv run python script/preview_recipe_chunks.py
```

写入 Qdrant：

```powershell
cd backend
uv run python -m kitchenpilot.seed.seed_qdrant
```

运行 Qdrant RAG demo：

```powershell
cd backend
uv run python script/demo_qdrant_rag.py --seed
```

只查单个问题：

```powershell
cd backend
uv run python script/demo_qdrant_rag.py --query "土豆丝怎么炒得脆？" --top-k 4
```

运行 RAG 相关单元测试：

```powershell
cd backend
uv run pytest tests/unit/test_chunks.py tests/unit/test_qdrant_store.py tests/unit/test_rag_qdrant.py
```

## 11. 当前已知边界

- 当前 chunk 是业务结构切分，不是按 token 长度自适应切分。
- Qdrant payload 已保留 metadata，但当前查询尚未使用 metadata filter。
- rerank 是规则型轻量 rerank，不是 cross-encoder 或 LLM rerank。
- 本地 fallback 是关键词召回，适合兜底，不等价于完整语义检索。
- RAG answer prompt 仍偏基础，source 引用格式、防幻觉约束和回答结构后续还需要增强。
- 用户长期行为和真实个性化偏好尚未进入 RAG 检索过滤链路。

## 12. 后续优化方向

后续工程优化顺序：

1. 增强回答结构：固定输出“直接建议、依据来源、新手安全提醒”。
2. 增加 source 引用：让回答能明确对应第几条 source。
3. 增加 metadata filter：根据 active_recipe、chunk_type 或食材先过滤再向量检索。
4. 扩充固定评测集：覆盖做法、失败、替代、安全和多轮追问。
5. 记录可复核指标：chunk 数、固定问题 Top-K 命中情况、RAG fallback 通过情况。
