"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.

Cách làm:
    - CORPUS được nạp từ chính Chroma collection của Task 4 (ids, documents,
      metadatas) nên BM25 và dense luôn chấm trên cùng một tập chunk/ID.
    - Tokenizer cho tiếng Việt: lowercase, tách theo ký tự chữ/số Unicode
      (giữ nguyên dấu), thêm bigram âm tiết để "học phí" khớp như một cụm
      thay vì hai âm tiết rời ("học", "phí" xuất hiện khắp nơi).
    - Index được cache và tự dựng lại khi CORPUS thay đổi.
"""

import re

import numpy as np
from rank_bm25 import BM25Okapi

from .contracts import validate_search_results


CORPUS: list[dict] = []

_TOKEN = re.compile(r"\w+", re.UNICODE)
_index_cache: dict = {"key": None, "bm25": None}


def tokenize(text: str) -> list[str]:
    """Âm tiết + bigram âm tiết, lowercase, giữ dấu tiếng Việt."""
    tokens = _TOKEN.findall(text.lower())
    bigrams = [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    return tokens + bigrams


def load_corpus_from_vectorstore() -> list[dict]:
    """Đọc toàn bộ chunk đã index ở Task 4 để BM25 dùng đúng corpus đó."""
    from .task4_chunking_indexing import get_collection

    response = get_collection().get(include=["documents", "metadatas"])
    corpus = []
    for item_id, content, metadata in zip(response["ids"], response["documents"], response["metadatas"]):
        metadata = dict(metadata or {})
        metadata.setdefault("url", None)
        corpus.append({"id": item_id, "content": content, "metadata": metadata})
    corpus.sort(key=lambda item: item["id"])
    return corpus


def _ensure_corpus() -> list[dict]:
    if not CORPUS:
        CORPUS.extend(load_corpus_from_vectorstore())
    return CORPUS


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    return BM25Okapi([tokenize(item["content"]) for item in corpus])


def _get_index(corpus: list[dict]) -> BM25Okapi:
    key = (id(corpus), len(corpus), corpus[0]["id"] if corpus else None, corpus[-1]["id"] if corpus else None)
    if _index_cache["key"] != key:
        _index_cache["bm25"] = build_bm25_index(corpus)
        _index_cache["key"] = key
    return _index_cache["bm25"]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần (chỉ chunk có score > 0)."""
    corpus = _ensure_corpus()
    query_tokens = tokenize(query)
    if top_k <= 0 or not corpus or not query_tokens:
        return []

    bm25 = _get_index(corpus)
    scores = bm25.get_scores(query_tokens)
    # Chỉ giữ chunk thực sự chứa token của query. Không lọc theo score > 0 vì
    # với corpus rất nhỏ IDF có thể bằng 0 dù chunk khớp từ khóa.
    query_set = set(query_tokens)
    overlap = np.array([len(query_set.intersection(doc)) for doc in bm25.doc_freqs])
    candidates = np.flatnonzero(overlap > 0)
    order = sorted(candidates, key=lambda i: (-scores[i], -overlap[i], i))[:top_k]

    results: list[dict] = []
    for index in order:
        score = float(scores[index])
        item = corpus[index]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": round(score, 6),
            "metadata": dict(item["metadata"]),
            "retrieval_method": "bm25",
        })

    validate_search_results(results, top_k=top_k, expected_method="bm25")
    return results


if __name__ == "__main__":
    queries = [
        "770.000 đồng/tín chỉ",
        "Quyết định 920/QĐ-ĐHCN",
        "học bổng Nguyễn Thanh Bình",
        "đăng ký học phần học kỳ phụ 2",
    ]
    print(f"Corpus: {len(_ensure_corpus())} chunks")
    for query in queries:
        print(f"\n### {query}")
        for result in lexical_search(query, top_k=3):
            meta = result["metadata"]
            print(f"  {result['score']:8.3f}  {result['id']:<32} [{meta['doc_type']}] {meta['title'][:60]}")
            print(f"            {result['content'][:120]!r}")
