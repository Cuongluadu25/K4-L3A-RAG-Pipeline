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
# Cache mapping source -> document ID để lần chạy sau không upload lại.
CACHE_PATH = Path(__file__).parent.parent / "pageindex_cache.json"

# PageIndex nhận PDF, không nhận Markdown trực tiếp.
SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx"}


def _client():
    """Tạo PageIndex client, báo lỗi rõ ràng nếu thiếu API key."""
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY chưa được cấu hình trong .env")

    from pageindex import PageIndexClient

    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    cache = _load_cache()
    client = _client()

    # PageIndex cần file PDF gốc nằm trong data/landing/legal.
    landing_dir = Path(__file__).parent.parent / "data" / "landing" / "legal"
    for path in sorted(landing_dir.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.name in cache:
            print(f"Cached: {path.name} -> {cache[path.name]}")
            continue

        response = client.submit_document(file_path=str(path))
        # Kiểm tra field thật của SDK thay vì đoán tên.
        doc_id = response.get("id") or response.get("doc_id")
        if not doc_id:
            print(f"Không lấy được document ID cho {path.name}: {response}")
            continue

        cache[path.name] = doc_id
        print(f"Uploaded: {path.name} -> {doc_id}")

    _save_cache(cache)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0:
        return []

    cache = _load_cache()
    if not cache:
        raise RuntimeError("Chưa có document nào trên PageIndex; chạy upload_documents() trước")

    client = _client()
    results: list[dict] = []

    for source, doc_id in cache.items():
        if len(results) >= top_k:
            break
        # Bỏ qua document chưa index xong thay vì để API báo lỗi.
        if not client.is_retrieval_ready(doc_id):
            continue

        response = client.submit_query(doc_id=doc_id, query=query)
        content = _extract_content(response)
        if not content:
            continue

        metadata = {
            "source": source,
            "title": Path(source).stem,
            "doc_type": "legal",
            "url": "",
            "chunk_index": len(results),
        }
        results.append(
            {
                "id": f"pageindex::{doc_id}::{len(results)}",
                "content": content,
                "score": 0.0,
                "metadata": metadata,
                "retrieval_method": "pageindex",
            }
        )

    # API không trả score, nên gán score giảm dần theo rank để thoả contract
    # "sort giảm dần" mà không ngụ ý so sánh được với cosine.
    total = len(results)
    for index, result in enumerate(results):
        result["score"] = float(total - index)

    return results


def _extract_content(response: dict) -> str:
    """Lấy phần text trả lời từ response của PageIndex."""
    if not isinstance(response, dict):
        return ""
    for key in ("content", "answer", "text", "response"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


if __name__ == "__main__":
    upload_documents()
