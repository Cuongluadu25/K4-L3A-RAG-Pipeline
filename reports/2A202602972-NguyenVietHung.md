# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Việt Hùng
- Mã học viên: 2A202602972
- Nhóm: K4-L3A
- Repository/branch: https://github.com/Cuongluadu25/K4-L3A-RAG-Pipeline - `NguyenVietHung2972`
- Role theo `TEAMMATES.md`: Lexical & Fusion — Task 6, Task 7, `group_project/evaluation/RESULT.md`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 6 — Lexical search (BM25) | Viết `tokenize()` cho tiếng Việt (âm tiết Unicode giữ dấu + bigram âm tiết), `build_bm25_index()` bằng `rank_bm25.BM25Okapi`, `lexical_search()` trả `SearchResult` với `retrieval_method="bm25"`; `load_corpus_from_vectorstore()` nạp `CORPUS` từ chính Chroma collection của Task 4 để BM25 và dense chấm trên cùng tập chunk/ID; cache index, tự dựng lại khi `CORPUS` đổi | `src/task6_lexical_search.py` (nhánh `NguyenVietHung2972`) | Done |
| Task 7 — Reciprocal Rank Fusion | Viết `rerank_rrf()`: `score = Σ 1/(k + rank)`, `rank` từ 1, `k = 60`; ID lặp trong cùng một list chỉ tính lần đầu; giữ nguyên `content`/`metadata` của lần xuất hiện đầu, gắn `retrieval_method="hybrid"`; tie-break xác định (điểm → thứ hạng tốt nhất → thứ tự xuất hiện); lưu score gốc của từng đường vào `metadata["fused_from"]` để debug | `src/task7_reranking.py` (nhánh `NguyenVietHung2972`) | Done |
| `RESULT.md` — Evaluation | Chưa bắt đầu: cần `golden_dataset.json` (Khánh phụ trách, hiện 0 byte) và Task 9/10 merge vào `main` | `group_project/evaluation/RESULT.md` | Blocked |
| Ngoài phân công — sửa dữ liệu Task 1–3 | Phát hiện `standardized/legal/Hoc-phi.md` rỗng 0 byte (PDF scan) → thêm OCR fallback (EasyOCR tiếng Việt) vào `convert_legal_docs()`, đối chiếu tay 11/11 mức thu với bản scan; thêm `SOURCES` + `download_documents()` cho Task 1 (tải tự động được `Hoc-phi.pdf`, hash trùng file gốc); Task 2 dùng selector khung bài theo template site + `PruningContentFilter`, crawl đủ 10/10 URL (trước 8/10, JSON chứa cả menu/footer) | `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `src/task3_convert_markdown.py`, `data/` (nhánh `NguyenVietHung2972`) | Done |
| Ngoài phân công — Task 4, 5 | Implement trong lúc chờ phần của Khánh để có index thật chạy Task 6/7: `load_documents()` tách header metadata khỏi nội dung, chunk id `<path>::chunk-<i>`, `embed_texts()` dispatch theo `EMBEDDING_PROVIDER`, dọn chunk mồ côi khi re-index; `semantic_search()` dùng chung `embed_texts()` | `src/task4_chunking_indexing.py`, `src/task5_semantic_search.py` | Done (chờ đối chiếu với bản của Khánh trên nhánh `LeManhCuong`) |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Tokenizer BM25 dùng âm tiết Unicode (giữ dấu) **cộng thêm bigram âm tiết**, thay vì `text.lower().split()` như starter.
   **Lý do/evidence:** Tiếng Việt viết rời từng âm tiết, "học" và "phí" xuất hiện ở hầu hết chunk nên unigram không phân biệt được. Đo trên corpus thật 734 chunk với query *"mức thu học phí chương trình chuẩn"*: unigram top-3 toàn bài tuyển sinh (`news/article_04::chunk-19`, `article_01::chunk-24`, `article_02::chunk-105`); có bigram top-3 là đúng Quyết định học phí (`legal/Hoc-phi.md::chunk-4/3/6`). `split()` còn dính dấu câu ("phí," ≠ "phí") nên tôi tách bằng `\w+`.
   **Trade-off:** Số token/chunk tăng ~2 lần → dựng index chậm hơn (vẫn < 1 s cho 734 chunk) và query một từ đơn không hưởng lợi. Chấp nhận vì corpus nhỏ và câu hỏi người dùng thường là cụm từ.

2. **Quyết định:** `lexical_search()` lọc kết quả theo **có ít nhất một token trùng với query** thay vì `score > 0`; RRF **không** ghi đè score gốc mà lưu vào `metadata["fused_from"]`.
   **Lý do/evidence:** Với corpus rất nhỏ (contract test dùng 2 chunk) IDF của BM25Okapi bằng 0 → mọi score = 0, lọc `score > 0` trả rỗng dù chunk khớp từ khóa — chính starter cũng fail test này. Lọc theo overlap đúng bản chất lexical và không phụ thuộc kích thước corpus. Về RRF: `docs/MODULE_CONTRACTS.md` cấm dùng RRF score cho fallback; giữ cosine/BM25 gốc trong metadata giúp Task 9 và người debug thấy vì sao một chunk được đẩy lên mà không nhầm hai thang điểm.
   **Trade-off:** Query ngoài domain vẫn có thể trả vài chunk BM25 điểm thấp (ví dụ *"thư viện mở cửa mấy giờ"* → 10.0 so với 40–55 của query trong domain); việc quyết định "không đủ bằng chứng" được đẩy đúng về Task 9 dựa trên dense cosine, không phải BM25.

## Kiểm thử và kết quả

- **Test tôi đã dùng:** `pytest tests/test_contracts.py -q` sau từng module; chạy `python -m src.task6_lexical_search` với 5 query thật trên 734 chunk.
- **Kết quả trước/sau:**

  | Kiểm tra | Trước | Sau |
  |---|---|---|
  | `test_lexical_search_returns_bm25_contract` | `NotImplementedError` → fail (và fail cả khi dùng code gợi ý trong starter vì IDF = 0) | pass |
  | `test_rrf_uses_rank_deduplicates_and_marks_hybrid` (`1/62 + 1/61`, `chunk-1` đứng đầu) | fail | pass |
  | Contract tests tổng | 9/15 pass | 11/15 pass (4 fail còn lại là Task 9/10 của Minh, Tùng) |
  | Query *"770.000 đồng/tín chỉ"* | — | top-1 chunk "Chính sách học phí" (score 42.3) |
  | Query *"học bổng Nguyễn Thanh Bình"* | — | top-1 `news/article_10.md::chunk-3` đúng mục học bổng NTB (47.5) |
  | Query *"đăng ký học phần học kỳ phụ 2"* | — | top-1 thông báo mở/không mở lớp HK phụ 2 (54.4) |

- **Lỗi đã phát hiện và cách xử lý:**
  - Query *"Quyết định 920/QĐ-ĐHCN"* chỉ khớp chunk phụ lục của `Hoc-phi.md`, không khớp trang 1 vì OCR đọc số hiệu thành `9 2 0 'IQĐ-ĐHCN` (bị tách bởi con dấu đỏ). Đã ghi nhận; số hiệu đúng nằm trong `title` metadata nên vẫn truy vết được.
  - `article_02` và `article_03` là cùng một văn bản đăng trên hai site → BM25 trả cặp chunk trùng nội dung với điểm bằng nhau (ví dụ `article_02::chunk-143` và `article_03::chunk-161`). Đã báo nhóm; đề xuất thay `article_03` bằng trang "Quy định tính học phí 2025-2026".
  - Ổ C: đầy khiến tải `BAAI/bge-m3` (2.2 GB) lỗi giữa chừng → chuyển `HF_HOME` sang ổ D: qua `.env` (ghi hướng dẫn vào `.env.example`).

## Điều còn hạn chế

- **Hạn chế cụ thể:** BM25 chưa có stopword tiếng Việt và chưa có tách từ thật (chỉ bigram âm tiết), nên query dài kiểu hội thoại ("cho mình hỏi là...") bị nhiễu bởi các âm tiết chức năng; RESULT.md chưa có số liệu vì golden dataset và pipeline end-to-end chưa merge.
- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** chạy A/B dense-only vs hybrid trên golden dataset để chọn `k` của RRF và ngưỡng fallback bằng số liệu thay vì mặc định `k = 60`, rồi điền `RESULT.md`.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Nguyễn Việt Hùng
