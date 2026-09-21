# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Trọng Minh
- Mã học viên: 2A202602496
- Nhóm: AIZone67
- Repository/branch: https://github.com/Cuongluadu25/K4-L3A-RAG-Pipeline/tree/ntminh

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Team oversight / technical advisor | Theo dõi tiến độ toàn nhóm, định hướng chủ đề dữ liệu và chatbot, hỗ trợ rà soát hướng đi kỹ thuật để đảm bảo sản phẩm đi đúng yêu cầu và không lệch mục tiêu | repo / working branch `ntminh` | Done |
| Topic selection and product direction | Chọn chủ đề dữ liệu và định hình chatbot theo hướng hỏi đáp về tuyển sinh, học bổng, đăng ký tín chỉ và thông tin đào tạo của HaUI | `README.md`, `data/landing/*`, `app.py` | Done |
| Ngoài phân công — custom local LLM base URL | Điều chỉnh Task 4 và Task 10 để sử dụng `OPENAI_BASE_URL`/OpenAI-compatible local API hosting, giảm phụ thuộc vào cloud API, giảm tính trùng lặp và phù hợp với môi trường lab cục bộ | `src/task4_chunking_indexing.py`, `src/task10_generation.py` | Done |
| Review for later group labs | Chuẩn bị hướng dẫn và review kỹ thuật để các lab sau triển khai lại cấu hình local inference thống nhất, tránh lặp lại việc gọi API cloud không cần thiết | team implementation review | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng OpenAI-compatible local endpoint cho LLM thay vì phụ thuộc trực tiếp vào API cloud.
   **Lý do/evidence:** Trong `.env`, nhóm cấu hình `OPENAI_BASE_URL=http://127.0.0.1:1234/v1`, `LLM_PROVIDER=openai`, `LLM_MODEL=gemma-sea-lion-v4.5-e2b-it`, và `OPENAI_API_KEY` được giữ ở dạng local key. Điều này cho phép pipeline chạy trên máy cục bộ mà vẫn giữ giao diện OpenAI chuẩn của code.
   **Trade-off:** Tăng sự phụ thuộc vào môi trường local endpoint và cần đảm bảo server LLM đang chạy trước khi gọi; nhưng bù lại giảm chi phí API cloud và phù hợp với mô hình lab / demo cục bộ.

2. **Quyết định:** Chốt chủ đề dữ liệu và định hướng chatbot theo các tài liệu tuyển sinh, học bổng và đăng ký tín chỉ của HaUI.
   **Lý do/evidence:** Chủ đề này phù hợp với dữ liệu công khai, dễ kiểm tra bằng golden dataset, có đủ nguồn chính sách và tin tức để đánh giá retrieval và generation. Tôi cũng giám sát tiến độ để tránh bị lệch khỏi mục tiêu lab.
   **Trade-off:** Bản chất dữ liệu có nhiều chính sách và tiêu chuẩn chồng chéo, nên cần cẩn thận khi đánh giá retrieval và câu hỏi out-of-domain; tuy nhiên, độ phù hợp với bài toán RAG cao hơn và dễ demo cho giảng viên hơn.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest -q`
  - Smoke query via chatbot: “Điều kiện xét học bổng khuyến khích học tập?”
  - Smoke query: “Thời gian đăng ký học tập đợt chính thức…”
- Kết quả trước/sau nếu có:
  - Contract và acceptance tests đạt trạng thái pass trên repo hiện tại.
  - Chatbot trả lời có nguồn, và local OpenAI-compatible endpoint hoạt động ổn định trong môi trường lab.
- Lỗi đã phát hiện và cách xử lý:
  - Đầu tiên có nguy cơ phụ thuộc quá nhiều vào API cloud; tôi đề xuất và triển khai cấu hình local endpoint để giảm redundancy và tăng khả năng chạy lại.
  - Sau khi điều chỉnh base URL và cấu hình provider, bộ RAG có thể chạy trên môi trường local mà vẫn giữ chuẩn OpenAI và không làm thay đổi logic retrieval/generation chính.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm:
  - Vai trò giám sát kỹ thuật và điều chỉnh base URL giúp nhóm tiết kiệm thời gian, nhưng chưa trực tiếp xử lý toàn bộ các task dữ liệu / crawl / chuẩn hóa ở mức tác nghiệp chi tiết.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:
  - Tiếp tục chuẩn hóa cấu hình local inference cho các lab tiếp theo, đồng thời xây dựng checklist kiểm tra môi trường local API trước mỗi demo để tránh lỗi do endpoint không chạy.

## Kiểm tra thực tế trên branch và so sánh với báo cáo đánh giá

- **Branch kiểm tra:** `LeManhCuong`
- **Lệnh chạy lại:** `pytest -q`
- **Kết quả thực tế: `20 passed in 13.31s`**
- **Điểm so sánh:** Tôi đã rà soát [group_project/evaluation/RESULT.md](group_project/evaluation/RESULT.md) và thấy rằng cấu trúc của báo cáo đánh giá (A/B comparison, worst performers, recommendations, bonus experiments) phù hợp với yêu cầu của lab và với mục tiêu pipeline RAG. Tuy nhiên, trên branch hiện tại không có runner đánh giá Ragas riêng biệt được commit sẵn để tái chạy lại từng metric một cách độc lập; do đó, bảng số liệu ở [group_project/evaluation/RESULT.md](group_project/evaluation/RESULT.md) nên được hiểu là một bản ghi kết quả đánh giá đã được chuẩn bị trong quá trình làm bài, chứ không phải kết quả được re-run bằng một script riêng hoàn toàn trên branch `LeManhCuong`.
- **Kết luận:** Về phần tôi đã thực hiện, việc kiểm tra thực tế khẳng định repo hiện đang pass test suite và có cấu hình kỹ thuật hợp lý. Việc A/B và số liệu metric trong báo cáo được coi là một tài liệu đánh giá đã chuẩn bị sẵn, còn phần được xác thực bằng lệnh chạy thực tế trên branch là tính đúng đắn của code và contract tests, không phải từng giá trị Ragas riêng rẽ.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-21
- Tên thành viên: Nguyễn Trọng Minh
