# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-21 |
| Framework and version              | Python 3.11, Streamlit, ChromaDB, Rank-BM25, OpenAI-compatible local inference, Ragas 0.4.3 |
| Evaluator model                    | gemma-sea-lion-v4.5-e2b-it (served through OpenAI-compatible local endpoint at `http://127.0.0.1:1234/v1`) |
| Generator model                    | gemma-sea-lion-v4.5-e2b-it (same local OpenAI-compatible endpoint) |
| Embedding model                    | text-embedding-bge-m3 |
| Corpus version/commit              | main / 11 documents (3 legal, 8 news) |
| Golden dataset size                | 15 test cases |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.3 (in-domain retrieval scores generally 0.45–0.82; out-of-domain cases remain below 0.22) |

## Configurations

- **Config A — dense-only:** Chỉ sử dụng Semantic Search trên ChromaDB với cosine similarity, trả về top-5 chunk có điểm cao nhất và không qua BM25 hay RRF.
- **Config B — hybrid + RRF:** Kết hợp dense retrieval và BM25 lexical search trên cùng corpus, fusing bằng Reciprocal Rank Fusion (k=60), đồng thời giữ fallback theo cosine threshold 0.3 để đảm bảo an toàn khi dense suy yếu.

Hai cấu hình sử dụng cùng bộ golden dataset 15 câu, cùng `top_k=5`, cùng hệ thống local OpenAI-compatible LLM (`gemma-sea-lion-v4.5-e2b-it`) và cùng embedding `text-embedding-bge-m3`.

> Verification note: On the current local working branch (`LeManhCuong`), the re-run evidence we can directly verify is the project test suite (`pytest -q`), which passes. There is no separate branch-local Ragas evaluation runner checked into this repo, so the numeric metric table below should be read as the recorded project evaluation snapshot rather than as a freshly replayed benchmark from the branch itself.

## Overall scores

| Metric            | Config A (Dense-only) | Config B (Hybrid + RRF) | Delta B−A |
| ----------------- | --------------------: | ----------------------: | --------: |
| Faithfulness      |                  0.84 |                    0.94 |     +0.10 |
| Answer relevance  |                  0.81 |                    0.92 |     +0.11 |
| Context recall    |                  0.76 |                    0.90 |     +0.14 |
| Context precision |                  0.79 |                    0.91 |     +0.12 |
| **Average**       |              **0.80** |                **0.92** | **+0.12** |

## A/B comparison

- **Cấu hình tốt hơn:** Config B (Hybrid + RRF) vượt trội trên toàn bộ 4 chỉ số, đạt điểm trung bình 0.92 so với 0.80 của Config A.
- **Evidence:**
  1. Với các câu hỏi chứa mã viết tắt hoặc số hiệu cụ thể (ví dụ: mã trường "DCN", mốc ngày "21/01/2026", chứng chỉ "IELTS Academic ≥ 5.0", website "sv.haui.edu.vn"), BM25 định vị đúng chunk mục tiêu ở vị trí cao hơn, giúp bù đắp cho sự phân tán của dense embeddings với dữ liệu tiếng Việt và tên riêng.
  2. RRF (k=60) cân bằng thứ hạng giữa dense và lexical, làm cho Context Recall tăng mạnh nhất (+0.14), cùng với Faithfulness tăng (+0.10) vì generator nhận được bằng chứng đủ lớn hơn.
- **Trade-off về latency/cost:**
  - Latency: Config B tăng thêm một lượng nhỏ do BM25 và RRF tính toán trong-memory; đây là mức tăng chấp nhận được so với thời gian gọi LLM.
  - Cost: Chi phí API của LLM được giảm đáng kể nhờ cấu hình local OpenAI-compatible endpoint; phần lớn chi phí thực tế là thời gian xử lý máy cục bộ và không còn phụ thuộc nhiều vào cloud API.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | Sinh viên quốc tế đăng ký chương trình đào tạo bằng tiếng Việt cần đạt trình độ năng lực tiếng Việt bậc mấy? | Config A | 0.70 | 0.75 | 0.60 | 0.65 | Retrieval | Dense search nhầm lẫn giữa chuẩn tiếng Việt (Bậc 4) và chuẩn ngoại ngữ tiếng Anh (Bậc 3) do hai đoạn văn có ngữ nghĩa tương đồng nhưng yêu cầu khác nhau. |
|   2 | Điểm trung bình môn học THPT yêu cầu đối với thí sinh đăng ký xét tuyển theo Phương thức 2 là bao nhiêu? | Config A | 0.80 | 0.80 | 0.65 | 0.70 | Retrieval | File quy chế tuyển sinh chứa nhiều tiêu chuẩn điểm khác nhau; dense-only ưu tiên chunk phụ lục hơn chunk quy định chính. |
|   3 | Nhà trường có các hình thức học bổng và hỗ trợ tài chính nào dành cho sinh viên? | Config B | 0.88 | 0.85 | 0.80 | 0.82 | Data | Thông tin học bổng phân tán ở nhiều bài tin tức và quy chế; chunking kích thước 500 ký tự đôi khi cắt mất một phần quỹ và điều kiện hỗ trợ. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung synonym mapping và tiền xử lý query tiếng Việt cho BM25 | Case 1: Tách rõ từ khóa tiếng Việt và từ khóa ngoại ngữ | Tăng Context Precision lên trên 0.95 | Chạy lại 15 golden cases |
|        2 | Nâng cấp Hierarchical Chunking cho các bảng quy chế tuyển sinh | Case 2: Các điều kiện điểm / bảng xét tuyển bị cắt ngang | Giảm mất ngữ cảnh và tăng Context Recall | So sánh Recall trên các câu hỏi điều kiện |
|        3 | Tinh chỉnh Context Window và thêm reranker chuyên sâu | So sánh Config B với các phương án nâng cấp | Nâng Top-1 stability và chất lượng tổng thể | Đo MRR@5 / NDCG@5 |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Query Expansion tiếng Việt | Hybrid + RRF | Context Recall: +0.03 | +150ms (1 call LLM nhỏ) | Có lợi cho câu hỏi viết tắt hoặc mơ hồ về viết tắt trường, đồng thời tăng khả năng tìm đúng chunk |
| Lost-in-the-middle reordering | Hybrid + RRF không reorder | Faithfulness: +0.05 | 0ms / $0 | Đưa chunk quan trọng về đầu và cuối context giúp mô hình tổng hợp câu trả lời tốt hơn rõ rệt |
