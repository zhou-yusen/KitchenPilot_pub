# KitchenPilot RAG 评测数据集

## 当前数据集

主评测集文件：`rag_eval_split_250.json`

共 250 条测试用例，覆盖 9 种问题类型、3 个难度等级。

### 问题类型分布

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| exact_recipe | 50 | 指定菜谱的做法问答 |
| ingredient_based | 38 | 基于已有食材的菜谱匹配 |
| technique | 38 | 烹饪技巧和步骤细节 |
| substitution | 25 | 食材替代方案 |
| comparison | 25 | 多菜谱对比 |
| constraint_based | 25 | 带约束条件的推荐 |
| step_detail | 25 | 步骤级别的细节问答 |
| confusing_query | 12 | 模糊或易混淆问题 |
| unanswerable | 12 | 知识库中无答案的问题 |

### 难度分布

| 等级 | 数量 | 占比 |
| --- | --- | --- |
| easy | 66 | 26.4% |
| medium | 134 | 53.6% |
| hard | 50 | 20% |

### 数据结构

每条用例包含以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| test_id | string | 唯一标识 |
| query | string | 用户问题 |
| question_type | enum | 问题类型 |
| case_level | enum | regular / hard |
| query_difficulty | enum | easy / medium / hard |
| relevant_record_ids | list[int] | 应检索到的菜谱 ID |
| expected_chunk_ids | list[str] | 期望命中的 chunk ID |
| golden_contexts | list[dict] | 标准 context（含 chunk_id, content, chunk_type） |
| reference_answer | string | 参考标准答案 |
| must_include_facts | list[str] | 回答中必须包含的关键事实 |
| must_not_include_facts | list[str] | 回答中不应出现的内容 |
| supporting_chunk_ids | list[str] | 支撑答案的 chunk |
| required_chunk_ids | list[str] | 必须检索到的 chunk |
| optional_chunk_ids | list[str] | 可选 chunk |
| hard_negative_chunk_ids | list[str] | 易混淆的干扰 chunk |
| metric_applicability | dict | 各指标是否适用于本条用例 |

## 已删除的旧数据集

以下旧数据集已被 `rag_eval_split_250.json` 替代并删除：

- `rag_questions.jsonl`（150 条，旧版单轮 RAG 评测）
- `rag_multiturn_questions.jsonl`（25 条，旧版多轮评测）
- `router_questions.jsonl`（90 条，旧版 Router 评测）
- `safety_questions.jsonl`（40 条，旧版安全评测）
- `eval_manifest.json`（旧版评测说明）
