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
