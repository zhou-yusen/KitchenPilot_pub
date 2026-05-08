# KitchenPilot 简历项目写法

## 1. 简历项目标题

可以使用以下标题之一：

### 推荐标题

**KitchenPilot：基于 LangGraph 的个性化食谱 Agentic RAG 助手**

### 中文标题

**小厨子：面向厨房新手的食谱推荐与问答系统**

### 偏技术标题

**基于 LangGraph + RAG 的个性化食谱推荐与问答系统**

## 2. 简历项目一句话描述

构建了一个面向厨房新手的 Agentic RAG 食谱助手，基于 LangGraph 编排多任务 Agent 工作流，结合结构化食谱库、Qdrant 向量检索、用户做菜历史和推荐算法，实现可溯源的菜谱问答、食材推荐和个性化每日推荐。

## 3. 技术栈写法

**技术栈：** LangGraph、LangChain、FastAPI、SQLite、Qdrant、SQLAlchemy、Pydantic、Embedding Model、LLM、Docker Compose

如果简历空间较紧，可以写成：

**技术栈：** LangGraph、LangChain、FastAPI、SQLite、Qdrant、SQLAlchemy、Pydantic

## 4. 简历项目经历模板

### 版本一：适合完整项目经历

**KitchenPilot：基于 LangGraph 的个性化食谱 Agentic RAG 助手**

**技术栈：** LangGraph、LangChain、FastAPI、SQLite、Qdrant、SQLAlchemy、Pydantic、LLM、Embedding Model

- 面向厨房新手场景，设计并实现 Agentic RAG 食谱助手，支持菜谱问答、食材推荐、替代食材建议、失败原因分析和个性化每日推荐。
- 基于 LangGraph 构建 Router-based Hierarchical Agent Graph，通过意图识别 Router 将用户请求分发到菜谱问答、食材推荐、每日推荐等子图，并加入质量检查与答案修复闭环。
- 设计 SQLite 结构化食谱库，存储菜谱、食材、步骤、难度、季节性、新手友好度、用户做菜历史和评分反馈等数据，支撑精确查询与推荐排序。
- 使用 Qdrant 构建向量知识库，将菜谱步骤、烹饪技巧、常见失败点、替代食材等内容切分为 chunk 并生成 embedding，实现基于语义检索的 RAG 问答。
- 设计食材匹配和推荐排序逻辑，综合已有食材匹配度、缺失食材、菜品难度、预计耗时、食材常见性、季节性和用户历史偏好生成推荐结果。
- 使用 Pydantic 定义 Agent 状态、食谱 Schema 和结构化输出格式，并在质量检查节点校验回答是否基于检索结果、是否符合用户食材约束和新手安全要求。
- 通过 FastAPI 封装问答、推荐、用户历史和菜谱查询接口，支持前端聊天界面和推荐结果展示。

## 5. 精简版项目经历

适合简历空间有限时使用：

**KitchenPilot：基于 LangGraph 的个性化食谱 Agentic RAG 助手**

**技术栈：** LangGraph、LangChain、FastAPI、SQLite、Qdrant、SQLAlchemy、Pydantic

- 构建面向厨房新手的 Agentic RAG 食谱助手，支持菜谱问答、食材推荐、替代食材建议和个性化每日推荐。
- 基于 LangGraph 设计意图路由、多任务子图、工具调用和质量检查闭环，实现可控的 Agent 工作流。
- 使用 SQLite 存储结构化食谱、食材、步骤和用户历史，使用 Qdrant 存储菜谱 chunk embedding，支持结构化过滤与语义检索结合。
- 设计推荐排序逻辑，综合食材匹配度、菜品难度、预计耗时、季节性、食材常见性和用户反馈生成推荐结果。
- 使用 Pydantic 约束 Agent 状态和 LLM 结构化输出，并通过质量检查降低幻觉和不安全烹饪建议。

## 6. 更偏 AI 工程方向的写法

如果投递岗位更偏大模型应用、RAG、AI Agent，可以突出以下内容：

**KitchenPilot：Agentic RAG 食谱推荐与问答系统**

**技术栈：** LangGraph、LangChain、Qdrant、FastAPI、SQLite、Pydantic、LLM、Embedding Model

- 基于 LangGraph 实现 Router-based Hierarchical Agent Graph，将复杂用户请求拆分为意图识别、知识检索、食材分析、推荐排序、答案生成和质量检查等节点。
- 构建混合检索方案，使用 SQLite 进行食材、难度、时间、季节性等结构化过滤，使用 Qdrant 进行菜谱技巧和失败原因的语义检索。
- 将食谱知识拆分为食材准备、步骤说明、新手提示、失败原因和替代食材等 chunk，生成 embedding 后写入 Qdrant，提升问答依据的可追溯性。
- 设计 RAG 答案质量检查机制，校验回答是否引用知识库、是否遗漏关键步骤、是否存在不适合新手或危险的烹饪建议。
- 使用 Pydantic 约束 Agent State 和 LLM 输出，减少自由文本解析错误，提高 Agent 工作流稳定性。

## 7. 更偏后端工程方向的写法

如果投递岗位更偏 Python 后端、后端开发、AI 后端，可以突出以下内容：

**KitchenPilot：基于 FastAPI 的智能食谱推荐与问答后端系统**

**技术栈：** FastAPI、SQLAlchemy、SQLite、Qdrant、LangGraph、LangChain、Pydantic

- 使用 FastAPI 设计问答、食材推荐、每日推荐、菜谱查询和用户历史接口，封装 LangGraph Agent 服务能力。
- 基于 SQLAlchemy 设计食谱、食材、菜谱步骤、用户做菜历史、评分反馈和问答日志等数据模型。
- 使用 SQLite 存储结构化业务数据，支持按食材、难度、耗时、季节性和新手友好度进行候选菜谱筛选。
- 集成 Qdrant 向量数据库，存储菜谱知识 chunk embedding，为菜谱问答、失败原因分析和替代食材建议提供语义检索能力。
- 将推荐逻辑封装到 Service Layer，综合食材匹配、缺失食材、用户偏好、历史评分和近期推荐记录进行排序。
- 通过 Pydantic 定义请求、响应和内部状态 Schema，提高接口稳定性和数据校验能力。

## 8. 更偏推荐系统方向的写法

如果投递岗位涉及推荐算法、搜索推荐、数据应用，可以突出以下内容：

**KitchenPilot：个性化食谱推荐与 RAG 问答系统**

**技术栈：** Python、FastAPI、SQLite、Qdrant、LangGraph、LangChain、Pydantic

- 设计面向厨房新手的食谱推荐系统，基于用户已有食材、做菜历史、评分反馈和菜品属性生成个性化推荐。
- 构建多因子推荐排序策略，综合食材匹配度、缺失食材数量、菜品难度、预计耗时、食材常见性、季节性和历史偏好计算推荐分数。
- 记录用户做菜历史、评分、难度反馈和近期推荐结果，用于偏好建模和避免重复推荐。
- 结合 Qdrant 语义检索和 SQLite 结构化过滤，实现菜谱知识检索、候选召回和推荐解释生成。
- 输出推荐理由、已有食材匹配情况、缺失食材、新手注意事项和常见失败点，提升推荐结果可解释性。

## 9. 面试讲解思路

面试中可以按以下顺序介绍项目：

1. **项目背景**：厨房新手做饭时常遇到不知道做什么、已有食材不会搭配、做菜失败不知道原因等问题。
2. **为什么不用普通聊天机器人**：做饭建议需要基于具体食谱和安全规则，直接让大模型回答容易幻觉。
3. **为什么使用 RAG**：通过检索结构化食谱库和向量知识库，让回答基于可追溯的食谱内容。
4. **为什么使用 Agent**：用户问题通常包含多个子任务，需要意图识别、食材分析、检索、推荐排序和质量检查。
5. **系统架构**：FastAPI 接入请求，LangGraph 编排 Agent，Service Layer 封装业务逻辑，SQLite 和 Qdrant 分别存结构化数据和向量数据。
6. **核心难点**：如何让推荐结果符合用户已有食材、如何控制 Agent 流程、如何减少幻觉和危险建议。
7. **改进方向**：增加菜谱录入、一周菜单规划、营养分析、图谱化食材替代关系和多用户部署。

## 10. 可以量化的指标

如果后续实现时补充测试或实验，可以在简历中加入量化指标。

可设计的指标包括：

- 首批录入菜谱数量，例如 `100+` 道家常菜
- 菜谱知识 chunk 数量，例如 `500+` 条
- 推荐接口平均响应时间
- RAG 检索 Top-K 命中率
- 质量检查通过率
- 人工评估回答准确率
- 用户历史推荐去重率

示例写法：

- 构建包含 `100+` 道家常菜和 `500+` 条知识 chunk 的食谱知识库，支持按食材、难度、耗时和季节性进行混合检索。
- 设计 Top-K 语义检索与结构化过滤结合的召回方案，在测试问题集上提升菜谱技巧问答命中率。

## 11. 推荐最终简历版本

如果只能放一个版本，推荐使用下面这版：

**KitchenPilot：基于 LangGraph 的个性化食谱 Agentic RAG 助手**

**技术栈：** LangGraph、LangChain、FastAPI、SQLite、Qdrant、SQLAlchemy、Pydantic、LLM

- 面向厨房新手场景，构建 Agentic RAG 食谱助手，支持菜谱问答、食材推荐、替代食材建议、失败原因分析和个性化每日推荐。
- 基于 LangGraph 设计意图路由、多任务子图、工具调用和质量检查闭环，将复杂请求拆分为食材分析、知识检索、推荐排序、答案生成和安全校验等步骤。
- 使用 SQLite 存储结构化食谱、食材、步骤、难度、季节性和用户做菜历史，使用 Qdrant 存储菜谱知识 chunk embedding，实现结构化过滤与语义检索结合。
- 设计多因子推荐排序策略，综合食材匹配度、缺失食材、菜品难度、预计耗时、食材常见性、季节性和用户历史反馈生成推荐结果。
- 使用 Pydantic 约束 Agent State 和 LLM 结构化输出，并通过质量检查节点校验回答依据、用户约束和烹饪安全性，降低幻觉和不可靠建议。

## 12. 简历写法注意事项

- 不要只写“调用大模型实现食谱问答”，这样技术含量不够。
- 要突出 LangGraph 的工作流设计，而不是泛泛写 Agent。
- 要突出 SQLite 和 Qdrant 分工，体现结构化数据和向量数据结合。
- 要突出质量检查和安全校验，因为做饭场景有实际风险。
- 如果项目还没完全实现，简历中不要写具体量化指标，除非已经真实完成测试。
- 如果使用了本地模型或开源模型，可以强调支持多 LLM Provider 切换。

