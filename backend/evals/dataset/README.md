# KitchenPilot 固定评测集 v1.0

本评测集基于 `preview_fixed_clickable_links.html` 自动抽取生成，覆盖 50 道家常菜。

## 文件

- `rag_questions.jsonl`：单轮 RAG 检索 + 回答评测，共 150 条。
- `router_questions.jsonl`：Router 意图识别评测，共 90 条。
- `rag_multiturn_questions.jsonl`：多轮追问 / session-memory 评测，共 25 条。
- `safety_questions.jsonl`：食品安全专项评测，共 40 条。
- `recipes_extracted.json`：从 HTML 中抽取出的结构化菜谱数据。
- `eval_manifest.json`：评测集说明和推荐指标。

## 推荐放置路径

```text
backend/evals/rag_questions.jsonl
backend/evals/router_questions.jsonl
backend/evals/rag_multiturn_questions.jsonl
backend/evals/safety_questions.jsonl
```

## 推荐指标

### Retrieval
- Recipe Recall@4
- ChunkType Hit@4
- MRR
- Source Coverage

### Answer
- Must Include Pass
- Groundedness Pass
- Safety Pass
- No Hallucination Pass

### Router
- Intent Accuracy
- Recommendation Type Accuracy
- Recipe Slot Accuracy

### Session
- Active Recipe Accuracy
- Rewrite Keyword Accuracy
- Follow-up Intent Accuracy

## 说明

这是一套固定 benchmark，不建议每次运行时动态生成。后续如果你修改菜谱库，可以另存为 v1.1 / v2.0，避免不同实验结果不可比较。
