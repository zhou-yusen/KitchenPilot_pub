# KitchenPilot Evals

固定评测集位于 `dataset/`，评测输出写入 `results/`。

## RAG benchmark

快速检索评测，不调用 LLM：

```powershell
uv run python evals/run_rag_benchmark.py --mode retrieval
```

使用本地 lexical fallback 做 smoke test：

```powershell
uv run python evals/run_rag_benchmark.py --mode retrieval --limit 10 --no-rag-use-qdrant
```

评测 RAG 生成答案，会调用当前配置的 LLM：

```powershell
uv run python evals/run_rag_benchmark.py --mode answer
```

评测 session memory 多轮追问：

```powershell
uv run python evals/run_rag_benchmark.py --mode multiturn
```

完整评测：

```powershell
uv run python evals/run_rag_benchmark.py --mode all
```

常用参数：

- `--top-k 4`：设置检索 top-k。
- `--limit 10`：只跑前 10 条，用于快速验证。
- `--llm-provider mock|ollama|openai`：覆盖 LLM provider。
- `--no-rag-use-qdrant`：不用 Qdrant，改用本地 lexical fallback。
- `--output-prefix my_run`：指定输出文件前缀。

输出文件：

- `results/<prefix>_summary.json`：聚合指标。
- `results/<prefix>_single_turn.jsonl`：单轮逐样例结果。
- `results/<prefix>_multiturn.jsonl`：多轮逐样例结果。

## Qdrant RAG focused benchmark

绕过意图路由，直接测试 Qdrant RAG 层的检索和生成质量。

纯 Qdrant 向量检索评测（不调 LLM，快速）：

```powershell
uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval
```

Qdrant 检索 + LLM 生成答案（绕过意图路由）：

```powershell
uv run python evals/run_qdrant_eval.py --mode qdrant-answer
```

多轮追问 RAG 评测（绕过 agent graph）：

```powershell
uv run python evals/run_qdrant_eval.py --mode qdrant-multiturn
```

与本地 lexical fallback 对比（生成 Jaccard overlap 指标）：

```powershell
uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval --compare-local
```

限制条数快速验证：

```powershell
uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval --limit 10
```

使用自定义评测集：

```powershell
uv run python evals/run_qdrant_eval.py --mode qdrant-retrieval --dataset evals/dataset/my_questions.jsonl
```

常用参数：

- `--mode qdrant-retrieval|qdrant-answer|qdrant-multiturn`：评测模式。
- `--top-k 4`：检索 top-k（默认 4）。
- `--limit N`：只跑前 N 条。
- `--compare-local`：同时跑本地 lexical 检索并输出 Jaccard overlap。
- `--dataset path`：自定义 JSONL 数据集。
- `--output-prefix my_run`：指定输出文件前缀。

输出文件：

- `results/<prefix>_summary.json`：聚合指标（含 per-category 分类统计）。
- `results/<prefix>_qdrant_retrieval.jsonl`：逐样例结果。
- `results/<prefix>_local_retrieval.jsonl`：本地检索对比结果（使用 `--compare-local` 时）。
