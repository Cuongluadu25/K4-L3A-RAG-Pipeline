"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if os.getenv("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT")

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

# Provider/model đọc từ .env để Task 4 và Task 5 luôn dùng chung một cấu hình.
# Mặc định là model multilingual nhỏ (384 dim) cho phù hợp máy CPU.
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
).strip()

# Dimension của EMBEDDING_MODEL. Đổi model thì phải đổi cả hằng số này và .env.
EMBEDDING_DIM = 384

COLLECTION_NAME = "rag_documents"

_MODEL = None


def _get_sentence_transformer():
    """Nạp model local một lần duy nhất cho cả process."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer(EMBEDDING_MODEL)
    return _MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed một batch text bằng provider duy nhất của pipeline."""
    if not texts:
        return []

    if EMBEDDING_PROVIDER == "sentence_transformers":
        model = _get_sentence_transformer()
        # normalize_embeddings để cosine similarity nằm trong [-1, 1] ổn định.
        return model.encode(texts, normalize_embeddings=True).tolist()

    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI()
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]

    if EMBEDDING_PROVIDER == "gemini":
        from google import genai

        client = genai.Client()
        vectors = []
        for text in texts:
            response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
            vectors.append(list(response.embeddings[0].values))
        return vectors

    raise ValueError(f"EMBEDDING_PROVIDER không hỗ trợ: {EMBEDDING_PROVIDER}")


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


_TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_SOURCE_PATTERN = re.compile(r"^\*\*Source:\*\*\s*(\S+)\s*$", re.MULTILINE)


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document theo contract."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        # File rỗng (ví dụ PDF scan convert ra 0 ký tự) không phải Document hợp lệ.
        if not content.strip():
            continue

        doc_type = "legal" if "legal" in path.parts else "news"
        title_match = _TITLE_PATTERN.search(content)
        source_match = _SOURCE_PATTERN.search(content)

        documents.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": title_match.group(1).strip() if title_match else path.stem,
                    "doc_type": doc_type,
                    # Bài news có URL trong header; tài liệu legal thì không.
                    "url": source_match.group(1).strip() if source_match else None,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for document in documents:
        kept_index = 0
        for text in splitter.split_text(document["content"]):
            # Bỏ chunk chỉ có khoảng trắng: contract yêu cầu content không rỗng.
            if not text.strip():
                continue
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{kept_index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": kept_index},
                }
            )
            kept_index += 1
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def _sanitize_metadata(metadata: dict) -> dict:
    """Chroma chỉ nhận str/int/float/bool, nên None phải đổi thành chuỗi rỗng."""
    return {key: ("" if value is None else value) for key, value in metadata.items()}


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return

    collection = get_collection()
    # upsert theo id ổn định nên chạy lại pipeline không tạo dữ liệu trùng.
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[_sanitize_metadata(chunk["metadata"]) for chunk in chunks],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
