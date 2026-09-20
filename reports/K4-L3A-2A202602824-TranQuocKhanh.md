# Individual contribution report

## Thông tin

- Họ và tên: Trần Quốc Khánh
- Mã học viên: 2A202602824
- Nhóm: K4-L3A
- Repository/branch: https://github.com/Cuongluadu25/K4-L3A-RAG-Pipeline - `tqkhanh`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 4 — Chunking & indexing | Thiết kế và triển khai `load_documents()`, `chunk_documents()`, `embed_chunks()`, `index_to_vectorstore()`; đảm bảo chunk id ổn định theo `source::chunk-index` và lưu vào Chroma với cosine space | `src/task4_chunking_indexing.py` | Done |
| Task 5 — Dense semantic search | Triển khai search trên ChromaDB với cosine similarity, đồng bộ cùng shared embedding function và schema `SearchResult` | `src/task5_semantic_search.py` | Done |
| Golden dataset | Soạn và rà soát dataset 15 câu tương ứng với corpus thực, bao gồm `question`, `expected_answer`, `expected_context` | `group_project/evaluation/golden_dataset.json` | Done |
| Validation & regression check | Chạy contract/acceptance tests để đảm bảo pipeline và evaluation report không còn TODO và project chạy end-to-end | `tests/test_contracts.py`, `tests/test_acceptance.py`, `group_project/evaluation/RESULT.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng chung một hàm embedding cho Task 4 và Task 5, thay vì tạo nhiều mô hình/flow riêng.
   **Lý do/evidence:** Contract test kiểm tra `embed_texts()` phải được dùng độc lập, giúp dữ liệu chunk và query cùng một không gian vector; file triển khai nằm trong `src/task4_chunking_indexing.py` và `src/task5_semantic_search.py`.
   **Trade-off:** Tăng độ phụ thuộc giữa hai module nhưng giảm sai lệch vector, đồng thời đơn giản hóa debug và duy trì tính nhất quán.

2. **Quyết định:** Dùng id ổn định cho chunk theo định dạng `<relative_path>::chunk-<index>`.
   **Lý do/evidence:** Mỗi chunk có identity duy nhất, chạy lại pipeline không tạo dữ liệu trùng lặp và dễ map trả về source/citation; công việc này là căn cứ trong `chunk_documents()` và `index_to_vectorstore()`.
   **Trade-off:** Cần giữ metadata rõ ràng và không thay đổi cấu trúc corpus, nhưng giúp tái tạo index ổn định trong demo và evaluation.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest -q`
  - `pytest tests/test_contracts.py -q`
  - `pytest tests/test_acceptance.py -q`
- Kết quả trước/sau nếu có:
  - Sau khi hoàn thiện pipeline và dữ liệu, toàn bộ suite đã pass: `20 passed in 7.18s`.
- Lỗi đã phát hiện và cách xử lý:
  - Several gaps in the repo were template/TODO placeholders; I verified the contract and filled the actual deliverable files accordingly.
  - The main technical issue in retrieval logic was BM25 fallback when tiny corpora returned zero scores; this was corrected to retain exact keyword hits without breaking contract tests.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm:
  - Dense/BM25 retrieval trên corpus nhỏ vẫn phụ thuộc nhiều vào token normalization và cách đánh giá proxy offline, nên độ chính xác có thể thấp với câu hỏi biến thể ngữ nghĩa.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:
  - Bổ sung chuẩn hóa từ vựng tiếng Việt và cải thiện filtering boilerplate trước khi chunking để tăng context precision và recall.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Trần Quốc Khánh
