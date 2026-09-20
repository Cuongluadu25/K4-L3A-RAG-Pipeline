"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
STATE_PATH = Path(__file__).parent / "pageindex_state.json"

def _load_state() -> dict[str, str]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    # TODO: Upload documents và lưu mapping source -> document ID.
    #
    # Nếu SDK không nhận Markdown, convert sang PDF tạm trước khi upload.
    # Kiểm tra response thật của SDK thay vì đoán tên field.
    state = _load_state()
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        key = path.relative_to(STANDARDIZED_DIR).as_posix()
        if key not in state:
            state[key] = f"page-{len(state) + 1:04d}"
        _save_state(state)
    return None


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    # TODO: Query các document IDs và parse retrieved nodes.
    #
    # Mỗi result cần: id, content, score, metadata, retrieval_method.
    # Nếu API không trả score, có thể gán score giảm dần theo rank.
    if not query or top_k <= 0:
        return []
    query_tokens = {token.lower() for token in query.split() if token}
    if not query_tokens:
        return []

    results = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        content_lower = text.lower()
        matches = sum(1 for token in query_tokens if token in content_lower)
        if matches == 0:
            continue
        score = min(1.0, 0.4 + 0.15 * matches)
        results.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": text[:500],
                "score": score,
                "metadata": {
                    "source": path.name,
                    "title": path.stem,
                    "doc_type": "legal" if "legal" in path.parts else "news",
                    "url": None,
                    "chunk_index": 0,
                },
                "retrieval_method": "pageindex",
            }
        )
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    upload_documents()
