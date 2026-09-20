# TEAMMATES

## Thông tin nhóm

- **Nhóm:** K4-L3A
- **Đề tài:** Chatbot RAG trả lời câu hỏi về chính sách và thông tin tuyển sinh đại học
- **Repository:** https://github.com/Cuongluadu25/K4-L3A-RAG-Pipeline
- **Branch chính:** `main`
- **Corpus:** 3 tài liệu chính sách (`data/landing/legal/`) + 8 bài viết (`data/landing/news/`)

## Thành viên và phân công

| # | Họ và tên | Mã học viên | Role | Task phụ trách | Báo cáo cá nhân |
| -: | --------- | ----------- | ---- | -------------- | --------------- |
| 1 | Lê Mạnh Cường | 2A202602604 | Data Lead | Task 1, 2, 3 | `reports/2A202602604_LeManhCuong.md` |
| 2 | Trần Quốc Khánh | `<điền mã HV>` | Index & Dense Retrieval | Task 4, 5 | `reports/<mã HV>-TranQuocKhanh.md` |
| 3 | Nguyễn Việt Hùng | `<điền mã HV>` | Lexical & Fusion | Task 6, 7 | `reports/<mã HV>-NguyenVietHung.md` |
| 4 | Nguyễn Trọng Minh | `<điền mã HV>` | Pipeline & Fallback | Task 8, 9 | `reports/<mã HV>-NguyenTrongMinh.md` |
| 5 | Lê Đức Tùng | 2A202603005 | Generation & UI | Task 10, `app.py` | `reports/<mã HV>-LeDucTung.md` |

**Quy ước:** mã học viên điền vào cả cột trên và tên file báo cáo, theo format `reports/<mã HV>-<TenNgan.md>` như `group_project/ịndividual/INDIVIDUAL_REPORT.md` quy định.

## Chi tiết phân công

### 1. Lê Mạnh Cường — Task 1, 2, 3 (Data)

| Module/deliverable | Việc trực tiếp làm | File/commit |
| ------------------ | ------------------ | ----------- |
| Task 1 — Thu thập tài liệu chính sách | Thu thập 3 PDF công khai (học phí, học bổng, đăng ký tín chỉ, tuyển sinh) | `data/landing/legal/*.pdf` (`0d5af09`, `c932ab8`) |
| Task 2 — Crawl bài viết | Cấu hình 10 URL, crawl bằng Crawl4AI, lưu JSON có `url`/`title`/`date_crawled`/`content_markdown` | `src/task2_crawl_news.py`, `data/landing/news/article_02..09.json` |
| Task 3 — Chuẩn hóa Markdown | `convert_legal_docs()` dùng MarkItDown cho PDF, `convert_news_articles()` chèn metadata header | `src/task3_convert_markdown.py` (`f63dac2`) |

**Đầu ra bàn giao cho các task sau:** `data/standardized/legal/*.md`, `data/standardized/news/article_*.md` — mỗi file giữ `title`, `url`, `doc_type` để Task 10 trích dẫn đối chiếu được với `sources`.

### 2. Trần Quốc Khánh — Task 4, 5 (Chunking, embedding, index, dense search)

| Module/deliverable | Việc trực tiếp làm | File |
| ------------------ | ------------------ | ---- |
| Task 4 — Chunking & indexing | `load_documents()`, `chunk_documents()`, `embed_texts()`, `embed_chunks()`, `get_collection()`, `index_to_vectorstore()` | `src/task4_chunking_indexing.py` |
| Task 5 — Semantic search | `semantic_search()`: query ChromaDB, đổi cosine distance thành similarity | `src/task5_semantic_search.py` |

**Chốt kỹ thuật nhóm đã thống nhất (ghi vào báo cáo nhóm):**
- `CHUNK_SIZE = 500`, `CHUNK_OVERLAP = 50`, `CHUNKING_METHOD = "recursive"`
- Embedding `BAAI/bge-m3`, dim 1024, collection `rag_documents` với `hnsw:space = "cosine"`
- Task 4 và Task 5 **phải dùng chung** `embed_texts()` — contract test `test_semantic_search_uses_shared_embedding_and_contract` kiểm tra điều này

**Ràng buộc cần giữ:** `id` dạng `<đường dẫn>::chunk-<index>`, ổn định để chạy lại không sinh dữ liệu trùng; chunk không rỗng và có `chunk_index`.

### 3. Nguyễn Việt Hùng — Task 6, 7 (BM25, RRF)

| Module/deliverable | Việc trực tiếp làm | File |
| ------------------ | ------------------ | ---- |
| Task 6 — Lexical search | `build_bm25_index()`, `lexical_search()` trên cùng corpus chunks của Task 4 | `src/task6_lexical_search.py` |
| Task 7 — Reciprocal Rank Fusion | `rerank_rrf()` gộp hai bảng xếp hạng theo ID | `src/task7_reranking.py` |

**Ràng buộc cần giữ:**
- RRF dùng đúng công thức `sum(1 / (k + rank))`, `rank` bắt đầu từ **1**, `k = 60`
- RRF **chỉ fuse một lần** (Task 9 chỉ gọi một lần, không fuse lồng nhau)
- RRF chỉ phản ánh thứ hạng — **không** dùng RRF score để quyết định fallback
- Output gộp phải `retrieval_method = "hybrid"`, không trùng ID

### 4. Nguyễn Trọng Minh — Task 8, 9 (Vectorless fallback, retrieval pipeline)

| Module/deliverable | Việc trực tiếp làm | File |
| ------------------ | ------------------ | ---- |
| Task 8 — PageIndex vectorless | `upload_documents()`, `pageindex_search()` trả `retrieval_method = "pageindex"` | `src/task8_pageindex_vectorless.py` |
| Task 9 — Retrieval pipeline | `retrieve()`: dense + BM25 → RRF → so threshold → fallback | `src/task9_retrieval_pipeline.py` |

**Ràng buộc cần giữ:**
- Fallback so threshold với **cosine score gốc của dense search**, không dùng RRF score
- Threshold phải hiệu chỉnh trên cả query **trong domain** và **ngoài domain** — ghi lại con số đã chọn và căn cứ
- PageIndex lỗi không được làm UI crash: pipeline trả hybrid result hoặc safe refusal

### 5. Lê Đức Tùng — Task 10 và UI (Generation có citation)

| Module/deliverable | Việc trực tiếp làm | File |
| ------------------ | ------------------ | ---- |
| Task 10 — Generation | `reorder_for_llm()`, `format_context()`, `call_llm()`, `generate_with_citation()` | `src/task10_generation.py` |
| Chatbot UI | Gọi pipeline, hiển thị answer + nguồn và citation | `app.py` |

**Ràng buộc cần giữ:**
- Reorder chunks nhưng **không làm mất ID**; context có title/source
- Dispatch theo `LLM_PROVIDER` trong `.env`: OpenAI, Gemini hoặc Anthropic Claude
- Không đủ evidence thì trả **safe refusal**, không bịa
- Citation trong answer phải map được về phần tử trong `sources`

## Deliverable dùng chung

| Deliverable | Người chịu trách nhiệm | Ghi chú |
| ----------- | ---------------------- | ------- |
| `group_project/evaluation/golden_dataset.json` | Trần Quốc Khánh | Tối thiểu 15 câu, có ground truth |
| `group_project/evaluation/RESULT.md` | Nguyễn Việt Hùng | 4 metric + A/B dense-only vs hybrid |
| `tests/test_contracts.py`, `tests/test_acceptance.py` | Nguyễn Trọng Minh | Chạy `pytest -q` trước khi push |
| `README.md`, khả năng chạy lại | Lê Đức Tùng | Hướng dẫn chạy end-to-end |
| `reports/<mã HV>-<ten>.md` | Mỗi thành viên | Theo `group_project/ịndividual/INDIVIDUAL_REPORT.md` |

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
| -------- | ---------- |
| Task 1, 2, 3 | Done |
| Task 4 → 10 | Code xong trên nhánh `LeManhCuong` (commit `ba3d405`), **chưa merge vào `main`** — `main` hiện vẫn còn `NotImplementedError` |
| `app.py` tích hợp pipeline | Xong trên `LeManhCuong` (103 dòng), `main` còn là stub TODO |
| `golden_dataset.json` | **Còn rỗng (0 byte)** — cần điền tối thiểu 15 câu |
| `RESULT.md` | **Còn toàn bộ TODO** — cần chạy evaluation thật rồi điền |
| Báo cáo cá nhân | Mới có của Lê Mạnh Cường; 4 người còn lại chưa có |

**Việc cần làm trước khi nộp:** merge `LeManhCuong` vào `main`, chạy lại `pytest -q`, tạo golden dataset, chạy evaluation và điền `RESULT.md`, viết 4 báo cáo cá nhân còn lại.

## Lưu ý về commit

Các commit `f63dac2`, `0d5af09`, `c932ab8`, `70d5b8f`, `ba3d405`, `e18b6ce` hiện ghi tác giả là `Your Name <you@example.com>` (giá trị mặc định, do biến `user.email` cấu hình sai). Cần sửa lại để commit gắn đúng email học viên:

```bash
git config user.name "Lê Mạnh Cường"
git config user.email "<email>"
```

Mỗi thành viên nên commit dưới tên mình để đối chiếu được với báo cáo cá nhân trong buổi demo.
