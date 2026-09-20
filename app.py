import os
import streamlit as st
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from src.task10_generation import generate_with_citation

load_dotenv()

st.set_page_config(
    page_title="HaUI Assistant — RAG Chatbot",
    page_icon="🎓",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🎓 HaUI RAG Chatbot")
    st.markdown(
        "Hệ thống hỏi đáp thông minh dựa trên tài liệu tuyển sinh, quy chế học bổng "
        "và hướng dẫn đăng ký tín chỉ của **Trường Đại học Công nghiệp Hà Nội**."
    )
    st.divider()

    top_k = st.slider("Số lượng chunks tham khảo (top_k)", min_value=3, max_value=10, value=5)

    st.subheader("Cấu hình hệ thống")
    st.caption(f"• **Embedding Model:** `{os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2').split('/')[-1]}`")
    st.caption(f"• **LLM Model:** `{os.getenv('LLM_MODEL', 'gemini-2.5-flash')}`")
    st.caption("• **Retrieval Strategy:** `Hybrid (Dense + BM25 via RRF)`")
    st.caption(f"• **Fallback Threshold:** `{os.getenv('SCORE_THRESHOLD', '0.3')}`")

    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🎓 Trợ lý Thông tin & Tuyển sinh HaUI")
st.caption("Hỏi đáp tức thì về quy chế tuyển sinh, tiêu chuẩn xét học bổng, tiến độ đăng ký tín chỉ và chương trình đào tạo.")

def render_sources(sources: list[dict], retrieval_source: str):
    """Hiển thị danh sách nguồn trích dẫn kèm score và retrieval method."""
    if not sources:
        return
    with st.expander(f"📚 Nguồn tài liệu tham khảo ({len(sources)} chunks | Phương thức: {retrieval_source.upper()})"):
        for index, src in enumerate(sources, 1):
            metadata = src.get("metadata", {})
            title = metadata.get("title", "Không rõ tiêu đề")
            source_file = metadata.get("source", "Tài liệu")
            method = src.get("retrieval_method", "hybrid")
            score = src.get("score", 0.0)
            url = metadata.get("url")

            st.markdown(f"**[{index}] {title}** (`{source_file}`)")
            col1, col2 = st.columns([1, 3])
            with col1:
                st.caption(f"• Phương thức: `{method}` | Điểm: `{score:.4f}`")
            with col2:
                if url:
                    st.caption(f"• Link: [{url}]({url})")

            st.text_area(
                f"Nội dung chunk [{index}]",
                value=src.get("content", "").strip(),
                height=90,
                key=f"chunk_view_{src.get('id', index)}_{index}",
                disabled=True,
            )
            st.divider()

# Hiển thị các tin nhắn cũ
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "sources" in message:
            render_sources(message.get("sources", []), message.get("retrieval_source", "hybrid"))

# Xử lý input từ người dùng
query = st.chat_input("Nhập câu hỏi của bạn (ví dụ: Điều kiện xét học bổng khuyến khích học tập?)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm thông tin và tổng hợp câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
            answer = result["answer"]
            sources = result.get("sources", [])
            retrieval_source = result.get("retrieval_source", "hybrid")

            st.markdown(answer)
            render_sources(sources, retrieval_source)

    # Lưu lại vào session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
