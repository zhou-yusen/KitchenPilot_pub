# KitchenPilot 意图识别技术细节

本文记录 KitchenPilot 当前意图识别链路的工程实现，重点说明 Router 如何识别用户请求、如何抽取食材、如何区分菜谱问答和推荐、如何处理低置信度问题，以及结果如何进入 LangGraph 后续节点。

## 1. Router 在系统中的位置

意图识别位于 Agent 工作流前半段，负责把自然语言请求路由到不同任务节点。

当前主链路：

```text
用户问题
-> parse_input_node 抽取食材
-> load_session_memory_node 加载会话记忆并处理追问
-> load_user_history_node 加载用户画像
-> route_intent_node 识别意图
-> route_after_intent 选择后续节点
   -> recipe_qa
   -> recommendation
   -> fallback
```

相关代码：

- `backend/src/kitchenpilot/agent/nodes/intent_router.py`
- `backend/src/kitchenpilot/agent/graph.py`
- `backend/src/kitchenpilot/agent/state.py`
- `backend/src/kitchenpilot/agent/nodes/recommendation_node.py`

## 2. 当前支持的意图

顶层意图由 `IntentType` 定义：

| intent | 含义 | 后续节点 |
| --- | --- | --- |
| `recipe_qa` | 菜谱问答、做法、步骤、失败原因、替代食材、安全提醒 | `recipe_qa_node` |
| `recommendation` | 菜品推荐，包括已有食材推荐和每日推荐 | `recommendation_node` |
| `fallback` | 无法稳定判断，需要澄清 | `fallback_node` |

推荐类意图还会带 `RecommendationType`：

| recommendation_type | 含义 |
| --- | --- |
| `ingredients` | 根据用户已有食材推荐 |
| `daily` | 根据用户画像、偏好或“今天吃什么”类请求推荐 |

这种设计把顶层 intent 控制在较少类别，避免 Router 过早膨胀；推荐内部差异交给 `recommendation_type` 表达。

## 3. AgentState 中的路由字段

Router 结果会写入 `AgentState`，后续节点和前端调试台都依赖这些字段。

| 字段 | 说明 |
| --- | --- |
| `intent` | 顶层意图：`recipe_qa / recommendation / fallback` |
| `intent_confidence` | 当前分类置信度 |
| `intent_source` | 当前分类来源，例如 `rule`、`embedding`、`rule+embedding`、`llm`、`session_memory`、`ambiguous` |
| `recommendation_type` | 推荐子类型：`ingredients / daily` |
| `needs_clarification` | 是否需要向用户澄清 |
| `clarification_question` | fallback 时返回的问题 |
| `user_ingredients` | 从用户输入中抽取的食材 |
| `active_recipe` | 当前会话正在讨论的菜谱 |
| `rewritten_query` | 多轮追问改写后的 query |
| `is_follow_up` | 是否被判断为上下文追问 |

这些字段也会进入 `execution_trace`，方便调试 Router 决策。

## 4. 总体识别策略

当前 Router 采用三层策略：

```text
规则识别
-> 高置信度则直接返回
-> 否则执行 embedding 相似度识别
-> 合并 rule 与 embedding
-> 中高置信度则返回
-> 低置信度时调用 LLM fallback
-> 仍无法判断则 fallback 澄清
```

核心入口：

```python
IntentRouter.classify_with_confidence(query, ingredients=None)
```

默认阈值：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `high_confidence` | `0.80` | 规则结果达到该值可直接返回 |
| `low_confidence` | `0.60` | 合并结果达到该值可接受 |
| `min_margin` | `0.08` | embedding 第一名和第二名的最小差距 |

## 5. 输入解析和食材抽取

`parse_input_node` 会调用：

```python
router.extract_ingredients(query)
```

食材来源不是硬编码列表，而是从 `RecipeService().list_recipes()` 读取当前菜谱数据，汇总所有已知食材。

抽取逻辑：

- 如果食材名直接出现在用户输入中，则命中。
- 对部分常见后缀做短别名，例如 `鸡翅中` 可以匹配 `鸡翅`。
- 对 `鲜` 开头的食材生成去前缀别名。
- 抽取结果会和已有 `user_ingredients` 合并去重。

示例：

```text
输入：我有鸡翅，推荐一道菜
可能抽取：["鸡翅"]
```

食材抽取会影响后续判断：只要识别到已有食材，Router 更倾向于将请求归为 `recommendation / ingredients`。

## 6. 规则识别

规则识别是第一层，负责处理高确定性问题。它成本低、可解释，也能避免把所有判断都交给 LLM。

### 6.1 菜谱问答规则

以下情况倾向 `recipe_qa`：

- 用户提到已知菜名，并且出现学习或制作意图，例如 `我想学咸蛋黄鸡翅`。
- 用户问题包含问法、做法、失败、替代、注意事项等线索。
- 用户直接提到已知菜谱名。

常见关键词：

```text
怎么、如何、为什么、注意、替代、失败、太甜、做法、不脆
```

示例：

```text
土豆丝怎么炒得脆？ -> recipe_qa
可乐鸡翅为什么太甜？ -> recipe_qa
我想学咸蛋黄鸡翅 -> recipe_qa
```

### 6.2 食材推荐规则

以下情况倾向 `recommendation / ingredients`：

- 已抽取到食材。
- 用户问题包含“我有”“家里有”“只有”“食材”“能做什么”等线索。

示例：

```text
我有鸡蛋、番茄和土豆，推荐一道简单菜。 -> recommendation / ingredients
家里只有米饭和鸡蛋，能做什么？ -> recommendation / ingredients
```

### 6.3 每日推荐规则

以下情况倾向 `recommendation / daily`：

- 用户问 `今天吃什么`
- 用户要求 `今日推荐`、`每日推荐`
- 用户说 `推荐一道菜` 但没有明显已有食材上下文
- 用户提到偏好、晚饭、清淡等泛推荐需求

示例：

```text
今天吃什么？ -> recommendation / daily
推荐一道菜 -> recommendation / daily
想按我的偏好安排一顿饭 -> recommendation / daily
```

### 6.4 短追问澄清规则

有些短问题看起来像食材推荐，但实际缺少上下文。当前会走 `fallback` 澄清，而不是误判为推荐。

示例：

```text
用不用下盐？ -> fallback，需要用户说明是哪道菜
```

这种设计避免把“盐”“生抽”“油”这类调料词误当作用户已有食材推荐。

## 7. Embedding 相似度识别

当规则结果不够高置信度时，Router 会用 embedding 相似度补充判断。

示例句定义在 `INTENT_EXAMPLES` 中，按顶层 intent 分组：

- `recipe_qa` 示例：做法、失败原因、替代食材、注意事项。
- `recommendation` 示例：已有食材推荐、今天吃什么、按偏好推荐。

流程：

```text
启动后首次使用
-> embed 所有 intent examples 并缓存
-> embed 当前 query
-> 计算 query 和每个 example 的 cosine similarity
-> 每个 intent 取最高相似度
-> 比较第一名和第二名 margin
-> 得到 embedding 分类结果
```

置信度大致由 `top_score` 和 `margin` 共同决定：

- 相似度高、margin 大：提高置信度。
- margin 小：标记为 `ambiguous`，降低置信度。

Embedding 层的作用不是替代规则，而是处理规则关键词不明显但语义相近的请求。

## 8. Rule 与 Embedding 合并

`_merge_results()` 负责合并规则和 embedding 结果。

合并策略：

- 如果 rule 和 embedding 识别出相同非 fallback 意图，则提升置信度，source 标记为 `rule+embedding`。
- 如果两者冲突，并且 rule 不是 fallback，则降低置信度，source 标记为 `ambiguous`。
- 如果只有 embedding 有较高置信度，则使用 embedding 结果。
- 如果最终置信度低于 `low_confidence`，后续交给 LLM fallback。

这能避免某个单一判断源过度自信。

## 9. LLM Fallback

当规则和 embedding 都无法稳定判断时，Router 会调用 chat provider 做结构化分类。

Prompt 要求模型只输出 JSON：

```json
{
  "intent": "recommendation",
  "recommendation_type": "ingredients",
  "confidence": 0.8,
  "ingredients": ["鸡蛋"],
  "needs_clarification": false
}
```

Router 会从模型输出中截取 JSON object，并用 Pydantic / enum 进行约束。

安全策略：

- 如果没有识别到食材，并且输入没有任何做饭信号，即使 LLM 给出推荐，也会降级为 `fallback`。
- LLM 失败、JSON 解析失败或输出非法 enum 时，不抛出到 API 层，而是返回 `None`，由外层 fallback 处理。

示例：

```text
清淡一点别太麻烦 -> 规则不够明确，LLM fallback 可判断为 recommendation / daily
随便帮我想想 -> 非明确做饭请求，fallback 澄清
```

## 10. Session Memory 追问路由

Router 不只看当前 query，也会利用会话上下文处理追问。

`load_session_memory_node` 会读取当前 session 的最近对话和 `active_recipe`。如果用户问题像追问，并且存在上一轮菜谱上下文，则会改写 query：

```text
上一轮 active_recipe：可乐鸡翅
用户追问：生抽要下多少？
rewritten_query：可乐鸡翅：生抽要下多少？
```

追问判断线索包括：

```text
多少、几勺、几克、多久、火候、还需要、这个、这道菜、它、刚才、前面、放多少
```

当 `is_follow_up=True` 且存在 `active_recipe` 时，`route_intent_node` 会直接路由到：

```text
intent = recipe_qa
intent_source = session_memory
intent_confidence = 0.92
```

这样短追问不会被误判为食材推荐或 fallback。

## 11. 路由到后续节点

`route_after_intent()` 根据顶层 intent 决定 LangGraph 后续节点：

```python
if intent == IntentType.RECIPE_QA:
    return "recipe_qa"
if intent == IntentType.RECOMMENDATION:
    return "recommendation"
return "fallback"
```

后续行为：

- `recipe_qa`：调用 RAG，返回 answer 和 sources。
- `recommendation`：根据 `recommendation_type` 调用推荐服务。
- `fallback`：返回澄清问题。

`recommendation_node` 如果没有拿到 `recommendation_type`，会默认使用 `ingredients`，但正常情况下 Router 会提前填好。

## 12. Clarification 设计

当 Router 无法判断时，会返回统一澄清问题：

```text
我暂时无法判断你的具体需求。
你可以这样问：
1. 根据已有食材推荐菜：我有鸡蛋和土豆，推荐一道菜。
2. 按你的偏好推荐今天吃什么：今天吃什么？
3. 回答某道菜的具体做法：土豆丝怎么炒得脆？
```

短调料追问会返回更具体的澄清：

```text
你是在追问哪道菜？请先说菜名，例如：可乐鸡翅生抽要下多少？
```

澄清问题写入：

- `needs_clarification`
- `clarification_question`
- `draft_answer`

## 13. 当前验证命令

运行 Router 单元测试：

```powershell
cd backend
uv run pytest tests/unit/test_router.py
```

运行命令行 demo：

```powershell
cd backend
uv run python script/demo_intent_router.py
```

指定问题：

```powershell
cd backend
uv run python script/demo_intent_router.py --query "土豆丝怎么炒得脆？" --query "我有鸡蛋和土豆，推荐一道菜"
```

交互式测试：

```powershell
cd backend
uv run python script/demo_intent_router.py --interactive
```

## 14. 当前已知边界

- 顶层 intent 目前只保留三类，复杂任务例如一周菜单规划、菜谱录入尚未独立成生产路径。
- 食材抽取依赖当前菜谱库中的已知食材，无法识别知识库外的新食材。
- 规则关键词覆盖有限，表达特别隐晦时依赖 embedding 或 LLM fallback。
- Embedding 示例集规模较小，适合 MVP，不是完整意图分类训练集。
- LLM fallback 只做结构化分类，不负责业务执行。
- 当前推荐子类型只有 `ingredients` 和 `daily`，后续如果增加营养、预算、多人份等场景，需要扩展 `RecommendationType`。

## 15. 后续优化方向

后续工程优化顺序：

1. 扩充 Router 测试集：覆盖菜谱问答、食材推荐、每日推荐、短追问、非做饭请求。
2. 为每类 intent 固定 3-5 个验证样例，记录 intent、confidence、source 和 recommendation_type。
3. 把高频误判样例沉淀为规则或 embedding examples。
4. 增加更细的 query rewrite：让多轮追问不仅补菜名，也能补上一轮 topic。
5. 文档化 Router 决策案例，便于维护规则、embedding examples 和 LLM fallback 的边界。
