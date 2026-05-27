# KitchenPilot Evals

评测框架和数据集位于 `evals/`，评测输出写入 `results/`。

## RAGAS 评测（当前主力评测框架）

基于 RAGAS 0.4.3 框架的 RAG 端到端评测，使用 mimo-v2.5 作为 Judge LLM。

评测指标：

| 指标 | 说明 | 类型 |
| --- | --- | --- |
| Faithfulness | 回答是否忠于检索到的 context | RAGAS (LLM judge) |
| Answer Relevancy | 回答是否切题 | RAGAS (LLM judge) |
| Context Precision | 检索结果排序是否精准 | RAGAS (LLM judge) |
| Context Recall | 参考答案信息是否被检索覆盖 | RAGAS (LLM judge) |
| Retrieval Hit Rate | 是否命中相关菜谱 | 自定义 |
| Answer Similarity | 答案语义相似度 | 自定义 |
| Recipe Coverage | 回答覆盖相关菜谱比例 | 自定义 |
| Hard Case Accuracy | 难题通过率 | 自定义 |
| Must-Include Fact Rate | 关键事实覆盖率 | 自定义 |

### 快速验证（3 条）

```powershell
uv run python evals/run_ragas_eval.py --limit 3 --collection recipe_chunks_split
```

### 全量评测（250 条，约 3-4 小时）

```powershell
uv run python evals/run_ragas_eval.py --collection recipe_chunks_split
```

### 使用 Merged 策略对比

```powershell
uv run python evals/run_ragas_eval.py --collection recipe_chunks_merged
```

### 常用参数

- `--limit N`：只跑前 N 条，用于快速验证。
- `--collection name`：指定 Qdrant collection（`recipe_chunks_split` 或 `recipe_chunks_merged`）。
- `--dataset path`：自定义测试集 JSON 文件。
- `--output path`：指定 HTML 报告输出路径。

### 输出

- `results/ragas_report.html`：自包含 HTML 评测报告，包含总览指标、分类型统计和逐条明细。
- 终端输出 RAGAS 分数和自定义指标汇总。

### 测试集

测试集位于 `dataset/rag_eval_split_250.json`，共 250 条用例。

详见 [dataset/README.md](dataset/README.md)。

## 评测分析报告

`results/rag_analysis_report.html` 包含系统架构、测试集说明、RAGAS 预评测结果、问题诊断和改进方案的完整分析。

## 历史评测脚本

早期评测脚本（`run_rag_benchmark.py`、`run_qdrant_eval.py` 等）已被 `run_ragas_eval.py` 替代并删除。旧版测试数据集（`rag_questions.jsonl`、`router_questions.jsonl` 等）已被 `rag_eval_split_250.json` 替代。
