# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.4.3, LangChain 1.4.2 |
| Evaluator model                    | gemini-2.5-flash |
| Generator model                    | gemini-2.5-flash |
| Embedding model                    | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Corpus version/commit              | main / 11 documents (3 legal, 8 news) |
| Golden dataset size                | 15 test cases |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.3 (In-domain score 0.45 - 0.82; Out-of-domain score < 0.22) |

## Configurations

- **Config A — dense-only:** Chỉ sử dụng Semantic Search từ ChromaDB với cosine similarity, trả về top-5 chunk điểm cao nhất không qua BM25 hay RRF.
- **Config B — hybrid + RRF:** Kết hợp Semantic Search (ChromaDB) và Lexical Search (BM25Okapi) trên cùng corpus, gộp bảng xếp hạng qua Reciprocal Rank Fusion (k=60), kiểm tra cosine threshold 0.3 để kích hoạt fallback an toàn.

Hai config sử dụng cùng bộ golden dataset 15 câu, cùng generator model `gemini-2.5-flash`, cùng system prompt và cùng `top_k=5`.

## Overall scores

| Metric            | Config A (Dense-only) | Config B (Hybrid + RRF) | Delta B−A |
| ----------------- | --------------------: | ----------------------: | --------: |
| Faithfulness      |                  0.84 |                    0.94 |     +0.10 |
| Answer relevance  |                  0.81 |                    0.92 |     +0.11 |
| Context recall    |                  0.76 |                    0.90 |     +0.14 |
| Context precision |                  0.79 |                    0.91 |     +0.12 |
| **Average**       |              **0.80** |                **0.92** | **+0.12** |

## A/B comparison

- **Cấu hình tốt hơn:** Config B (Hybrid + RRF) vượt trội trên toàn bộ 4 thang đo đánh giá, đạt điểm trung bình 0.92 so với 0.80 của Config A.
- **Evidence:** 
  1. Với các câu hỏi chứa mã viết tắt hoặc số hiệu cụ thể (ví dụ: mã trường "DCN", mốc ngày "21/01/2026", chứng chỉ "IELTS Academic ≥ 5.0", website "sv.haui.edu.vn"), BM25 định vị chính xác chunk mục tiêu ở vị trí số 1, giúp bù đắp sự phân tán vector của embedding multilingual khi gặp từ viết tắt.
  2. RRF (k=60) cân bằng mượt mà thứ hạng giữa dense và lexical, giúp Context Recall tăng mạnh nhất (+0.14), kéo theo Faithfulness tăng (+0.10) do mô hình generator nhận đủ bằng chứng context.
- **Trade-off về latency/cost:** 
  - Latency: Config B tăng thêm khoảng 12ms trên mỗi lượt truy vấn (thời gian tokenize BM25 và tính điểm RRF in-memory). Đây là mức đánh đổi hoàn toàn chấp nhận được so với độ trễ gọi LLM (~800ms - 1.5s).
  - Cost: Chi phí gọi LLM không đổi do context được cắt gọt chuẩn ở cùng `top_k=5`.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | Sinh viên quốc tế đăng ký chương trình đào tạo bằng tiếng Việt cần đạt trình độ năng lực tiếng Việt bậc mấy? | Config A | 0.70 | 0.75 | 0.60 | 0.65 | Retrieval | Dense search nhầm lẫn giữa chuẩn tiếng Việt (Bậc 4) và chuẩn ngoại ngữ tiếng Anh (Bậc 3) do hai đoạn văn có ngữ nghĩa vector gần nhau. Config B khắc phục nhờ từ khóa BM25 "tiếng Việt" và "Bậc 4". |
|   2 | Điểm trung bình môn học THPT yêu cầu đối với thí sinh đăng ký xét tuyển theo Phương thức 2 là bao nhiêu? | Config A | 0.80 | 0.80 | 0.65 | 0.70 | Retrieval | File quy chế tuyển sinh có nhiều tiêu chuẩn điểm (điểm thi THPT >= 15, điểm từng môn >= 7.0). Dense-only xếp chunk phụ lục lên trước chunk quy định chính. |
|   3 | Nhà trường có các hình thức học bổng và hỗ trợ tài chính nào dành cho sinh viên? | Config B | 0.88 | 0.85 | 0.80 | 0.82 | Data | Thông tin học bổng phân tán ở nhiều bài tin tức và quy chế khác nhau; chunking size 500 ký tự khiến một số quỹ học bổng doanh nghiệp nhỏ không nằm trọn trong 1 chunk. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung synonym mapping và tiền xử lý query tiếng Việt cho BM25 | Case 1: Tách rõ từ khóa tiếng Việt và từ khóa ngoại ngữ | Tăng Context Precision lên > 0.95 | Chạy lại test suite 15 golden cases |
|        2 | Nâng cấp Hierarchical Chunking (Small-to-Big) cho các bảng quy chế tuyển sinh | Case 2: Các bảng điều kiện tuyển sinh dạng bảng bị cắt vụn qua RecursiveCharacterSplitter | Giảm hiện tượng mất ngữ cảnh điều kiện đi kèm | Đo lường Context Recall trên các câu hỏi điều kiện |
|        3 | Tinh chỉnh Context Window & Reranker Cross-Encoder chuyên sâu (BGE-reranker-v2-m3) | So sánh Config B với reranker chuyên dụng | Nâng thứ hạng chunk quan trọng nhất lên Top 1 ổn định hơn RRF | Đánh giá qua metric MRR@5 và NDCG@5 |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Query Expansion tiếng Việt (tự động mở rộng từ viết tắt HaUI -> Đại học Công nghiệp Hà Nội) | Hybrid + RRF | Context Recall: +0.03 | +150ms (1 call LLM nhỏ) | Hiệu quả với câu hỏi ngắn người dùng gõ tắt, phù hợp áp dụng vào chatbot thực tế |
| Tối ưu hóa Lost-in-the-Middle Reordering | Hybrid + RRF không reorder | Faithfulness: +0.05 | 0ms / $0 | Đưa chunk quan trọng về đầu và cuối context giúp LLM nắm bắt bằng chứng tốt hơn rõ rệt |
