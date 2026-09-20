"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://tuyensinh.haui.edu.vn/tin-tuc/thong-bao-tuyen-sinh-dai-hoc-chinh-quy-nam-2026/69e6fed295dfe0072a789d00",

    "https://tuyensinh.haui.edu.vn/dai-hoc-chinh-quy/thong-tin-tuyen-sinh-trinh-do-dai-hoc-nam-2026/69b4e60495dfe0072a789cf6",

    "https://major.haui.edu.vn/vn/tin-tuc/thong-tin-tuyen-sinh-trinh-do-dai-hoc-nam-2026/67609",

    "https://sict.haui.edu.vn/vn/tuyen-sinh-dai-hoc/tuyen-sinh-dai-hoc-chinh-quy-ctdt-khoa-hoc-may-tinh-nam-2026/71770",

    "https://www.haui.edu.vn/vn/hoc-bong-hoc-phi/ho-tro-tai-chinh-va-hoc-bong-danh-cho-sinh-vien-haui/68191",

    "https://sict.haui.edu.vn/vn/thong-bao/ke-hoach-dang-ky-va-hoc-tap-hoc-ky-phu-2-nam-hoc-2025-2026/71774",

    "https://sict.haui.edu.vn/vn/thong-bao/thong-bao-ve-viec-mo-khong-mo-cac-lop-hoc-phan-hoc-ky-phu-2-nam-hoc-2025-2026/71822",

    "https://sict.haui.edu.vn/vn/tuyen-sinh-dai-hoc/dai-hoc-cong-nghiep-ha-noi-du-kien-mot-so-diem-moi-trong-tuyen-sinh-dai-hoc-chinh-quy-nam-2025/71255",

    "https://tuyensinh.haui.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-nam-2025/680f9d53f721616a54f6495f",

    "https://dsa.haui.edu.vn/vn/hoc-bong-quy-khuyen-hoc/hoc-bong-dai-hoc-cong-nghiep-ha-noi/62589",
]

async def crawl_article(url: str) -> dict:
    from datetime import datetime
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

        return {
            "url": url,
            "title": result.metadata.get("title", "Unknown"),
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": result.markdown,
        }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
