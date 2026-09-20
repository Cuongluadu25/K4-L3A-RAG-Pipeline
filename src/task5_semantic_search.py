"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.

Score = 1 - cosine_distance (Chroma trả distance trong [0, 2] với vector đã
chuẩn hóa), cắt về [0, 1] để Task 9 so threshold trên thang similarity.
"""

from .contracts import validate_search_results
from .task4_chunking_indexing import embed_texts, get_collection


def _restore_metadata(metadata: dict) -> dict:
    """Chroma không lưu None nên url bị bỏ khi index -> khôi phục theo contract."""
    restored = dict(metadata or {})
    restored.setdefault("url", None)
    return restored


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if top_k <= 0 or not query.strip():
        return []

    collection = get_collection()
    n_results = top_k
    count = getattr(collection, "count", None)
    if callable(count):
        # Chroma báo lỗi/cảnh báo khi n_results lớn hơn số bản ghi hiện có.
        n_results = max(1, min(top_k, count()))

    query_vector = embed_texts([query])[0]
    response = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    results: list[dict] = []
    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        results.append({
            "id": item_id,
            "content": content,
            "score": round(min(1.0, max(0.0, 1.0 - float(distance))), 6),
            "metadata": _restore_metadata(metadata),
            "retrieval_method": "dense",
        })

    results.sort(key=lambda item: item["score"], reverse=True)
    results = results[:top_k]
    validate_search_results(results, top_k=top_k, expected_method="dense")
    return results


if __name__ == "__main__":
    queries = [
        "Học phí một tín chỉ chương trình chuẩn năm học 2026-2027 là bao nhiêu?",
        "Điều kiện để nhận học bổng khuyến khích học tập",
        "Thời gian đăng ký học phần học kỳ 2 năm học 2025-2026",
    ]
    for query in queries:
        print(f"\n### {query}")
        for result in semantic_search(query, top_k=3):
            meta = result["metadata"]
            print(f"  {result['score']:.4f}  {result['id']:<32} [{meta['doc_type']}] {meta['title'][:60]}")
            print(f"          {result['content'][:120]!r}")
