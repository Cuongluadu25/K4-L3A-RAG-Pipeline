"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re

CORPUS: list[dict] = []

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Tokenize đơn giản, giữ được ký tự có dấu của tiếng Việt."""
    return _TOKEN_PATTERN.findall(text.lower())


def load_corpus() -> list[dict]:
    """Lấy toàn bộ chunks đã index từ ChromaDB — cùng corpus với Task 5."""
    from .task4_chunking_indexing import get_collection

    response = get_collection().get(include=["documents", "metadatas"])
    return [
        {"id": item_id, "content": content, "metadata": metadata}
        for item_id, content, metadata in zip(
            response["ids"], response["documents"], response["metadatas"]
        )
    ]


def refresh_corpus() -> list[dict]:
    """Nạp lại CORPUS từ ChromaDB, bỏ qua nếu collection chưa có dữ liệu."""
    global CORPUS
    try:
        loaded = load_corpus()
    except Exception as error:
        # Chưa index hoặc chưa có ChromaDB: để CORPUS rỗng, không làm crash.
        print(f"Không nạp được corpus cho BM25: {error}")
        return CORPUS

    if loaded:
        CORPUS = loaded
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    tokenized = [tokenize(item["content"]) for item in corpus]
    return BM25Okapi(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if top_k <= 0:
        return []
    # Tự nạp corpus ở lần gọi đầu để không phải build index thủ công.
    if not CORPUS:
        refresh_corpus()
    if not CORPUS:
        return []

    # Build lại index mỗi lần gọi để luôn phản ánh CORPUS hiện tại.
    bm25 = build_bm25_index(CORPUS)
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    ranked = sorted(range(len(CORPUS)), key=lambda index: scores[index], reverse=True)

    results = []
    for index in ranked:
        if len(results) >= top_k:
            break
        # Lọc theo token trùng với query, không lọc theo score: IDF bằng 0 khi
        # corpus nhỏ nên score có thể bằng 0 dù tài liệu thực sự match.
        if not set(tokenize(CORPUS[index]["content"])) & set(query_tokens):
            continue
        item = CORPUS[index]
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(scores[index]),
                "metadata": item["metadata"],
                "retrieval_method": "bm25",
            }
        )
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
