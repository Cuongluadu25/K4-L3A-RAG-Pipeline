"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

from .task4_chunking_indexing import chunk_documents, load_documents


CORPUS: list[dict] = []


def _get_corpus() -> list[dict]:
    """Load the same chunk corpus used by the vector index when needed."""
    global CORPUS
    if not CORPUS:
        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    # TODO: Tokenize và tạo BM25 index.
    #
    from rank_bm25 import BM25Okapi
    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Okapi(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    # TODO: Tính BM25 scores và map lại corpus.
    #
    import numpy as np
    corpus = _get_corpus()
    if not corpus or top_k <= 0:
        return []

    bm25 = build_bm25_index(corpus)
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)
    indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for index in indices:
        item = corpus[index]
        lexical_overlap = sum(
            token in item["content"].lower().split() for token in query_tokens
        )
        score = float(scores[index])
        # BM25 can return zero for a tiny corpus; preserve exact keyword hits.
        if score <= 0 and lexical_overlap:
            score = float(lexical_overlap)
        if score <= 0:
            continue
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
