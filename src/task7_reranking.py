"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

Cách làm:
    - Mỗi ranked list đóng góp 1/(k + rank) cho từng ID; ID xuất hiện ở
      nhiều list được cộng dồn nên tự nhiên được đẩy lên (đồng thuận giữa
      dense và BM25).
    - Nếu một ID lặp trong cùng một list chỉ tính lần xuất hiện đầu (rank
      tốt nhất) để không cộng trùng.
    - Kết quả giữ nguyên content/metadata của lần xuất hiện đầu tiên, gắn
      retrieval_method="hybrid"; score gốc (cosine/BM25) được lưu vào
      metadata "fused_from" để debug, không dùng cho fallback.
    - Tie-break khi bằng điểm: ID có thứ hạng tốt nhất thấp hơn đứng trước,
      rồi đến thứ tự xuất hiện — kết quả xác định giữa các lần chạy.
"""

from .contracts import validate_search_results


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    if top_k <= 0 or k < 0:
        return []

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    best_rank: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    origins: dict[str, list[str]] = {}

    for ranked_list in ranked_lists:
        seen_in_list: set[str] = set()
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            if item_id in seen_in_list:
                continue
            seen_in_list.add(item_id)

            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            best_rank[item_id] = min(best_rank.get(item_id, rank), rank)
            if item_id not in items:
                items[item_id] = item
                first_seen[item_id] = len(first_seen)
            origins.setdefault(item_id, []).append(
                f"{item.get('retrieval_method', '?')}#{rank}={float(item.get('score', 0.0)):.4f}"
            )

    ranked_ids = sorted(
        scores,
        key=lambda item_id: (-scores[item_id], best_rank[item_id], first_seen[item_id]),
    )

    results: list[dict] = []
    for item_id in ranked_ids[:top_k]:
        source = items[item_id]
        results.append({
            "id": item_id,
            "content": source["content"],
            "score": scores[item_id],
            "metadata": {**source["metadata"], "fused_from": ", ".join(origins[item_id])},
            "retrieval_method": "hybrid",
        })

    validate_search_results(results, top_k=top_k, expected_method="hybrid")
    return results


if __name__ == "__main__":
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search

    query = "Học phí một tín chỉ chương trình đào tạo chuẩn năm học 2026-2027"
    dense = semantic_search(query, top_k=10)
    sparse = lexical_search(query, top_k=10)
    print(f"dense top: {[item['id'] for item in dense[:3]]}")
    print(f"bm25  top: {[item['id'] for item in sparse[:3]]}")
    for result in rerank_rrf([dense, sparse], top_k=5, k=60):
        print(f"  {result['score']:.5f}  {result['id']:<32} <- {result['metadata']['fused_from']}")
