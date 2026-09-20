"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve

load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

# Model mặc định cho từng provider khi .env không khai báo LLM_MODEL.
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-opus-5",
}

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def _model_name() -> str:
    """LLM_MODEL trong .env thắng, nếu trống thì dùng mặc định của provider."""
    return LLM_MODEL or DEFAULT_MODELS.get(LLM_PROVIDER, "")


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)

    # Chunk quan trọng nhất ở đầu, nhì ở cuối; phần giữa kém quan trọng hơn.
    # Model hay bỏ sót thông tin nằm giữa context dài (lost-in-the-middle).
    front = chunks[::2]
    back = chunks[1::2]
    # Trả list mới, không sửa list gốc để caller vẫn giữ đúng thứ tự ranking.
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(
            f"[Document {index} | Title: {metadata['title']} | "
            f"Source: {metadata['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    model = _model_name()
    if not model:
        raise ValueError(f"Chưa cấu hình LLM_MODEL cho provider: {LLM_PROVIDER}")

    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        response = OpenAI().chat.completions.create(
            model=model,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""

    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client()
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return response.text or ""

    if LLM_PROVIDER == "anthropic":
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            # Claude Opus 5 đã bỏ temperature/top_p: gửi vào sẽ bị lỗi 400.
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        if response.stop_reason == "refusal":
            return SAFE_REFUSAL
        return "\n".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: {LLM_PROVIDER}")


def _retrieval_source(chunks: list[dict]) -> str:
    """Map retrieval_method của chunk sang retrieval_source hợp lệ của contract."""
    method = chunks[0].get("retrieval_method")
    if method == "pageindex":
        return "pageindex"
    if method in {"hybrid", "dense", "bm25"}:
        return "hybrid"
    return "none"


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        # Provider lỗi hoặc thiếu API key: trả safe refusal thay vì làm UI crash.
        print(f"LLM unavailable: {error}")
        return {
            "answer": SAFE_REFUSAL,
            "sources": chunks,
            "retrieval_source": _retrieval_source(chunks),
        }

    if not answer.strip():
        answer = SAFE_REFUSAL

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": _retrieval_source(chunks),
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
