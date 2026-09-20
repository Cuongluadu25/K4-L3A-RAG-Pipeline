"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề nhóm: Dịch vụ đại học tại HaUI — học phí, học bổng, đăng ký học tập,
tuyển sinh. Nguồn: các site chính thức *.haui.edu.vn.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cách làm:
    - Dùng PruningContentFilter để lấy phần thân bài (fit_markdown) thay vì
      nguyên trang (menu, footer, sidebar...). Nếu bộ lọc cắt quá tay thì
      fallback về raw_markdown để không mất nội dung.
    - Tên file cố định theo vị trí URL trong ARTICLE_URLS (article_01.json...),
      chạy lại sẽ ghi đè đúng file cũ, không sinh bản sao.
    - Lưu thêm raw_length/fit_length để đối chiếu khi debug chunk.

Cài browser trước khi chạy:
    python -m playwright install chromium
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    # Tuyển sinh / chính sách chung
    "https://tuyensinh.haui.edu.vn/tin-tuc/thong-bao-tuyen-sinh-dai-hoc-chinh-quy-nam-2026/69e6fed295dfe0072a789d00",
    "https://tuyensinh.haui.edu.vn/dai-hoc-chinh-quy/thong-tin-tuyen-sinh-trinh-do-dai-hoc-nam-2026/69b4e60495dfe0072a789cf6",
    "https://major.haui.edu.vn/vn/tin-tuc/thong-tin-tuyen-sinh-trinh-do-dai-hoc-nam-2026/67609",
    "https://sict.haui.edu.vn/vn/tuyen-sinh-dai-hoc/tuyen-sinh-dai-hoc-chinh-quy-ctdt-khoa-hoc-may-tinh-nam-2026/71770",
    # Học phí / học bổng
    "https://www.haui.edu.vn/vn/hoc-bong-hoc-phi/ho-tro-tai-chinh-va-hoc-bong-danh-cho-sinh-vien-haui/68191",
    # Đăng ký học tập
    "https://sict.haui.edu.vn/vn/thong-bao/ke-hoach-dang-ky-va-hoc-tap-hoc-ky-phu-2-nam-hoc-2025-2026/71774",
    "https://sict.haui.edu.vn/vn/thong-bao/thong-bao-ve-viec-mo-khong-mo-cac-lop-hoc-phan-hoc-ky-phu-2-nam-hoc-2025-2026/71822",
    # Tuyển sinh năm trước (đối chiếu thay đổi)
    "https://sict.haui.edu.vn/vn/tuyen-sinh-dai-hoc/dai-hoc-cong-nghiep-ha-noi-du-kien-mot-so-diem-moi-trong-tuyen-sinh-dai-hoc-chinh-quy-nam-2025/71255",
    "https://tuyensinh.haui.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-nam-2025/680f9d53f721616a54f6495f",
    # Học bổng (Phòng Công tác sinh viên)
    "https://dsa.haui.edu.vn/vn/hoc-bong-quy-khuyen-hoc/hoc-bong-dai-hoc-cong-nghiep-ha-noi/62589",
]

# Khung chứa thân bài theo từng template site của HaUI. Domain không có
# trong bảng dùng DEFAULT_SELECTOR; nếu selector không khớp thì crawl cả trang.
CSS_SELECTORS = {
    "tuyensinh.haui.edu.vn": ".news-details-content",
    "major.haui.edu.vn": ".td_blog_details",
}
DEFAULT_SELECTOR = ".irs-blog-single-col"

# Nếu fit_markdown ngắn hơn tỉ lệ này so với raw thì coi là bộ lọc cắt quá
# tay (mất bảng/danh sách) và dùng raw_markdown.
MIN_FIT_RATIO = 0.15
MIN_CONTENT_CHARS = 500
MAX_RETRIES = 2

BROWSER_CONFIG = BrowserConfig(headless=True, verbose=False)
RUN_CONFIG = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    excluded_tags=["nav", "header", "footer", "aside", "script", "style", "form"],
    remove_overlay_elements=True,
    page_timeout=60_000,
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.45, threshold_type="dynamic", min_word_threshold=5
        ),
        options={"ignore_links": True, "ignore_images": True},
    ),
)


def _pick_content(raw: str, fit: str) -> tuple[str, str]:
    """Chọn fit_markdown nếu đủ dày, ngược lại dùng raw. Trả (content, method)."""
    raw, fit = raw.strip(), fit.strip()
    if fit and len(fit) >= MIN_CONTENT_CHARS and len(fit) >= MIN_FIT_RATIO * len(raw):
        return fit, "fit_markdown"
    return raw, "raw_markdown"


async def crawl_article(url: str, crawler: AsyncWebCrawler | None = None) -> dict:
    """Crawl một URL, trả dict đủ url/title/date_crawled/content_markdown."""
    if crawler is None:
        async with AsyncWebCrawler(config=BROWSER_CONFIG) as own_crawler:
            return await crawl_article(url, own_crawler)

    selector = CSS_SELECTORS.get(urlsplit(url).netloc, DEFAULT_SELECTOR)
    result = await crawler.arun(url=url, config=RUN_CONFIG.clone(target_elements=[selector]))
    scope = f"target:{selector}"
    if not result.success or len((result.markdown.raw_markdown or "").strip()) < MIN_CONTENT_CHARS:
        # Selector không khớp template -> lấy cả trang rồi để bộ lọc xử lý.
        result = await crawler.arun(url=url, config=RUN_CONFIG)
        scope = "page"
    if not result.success:
        raise RuntimeError(result.error_message or f"HTTP {result.status_code}")

    raw = result.markdown.raw_markdown or ""
    fit = result.markdown.fit_markdown or ""
    content, method = _pick_content(raw, fit)
    method = f"{scope}/{method}"
    if len(content) < MIN_CONTENT_CHARS:
        raise RuntimeError(f"content too short ({len(content)} chars)")

    title = (result.metadata or {}).get("title") or ""
    title = title.split(" || ")[0].split(" - ĐẠI HỌC")[0].strip() or "Unknown"

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "content_markdown": content,
        "extraction": method,
        "raw_length": len(raw),
        "fit_length": len(fit),
        "status_code": result.status_code,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    saved, failed = 0, []

    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        for index, url in enumerate(ARTICLE_URLS, 1):
            output = DATA_DIR / f"article_{index:02d}.json"
            last_error: Exception | None = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    article = await crawl_article(url, crawler)
                    output.write_text(
                        json.dumps(article, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    print(
                        f"Saved: {output.name} [{article['extraction']}, "
                        f"{len(article['content_markdown']):,} chars] {article['title']}"
                    )
                    saved += 1
                    last_error = None
                    break
                except Exception as error:  # noqa: BLE001 — thử lại rồi báo, không dừng batch
                    last_error = error
                    print(f"Retry {attempt}/{MAX_RETRIES}: {url} — {error}")
                    await asyncio.sleep(2 * attempt)
            if last_error is not None:
                failed.append(url)
                print(f"Failed: {url} — {last_error}")

    print(f"\nDone: {saved}/{len(ARTICLE_URLS)} articles saved to {DATA_DIR}")
    if failed:
        print("Failed URLs:")
        for url in failed:
            print(f"  - {url}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
