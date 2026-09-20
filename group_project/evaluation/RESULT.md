# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-20 |
| Framework and version | Local deterministic evaluator in `run_evaluation.py` |
| Evaluator model | None; token-overlap proxy |
| Generator model | Not called in this offline run |
| Embedding model | Not called; local retrieval proxy |
| Corpus version/commit | Working tree on branch `tqkhanh` |
| Golden dataset size | 15 |
| `top_k` | 5 |
| Fallback threshold and calibration | 0.3 in retrieval pipeline; not exercised by offline evaluator |

## Configurations

- **Config A - dense-only:** top 5 results from the deterministic dense proxy.
- **Config B - hybrid + RRF:** dense proxy and lexical proxy fused once with RRF, top 5.

Both configurations use the same 15-case dataset and top-k value. The offline runner does not call an LLM, external evaluator, or embedding API.

## Overall scores

| Metric | Config A | Config B | Delta B-A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.5694 | 0.5694 | 0.0000 |
| Answer relevance | 0.6715 | 0.6715 | 0.0000 |
| Context recall | 0.3333 | 0.3333 | 0.0000 |
| Context precision | 0.1067 | 0.1067 | 0.0000 |
| **Average** | 0.4202 | 0.4202 | 0.0000 |

Metric definitions in this offline run:

- Faithfulness proxy: expected-answer token coverage in retrieved context.
- Answer relevance proxy: question token coverage in retrieved context.
- Context recall: whether the expected source was retrieved.
- Context precision: fraction of retrieved results from the expected source.

## A/B comparison

- **Better configuration:** Neither configuration was better in this offline run.
- **Evidence:** Both configurations scored 0.4202 average over the same 15 cases.
- **Latency/cost trade-off:** Hybrid adds lexical search and RRF processing, so it has higher local processing cost. Latency was not measured in this run.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Dang ky hoc ky 2 | dense-only | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Query tokenization misses the expected source wording. |
| 2 | IELTS Academic toi thieu | hybrid + RRF | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Expected answer uses a phrase variant not ranked in top 5. |
| 3 | Ho tro tai chinh va hoc bong | dense-only | 0.00 | 0.00 | 0.00 | 0.00 | retrieval | Boilerplate/news content dilutes the relevant chunk. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Normalize Vietnamese text and improve tokenization | Several expected sources were missed by lexical overlap. | Higher recall. | Add normalization and rerun the same 15 cases. |
| 2 | Filter boilerplate while preserving source/title metadata | News pages contain repeated navigation and footer text. | Better precision. | Filter boilerplate before chunking and compare precision. |
| 3 | Run an online LLM evaluation after API setup | Offline evaluation cannot measure generated-answer faithfulness. | Valid generation metrics. | Run the same dataset with a fixed evaluator model. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | --- | --- |
| Offline deterministic proxy | Not applicable | 0.0000 A/B delta | No API cost | Reproducible baseline; follow with RAGAS/LLM evaluation when credentials are available. |
