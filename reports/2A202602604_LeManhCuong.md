# Individual contribution report

## Thông tin

- Họ và tên: Lê Mạnh Cường
- Mã học viên: 2A202602604
- Nhóm: AIZone67
- Repository/branch: https://github.com/Cuongluadu25/K4-L3A-RAG-Pipeline - 'main'

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 — Thu thập tài liệu chính sách | Thu thập 3 PDF công khai (học phí, học bổng, đăng ký tín chỉ) từ trang chính sách của trường, lưu vào `data/landing/legal/` | `data/landing/legal/*.pdf` (commit `0d5af09`, `c932ab8`) | Partial |
| Task 2 — Crawl bài viết | Cấu hình 10 URL công khai, crawl bằng Crawl4AI, lưu mỗi bài thành một JSON có `url`/`title`/`date_crawled`/`content_markdown` | `src/task2_crawl_news.py`, `data/landing/news/article_02..09.json` (commit `0d5af09`, `c932ab8`) | Done |
| Task 3 — Chuẩn hóa Markdown | Viết `convert_legal_docs()` dùng MarkItDown cho PDF và `convert_news_articles()` chèn metadata header cho JSON; giữ cấu trúc `legal/` và `news/` | `src/task3_convert_markdown.py` (commit `f63dac2` "Done task 1,2,3") | Partial |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Tải PDF thủ công thay vì viết code `requests.get()` tự động trong Task 1.
   **Lý do/evidence:** Trang nguồn chặn crawler tự động; tôi tải trực tiếp qua trình duyệt để không phải vượt WAF, đúng yêu cầu "không vượt WAF" trong docstring của đề bài. Kết quả: 3 file PDF có kích thước thật (489 KB / 620 KB / 795 KB).
   **Trade-off:** Đổi lấy tính lặp lại — `download_documents()` hiện vẫn `raise NotImplementedError`, người khác clone repo về không chạy lại được Task 1 bằng một lệnh. Đây là lý do tôi đánh dấu Task 1 là **Partial**, không phải Done.

2. **Quyết định:** Với dữ liệu news, giữ metadata thành header Markdown ở đầu file thay vì chỉ đổ phần nội dung thô.
   **Lý do/evidence:** `docs/MODULE_CONTRACTS.md` yêu cầu metadata nguồn (`title`, `url`, `doc_type`) được giữ xuyên suốt pipeline để Task 10 trích dẫn đối chiếu được với `sources`. Header gồm `# {title}`, `**Source:**`, `**Crawled:**` — kiểm chứng được ở đầu mọi file `data/standardized/news/article_*.md`.
   **Trade-off:** Nội dung Markdown bị pha thêm vài dòng không phải nội dung bài gốc, nên khi chunk ở Task 4 cần chấp nhận metadata này nằm trong chunk đầu tiên. Bù lại, truy vết nguồn không cần đọc lại file JSON.

## Kiểm thử và kết quả

- **Test tôi đã dùng:** chạy `python src/task3_convert_markdown.py` rồi đối chiếu số file vào/ra giữa `data/landing/` và `data/standardized/`.
- **Kết quả trước/sau:**

  | Thư mục | Số file | Kích thước |
  |---|---|---|
  | `landing/legal` | 3 PDF | 1.9 MB tổng |
  | `standardized/legal` | 3 MD | 6.5 KB / 35.0 KB / **0 B** |
  | `landing/news` | 8 JSON | 19 K–138 K ký tự/bài |
  | `standardized/news` | 8 MD | 148–1371 dòng |

- **Lỗi đã phát hiện và cách xử lý:**
  - **`data/standardized/legal/Hoc-phi.md` rỗng 0 byte** trong khi `Hoc-phi.pdf` nặng 795 KB. MarkItDown trả `text_content` rỗng cho PDF này (nhiều khả năng là PDF scan ảnh, không có text layer). Vi phạm yêu cầu "không tạo file rỗng" trong docstring Task 3. **Chưa xử lý** — cần thêm OCR (ví dụ `pytesseract`) hoặc thay bằng nguồn PDF có text layer.
  - **Crawl thiếu 2/10 URL.** `ARTICLE_URLS` có 10 phần tử nhưng chỉ sinh `article_02..09.json`, tức URL thứ 1 và thứ 10 thất bại. Hàm `crawl_all()` có `try/except` in ra `Failed:` nhưng **không lưu lại URL lỗi**, nên không đối chiếu được sau khi chạy. Yêu cầu đề bài là tối thiểu 5 URL nên vẫn đạt (8 ≥ 5), nhưng đây là lỗ hổng về khả năng truy vết.
  - **Cảnh báo về danh tính commit:** các commit `f63dac2`, `0d5af09`, `c932ab8` do tôi tạo hiện ghi tác giả là `Your Name <you@example.com>` — đây là giá trị mặc định, do biến `user.email` toàn cục bị cấu hình sai (gõ nhầm `user.eamil`). Cần sửa để commit gắn đúng email học viên.

## Điều còn hạn chế

- **Hạn chế cụ thể:** Task 1 không tái lập được bằng code (`download_documents()` chưa implement), và 1/3 tài liệu legal convert ra file rỗng — nghĩa là nguồn dữ liệu legal hiện chỉ có **2/3 tài liệu dùng được** cho các task sau.
- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** implement `download_documents()` với URL nguồn khai báo trong dict để Task 1 chạy lại được một lệnh, đồng thời thêm bước kiểm tra `len(result.text_content) == 0` trong `convert_legal_docs()` để fail loudly thay vì ghi ra file rỗng im lặng.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-20
- Tên thành viên: Lê Mạnh Cường
