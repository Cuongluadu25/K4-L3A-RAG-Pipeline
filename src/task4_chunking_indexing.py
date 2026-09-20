"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().

Cách làm:
    - load_documents(): tách header metadata (title, Source URL, Doc type) mà
      Task 3 đặt ở đầu mỗi .md ra khỏi nội dung, để chunk chỉ chứa văn bản
      thật; title/url đi theo metadata của mọi chunk.
    - chunk id = "<doc id>::chunk-<index>" — ổn định giữa các lần chạy, upsert
      ghi đè đúng chunk cũ; chunk mồ côi (doc bị rút ngắn/xóa) được dọn khỏi
      collection để không còn dữ liệu cũ lẫn vào retrieval.
    - embed_texts(): dispatch theo EMBEDDING_PROVIDER trong .env, model được
      cache trong process; Task 5 gọi lại đúng hàm này để embed query nên
      model/dimension luôn khớp. Vector được chuẩn hóa L2 nên cosine distance
      trong Chroma là chuẩn.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

from src.contracts import validate_document


ROOT_DIR = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT_DIR / "data" / "standardized"
CHROMA_DIR = ROOT_DIR / "chroma_db"

load_dotenv(ROOT_DIR / ".env")

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"
# Ưu tiên cắt theo đoạn/dòng (văn bản hành chính và bảng OCR đều theo dòng),
# rồi mới đến ranh giới câu/mệnh đề.
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "").strip() or "BAAI/bge-m3"
EMBEDDING_DIM = 1024
EMBEDDING_BATCH_SIZE = 16

COLLECTION_NAME = "rag_documents"
# Chroma giới hạn số bản ghi mỗi lần upsert.
UPSERT_BATCH_SIZE = 1000

_HEADER_FIELD = re.compile(r"^\*\*(?P<key>[^*]+):\*\*\s*(?P<value>.*)$")

_embedding_model = None


# --------------------------------------------------------------------------- #
# Embedding
# --------------------------------------------------------------------------- #
def _embed_sentence_transformers(texts: list[str]) -> list[list[float]]:
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    vectors = _embedding_model.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > EMBEDDING_BATCH_SIZE,
        convert_to_numpy=True,
    )
    return vectors.tolist()


def _embed_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 100):
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts[start:start + 100])
        vectors.extend(item.embedding for item in response.data)
    return vectors


def _embed_gemini(texts: list[str]) -> list[list[float]]:
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 100):
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts[start:start + 100])
        vectors.extend(item.values for item in response.embeddings)
    return vectors


_PROVIDERS = {
    "sentence_transformers": _embed_sentence_transformers,
    "openai": _embed_openai,
    "gemini": _embed_gemini,
}


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed một danh sách text bằng provider trong .env. Dùng chung cho Task 4 và 5."""
    if not texts:
        return []
    try:
        provider = _PROVIDERS[EMBEDDING_PROVIDER]
    except KeyError as error:
        raise ValueError(
            f"EMBEDDING_PROVIDER={EMBEDDING_PROVIDER!r} không hợp lệ; chọn {sorted(_PROVIDERS)}"
        ) from error

    vectors = provider(texts)
    if len(vectors) != len(texts):
        raise RuntimeError(f"embedding trả {len(vectors)} vector cho {len(texts)} text")
    if vectors and len(vectors[0]) != EMBEDDING_DIM:
        raise RuntimeError(
            f"{EMBEDDING_MODEL} trả dimension {len(vectors[0])}, cấu hình EMBEDDING_DIM={EMBEDDING_DIM}"
        )
    return vectors


# --------------------------------------------------------------------------- #
# Vector store
# --------------------------------------------------------------------------- #
def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": EMBEDDING_DIM,
        },
    )
    stored_model = (collection.metadata or {}).get("embedding_model")
    if stored_model and stored_model != EMBEDDING_MODEL:
        raise RuntimeError(
            f"Collection {COLLECTION_NAME!r} được index bằng {stored_model!r}, "
            f"còn .env đang cấu hình {EMBEDDING_MODEL!r}. Xóa {CHROMA_DIR} rồi index lại."
        )
    return collection


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
def _parse_markdown(text: str) -> tuple[dict[str, str], str]:
    """Tách header do Task 3 sinh ("# title", "**Key:** value", "---") khỏi body."""
    fields: dict[str, str] = {}
    lines = text.split("\n")
    body_start = 0
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if index == 0 and line.startswith("# "):
            fields["title"] = line[2:].strip()
            continue
        if line == "---":
            body_start = index + 1
            break
        match = _HEADER_FIELD.match(line)
        if match:
            fields[match.group("key").strip().lower()] = match.group("value").strip()
        elif line and not line.startswith(">") and index > 0:
            # Không phải header chuẩn -> coi toàn bộ file là nội dung.
            return fields, text
    return fields, "\n".join(lines[body_start:]).strip()


def load_documents() -> list[dict]:
    """Đọc Markdown trong data/standardized và trả về danh sách Document."""
    documents: list[dict] = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        fields, body = _parse_markdown(path.read_text(encoding="utf-8"))
        if not body:
            print(f"Skip (empty body): {path.name}")
            continue
        relative = path.relative_to(STANDARDIZED_DIR)
        doc_type = fields.get("doc type") or ("legal" if "legal" in relative.parts else "news")
        document = {
            "id": relative.as_posix(),
            "content": body,
            "metadata": {
                "source": path.name,
                "title": fields.get("title") or path.stem,
                "doc_type": doc_type,
                "url": fields.get("source url") or None,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id ổn định và chunk_index liên tục."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
        length_function=len,
        strip_whitespace=True,
    )
    chunks: list[dict] = []
    for document in documents:
        pieces = [piece for piece in splitter.split_text(document["content"]) if piece.strip()]
        for index, text in enumerate(pieces):
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk, giữ nguyên các field còn lại."""
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def _chroma_metadata(metadata: dict) -> dict:
    """Chroma không nhận giá trị None -> bỏ key; Task 5 khôi phục url=None khi đọc."""
    return {key: value for key, value in metadata.items() if value is not None}


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB và dọn chunk không còn trong corpus."""
    collection = get_collection()
    for start in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[start:start + UPSERT_BATCH_SIZE]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in batch],
        )

    current_ids = {chunk["id"] for chunk in chunks}
    stale_ids = [item_id for item_id in collection.get(include=[])["ids"] if item_id not in current_ids]
    if stale_ids:
        collection.delete(ids=stale_ids)
        print(f"Removed {len(stale_ids)} stale chunks")


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    print(f"Loaded {len(documents)} documents from {STANDARDIZED_DIR}")
    chunks = chunk_documents(documents)
    lengths = [len(chunk["content"]) for chunk in chunks]
    print(
        f"Chunked into {len(chunks)} chunks "
        f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}, method={CHUNKING_METHOD}; "
        f"min/avg/max chars = {min(lengths)}/{sum(lengths) // len(lengths)}/{max(lengths)})"
    )
    print(f"Embedding with {EMBEDDING_PROVIDER}:{EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks -> collection {COLLECTION_NAME!r} "
          f"now holds {get_collection().count()} chunks at {CHROMA_DIR}")


if __name__ == "__main__":
    run_pipeline()
