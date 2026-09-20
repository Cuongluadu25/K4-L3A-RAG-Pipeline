import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="R",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Tra cứu thông tin từ bộ tài liệu đã thu thập")
    top_k = st.slider("Số chunks", 3, 10, 5)

st.title("RAG Chatbot")
st.caption("Câu trả lời được tạo từ các nguồn trong corpus của nhóm")


def render_sources(message: dict) -> None:
    """Display retrieval metadata and citations attached to a response."""
    sources = message.get("sources", [])
    retrieval_source = message.get("retrieval_source", "none")

    st.caption(f"Phương thức truy xuất: {retrieval_source}")
    if not sources:
        return

    with st.expander(f"Nguồn tham khảo ({len(sources)})"):
        for index, source in enumerate(sources, 1):
            metadata = source.get("metadata", {})
            title = metadata.get("title", "Không có tiêu đề")
            source_name = metadata.get("source", "Không rõ nguồn")
            score = source.get("score", 0.0)
            url = metadata.get("url")
            source_label = f"[{index}] {title} - {source_name}"
            if url:
                st.markdown(
                    f"**{source_label}**  \n"
                    f"Score: `{float(score):.3f}` | [Mở nguồn]({url})"
                )
            else:
                st.markdown(
                    f"**{source_label}**  \n"
                    f"Score: `{float(score):.3f}`"
                )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message)

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        try:
            result = generate_with_citation(query, top_k)
        except Exception as error:
            result = {
                "answer": "Tôi không thể xử lý câu hỏi lúc này. Vui lòng thử lại sau.",
                "sources": [],
                "retrieval_source": "none",
            }
            st.error(f"Không thể hoàn tất truy xuất: {error}")

        answer = result["answer"]
        sources = result["sources"]
        retrieval_source = result["retrieval_source"]
        st.markdown(answer)
        assistant_message = {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": retrieval_source,
        }
        render_sources(assistant_message)

    st.session_state.messages.append(assistant_message)
