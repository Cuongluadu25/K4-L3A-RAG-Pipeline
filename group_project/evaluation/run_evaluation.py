"""Run a deterministic retrieval evaluation over the local golden dataset.

This evaluator does not call an LLM or an external API. It measures four
reproducible corpus-grounded proxies so the A/B retrieval comparison can be
rerun without credentials:
- faithfulness proxy: expected-answer token coverage in retrieved context
- answer relevance proxy: question token coverage in retrieved context
- context recall: expected source retrieved
- context precision: retrieved results belonging to expected source
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from src.task7_reranking import rerank_rrf

DATASET_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", text.lower())
        if len(token) > 1
    }


def load_chunks() -> list[dict]:
    chunks = []
    standardized = ROOT / "data" / "standardized"
    for path in sorted(standardized.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            continue
        document_id = path.relative_to(standardized).as_posix()
        doc_type = "legal" if "legal" in path.parts else "news"
        start = 0
        index = 0
        while start < len(content):
            end = min(start + 500, len(content))
            text = content[start:end].strip()
            if text:
                chunks.append(
                    {
                        "id": f"{document_id}::chunk-{index}",
                        "content": text,
                        "metadata": {
                            "source": path.name,
                            "title": path.stem,
                            "doc_type": doc_type,
                            "url": None,
                            "chunk_index": index,
                        },
                    }
                )
                index += 1
            if end == len(content):
                break
            start = end - 50
    return chunks


def dense_proxy(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    query_tokens = tokens(query)
    ranked = []
    for chunk in chunks:
        overlap = len(query_tokens & tokens(chunk["content"]))
        if overlap:
            item = chunk.copy()
            item["score"] = overlap / max(len(query_tokens), 1)
            item["retrieval_method"] = "dense"
            ranked.append(item)
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]


def lexical_proxy(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    query_tokens = tokens(query)
    ranked = []
    for chunk in chunks:
        overlap = len(query_tokens & tokens(chunk["content"]))
        if overlap:
            item = chunk.copy()
            item["score"] = float(overlap)
            item["retrieval_method"] = "bm25"
            ranked.append(item)
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]


def metric_values(case: dict, results: list[dict]) -> dict[str, float]:
    expected_source = case["expected_context"]
    context_tokens = tokens(" ".join(item["content"] for item in results))
    answer_tokens = tokens(case["expected_answer"])
    question_tokens = tokens(case["question"])
    source_hits = [
        item for item in results
        if item["id"].replace("\\", "/").startswith(expected_source)
    ]
    return {
        "faithfulness": len(answer_tokens & context_tokens) / max(len(answer_tokens), 1),
        "answer_relevance": len(question_tokens & context_tokens) / max(len(question_tokens), 1),
        "context_recall": 1.0 if source_hits else 0.0,
        "context_precision": len(source_hits) / max(len(results), 1),
    }


def average(rows: list[dict[str, float]]) -> dict[str, float]:
    return {
        key: sum(row[key] for row in rows) / max(len(rows), 1)
        for key in rows[0]
    }


def evaluate() -> dict:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    chunks = load_chunks()
    configurations = {"dense-only": [], "hybrid + RRF": []}

    for case in dataset:
        dense = dense_proxy(case["question"], chunks, top_k=10)
        sparse = lexical_proxy(case["question"], chunks, top_k=10)
        hybrid = rerank_rrf([dense, sparse], top_k=5)
        configurations["dense-only"].append(metric_values(case, dense[:5]))
        configurations["hybrid + RRF"].append(metric_values(case, hybrid))

    scores = {name: average(rows) for name, rows in configurations.items()}
    for name, values in scores.items():
        values["average"] = sum(values.values()) / 4
    return {"dataset_size": len(dataset), "top_k": 5, "scores": scores}


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
