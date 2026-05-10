# KitchenPilot 开发问题与工程思考

本文用于记录项目开发中暴露出的真实问题、原因分析、当前处理方式和后续改进方向。它更偏工程复盘，适合后续整理到简历、面试讲解或项目答辩中。

## 1. 多轮追问缺少 Session 记忆

### 现象

用户第一轮提问：

> 咸蛋黄鸡翅怎么做？只告诉我步骤就好

系统能正确进入 `recipe_qa`，并返回咸蛋黄鸡翅步骤。

用户第二轮继续追问：

> 料酒和生抽要下多少？还需要别的调料吗？

系统没有记住上一轮正在讨论“咸蛋黄鸡翅”，只看到“料酒”“生抽”等食材词，于是 Router 误判为 `recommendation / ingredients`，返回了热汤面、蛋炒饭等推荐结果。

### 原因

当前 `/api/chat` 每次请求基本按单轮输入处理。Agent State 中没有保存 session 级上下文，例如：

- 当前正在讨论的菜谱
- 上一轮 intent
- 上一轮 retrieved sources
- 上一轮回答中的关键实体
- 当前输入是否是追问

因此，当用户使用省略表达、代词或上下文依赖问题时，Router 无法做指代消解。

### 当前结论

这不是长期用户画像问题，而是短期 session memory 问题。

长期用户画像解决“用户偏好什么”。  
短期 session memory 解决“这一轮对话正在聊什么”。

### 后续设计

引入轻量 `ConversationMemoryService`，先用内存 dict 实现：

```text
session_id -> recent_turns
```

每轮保存：

- `query`
- `answer`
- `intent`
- `recommendation_type`
- `active_recipe`
- `ingredients`
- `retrieved_context`

前端每次请求带上 `session_id`。Router 在分类前读取最近 3-5 轮上下文。如果当前问题包含“这个”“它”“还需要什么”“下多少”“调料”等追问信号，就继承上一轮 `active_recipe`，优先走 `recipe_qa`，并把 query 改写为完整问题。

示例：

```json
{
  "query": "料酒和生抽要下多少？还需要别的调料吗？",
  "active_recipe": "咸蛋黄鸡翅",
  "rewritten_query": "咸蛋黄鸡翅中料酒和生抽要下多少？还需要别的调料吗？",
  "intent": "recipe_qa"
}
```

### 可用于简历/面试的表述

项目初版将每轮请求独立处理，导致多轮追问中 Router 缺少上下文。后续引入 session-level conversation memory，保存 active recipe、上一轮 intent 和 retrieved sources，用于追问消解和 query rewrite，提升多轮对话稳定性。

## 2. Intent 设计过细导致推荐模块割裂

### 现象

早期设计中，`ingredient_recommendation` 和 `daily_recommendation` 是两个独立 intent。前端也把“食材推荐”和“每日推荐”做成两个独立模块。

这导致系统看起来像多个功能按钮，而不是一个自然语言 Agent。

### 原因

顶层 intent 混合了“任务大类”和“任务子类型”：

- `recipe_qa` 是任务大类
- `ingredient_recommendation` 是推荐子类型
- `daily_recommendation` 也是推荐子类型

这种设计会让 Router、Graph、API、前端都跟着分裂。

### 当前处理

已将顶层 intent 收敛为：

- `recipe_qa`
- `recommendation`
- `fallback`

推荐类型通过 `recommendation_type` 区分：

- `ingredients`
- `daily`

后续可以扩展：

- `weekly`
- `budget`
- `seasonal`

### 工程价值

这种拆分让顶层 Agent Graph 更稳定，也避免每新增一种推荐场景都新增一个顶层 intent 和一个前端模块。

## 3. 前端最初偏展示页，不适合调试 Agent

### 现象

第一版前端包含多个区域：聊天问答、食材推荐、每日推荐、RAG 来源、执行轨迹。它适合展示功能，但不符合当前测试目标。

用户真实期望是：

> 前端只有一个聊天窗口，通过用户输入自动路由到不同功能，并可视化程序运行过程。

### 原因

前端早期按“功能展示”设计，而不是按“Agent 调试”设计。这样会弱化 Router 的价值，也不利于观察每次请求为什么被路由到某个节点。

### 当前处理

前端改为单聊天入口：

- 所有输入都走 `/api/chat`
- 页面展示 `intent`
- 页面展示 `recommendation_type`
- 页面展示 `execution_trace`
- 页面展示 `quality_check`
- 页面展示 recommendations、RAG sources 和 raw JSON

### 工程价值

调试型前端更适合 Agent 项目早期开发。它让 Router、Graph 节点、RAG sources 和质量检查结果都可见，方便定位误判和链路问题。

## 4. Qdrant / LLM 不可用时需要 fallback

### 现象

本地演示时，Qdrant、embedding 模型或 LLM 都可能因为服务未启动、网络、模型缺失等原因失败。

如果系统强依赖这些外部服务，演示和测试会非常脆弱。

### 当前处理

RAG 服务采用分层 fallback：

- 优先走 Qdrant 向量检索
- Qdrant 或 embedding 不可用时走本地关键词检索
- LLM 不可用时返回基于 source chunks 的模板化回答

### 工程价值

这让项目具备可演示性和鲁棒性。即使外部模型服务失败，系统仍能返回可解释结果，而不是直接 500。

## 5. 检索结果需要轻量 rerank

### 现象

真实 Qdrant 检索能返回相关内容，但不同问题需要不同类型的 chunk。例如：

- 替代食材问题应优先 `substitution`
- 安全问题应优先 `safety`
- 失败原因问题应优先 `failure`
- 做法步骤问题应优先 `step`

仅依赖向量相似度时，top-k 顺序不一定完全符合业务意图。

### 当前处理

在 `RAGService.retrieve()` 中加入轻量 rerank。根据中文问题关键词判断偏好的 chunk type，再在 Qdrant 结果上重排。

### 工程价值

这是一个简单但有效的 RAG 工程优化：不用引入复杂模型，也能让检索结果更贴近业务任务。

## 6. 用户画像接入后，推荐结果仍然同质化

### 现象

前端加入三种测试用户画像后：

- 完全新手
- 会简单菜式的入门用户
- 技艺高超的老手

用户切换画像后输入：

> 推荐一道菜

最初返回结果仍然高度相似，甚至新手和老手都偏向番茄炒蛋、蛋炒饭、热汤面这类简单菜。

这说明“前端有用户画像选项”不等于“推荐系统真正使用了用户画像”。

### 原因

问题主要有两层：

1. Router 没有把泛化推荐稳定路由到用户画像推荐。

   `推荐一道菜` 这类请求没有明确已有食材，也不包含“今天吃什么”等每日推荐关键词，早期容易进入低置信 fallback 或被 LLM fallback 处理，导致链路不稳定。

2. 推荐评分没有真正区分不同技能等级。

   原评分逻辑对所有用户都给“新手友好”较高加分：

   - 新手喜欢 easy 菜
   - 入门用户也喜欢 easy 菜
   - 老手同样因为 easy、耗时短拿到高分

   结果是不同画像虽然存在，但排序权重没有拉开差异。

### 当前处理

已将三种 persona 从旧 `mock_data.USER_PROFILES` 中拆出，放入独立的 `user_profiles.py`：

- `novice_user`：完全新手，偏好 easy、短时间、低风险菜
- `beginner_user`：入门用户，偏好 easy / medium，能接受简单肉菜
- `expert_user`：技艺高超的老手，偏好 medium / hard，能接受长耗时和复杂步骤

Router 规则也做了收敛：

- `推荐一道菜`、`推荐菜`、`随便推荐` → `recommendation / daily`
- `我有鸡蛋和土豆，推荐一道菜` → `recommendation / ingredients`

推荐评分接入 `skill_level` 和 `preferred_difficulties`：

- 新手：easy 加权更高，复杂菜扣分更重
- 入门用户：easy / medium 权重较高，复杂肉菜扣分
- 老手：medium / hard 加权更高，复杂菜不再强惩罚，反而有进阶加分

当前实测：

```text
novice_user -> 番茄炒蛋、蛋炒饭、酸辣土豆丝
expert_user -> 番茄牛腩炖土豆、芥末罗氏虾、白灼虾
```

### 工程价值

这个问题体现了推荐系统中的一个常见陷阱：

> 有用户画像字段，不代表推荐结果已经个性化。

必须让画像字段进入召回、过滤或排序权重，才能真正影响输出。

在当前 MVP 中，项目选择先用可解释的规则权重完成个性化闭环，而不是直接引入复杂模型。这样便于调试，也更适合在简历和面试中解释推荐结果为什么不同。

### 后续设计

后续如果继续增强，可以把 persona 从固定预设升级为真实用户画像：

- `/api/history` 写入用户做菜记录
- 从评分和反馈中更新 skill level
- 根据用户常选菜谱更新 liked ingredients
- 记录近期推荐，避免重复推荐
- 引入候选召回 + rerank 两阶段推荐

### 当前结论

当前推荐模块不是简单 mock：菜谱候选来自 seed/SQLite，排序逻辑会综合食材匹配、难度、耗时、新手友好度和 persona 权重。

但它仍不是生产级个性化系统，因为用户画像仍是预设 persona，不是从真实长期行为中学习得到。

### 简历表述边界

可以写：

> 实现基于规则的个性化推荐 MVP，设计新手、入门用户和老手三类 persona，将技能等级、难度偏好、耗时偏好和已有食材匹配接入推荐排序，支持可解释的推荐理由。

不应写：

> 实现生产级个性化推荐系统。

## 7. Windows 本地启动和停止问题

### 现象

Windows PowerShell 下，`uvicorn --reload` 和 `python -m http.server` 在某些终端环境里 `Ctrl+C` 停止不稳定。

### 当前处理

新增启动脚本：

- `backend/script/start_backend.py`
- `frontend/start_frontend.py`

两者都在终端显示访问链接，并支持按 `Esc` 停止。

### 工程价值

这不是核心算法问题，但会影响项目演示体验。简历项目也需要考虑“别人能不能顺利跑起来”。

## 8. 中文编码和 mojibake 问题

### 现象

部分中文字符串曾出现 mojibake，尤其是在 Windows PowerShell 读取或输出中文时更明显。

### 当前处理

- 文档读取时使用 `Get-Content <path> -Encoding UTF8`
- 前端 HTML 明确 `<meta charset="utf-8">`
- API 请求使用 JSON UTF-8

### 后续设计

需要统一检查数据文件、文档、测试样例和终端输出编码，避免测试“因为同样乱码而通过”。

## 总结

KitchenPilot 的工程价值不只在“能回答菜谱问题”，还在于暴露并处理了真实 Agentic RAG 项目常见问题：

- Router intent 粒度设计
- 推荐子类型建模
- RAG fallback
- 检索 rerank
- 多轮 session memory
- 调试型前端
- 本地运行体验
- 中文编码治理

这些问题都可以作为简历和面试中的工程思考点。
