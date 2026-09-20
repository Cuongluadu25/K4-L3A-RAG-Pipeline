"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: Dịch vụ đại học tại Đại học Công nghiệp Hà Nội (HaUI) —
học phí, học bổng, đăng ký học tập/tín chỉ, tuyển sinh.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Mỗi tài liệu được khai báo trong SOURCES kèm URL trang công bố để người khác
kiểm tra lại được. Tài liệu nào có link file trực tiếp thì script tự tải;
tài liệu chỉ công bố dạng HTML/nhúng thì tải tay và script chỉ kiểm tra.
Chạy lại script không tải đè file đã có (idempotent).

Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import unicodedata
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
MIN_FILE_SIZE = 1024
ALLOWED_SUFFIXES = {".pdf", ".doc", ".docx"}

# filename -> metadata. `page` là trang công bố (nguồn kiểm chứng),
# `file` là link tải trực tiếp nếu có (None = tải tay từ `page`).
SOURCES: dict[str, dict[str, str | None]] = {
    "Hoc-phi.pdf": {
        "title": (
            "Quyết định 920/QĐ-ĐHCN ngày 08/6/2026 về việc ban hành mức thu "
            "học phí đối với các chương trình đào tạo tại Đại học Công nghiệp "
            "Hà Nội năm học 2026-2027"
        ),
        "page": (
            "https://www.haui.edu.vn/vn/hoc-bong-hoc-phi/quyet-dinh-ve-viec-ban-hanh-"
            "muc-thu-hoc-phi-doi-voi-cac-chuong-trinh-dao-tao-tai-dhcn-ha-noi-"
            "nam-hoc-2026-2027/68147"
        ),
        # PDF được nhúng qua <iframe src="/media/..."> trên trang công bố.
        "file": "https://www.haui.edu.vn/media/QĐ mức thu học phí năm học 2026-2027.pdf",
    },
    "Hoc-bong.pdf": {
        "title": (
            "Thông báo tuyển sinh đại học chính quy năm 2026 của Đại học Công "
            "nghiệp Hà Nội (mục III: chính sách học phí, học bổng)"
        ),
        "page": "https://www.haui.edu.vn/vn/thong-bao/tuyen-sinh-dai-hoc-chinh-quy-nam-2026/67648",
        "file": None,
    },
    "Dang-ky-tin-chi.pdf": {
        "title": (
            "Thông báo kế hoạch đăng ký, học tập tại học kỳ 2 năm học 2025-2026 "
            "đối với sinh viên đại học các khóa"
        ),
        "page": (
            "https://sict.haui.edu.vn/vn/thong-bao/thong-bao-ve-ke-hoach-dang-ky-va-"
            "hoc-tap-hoc-ky-2-nam-hoc-2025-2026-doi-voi-sinh-vien-dai-hoc-cac-khoa/71606"
        ),
        "file": None,
    },
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def _encode_url(url: str) -> str:
    """Percent-encode phần path có dấu tiếng Việt.

    Server haui.edu.vn chỉ trả file khi path được chuẩn hóa Unicode NFD
    (dạng tổ hợp dấu) trước khi encode; dạng NFC bị redirect về trang lỗi.
    """
    parts = urlsplit(url)
    path = quote(unicodedata.normalize("NFD", parts.path))
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def _is_valid_document(path: Path) -> bool:
    """File tồn tại, đủ lớn và đúng định dạng (PDF hoặc gói Office/OLE)."""
    if not path.is_file() or path.stat().st_size < MIN_FILE_SIZE:
        return False
    with path.open("rb") as handle:
        head = handle.read(8)
    if path.suffix.lower() == ".pdf":
        return head.startswith(b"%PDF")
    if path.suffix.lower() == ".docx":
        return head.startswith(b"PK\x03\x04")
    if path.suffix.lower() == ".doc":
        return head.startswith(b"\xd0\xcf\x11\xe0")
    return False


def _download(url: str, destination: Path, referer: str | None) -> None:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"}
    if referer:
        headers["Referer"] = referer
    response = requests.get(_encode_url(url), headers=headers, timeout=60)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        raise RuntimeError(f"server returned HTML instead of a document ({content_type})")
    destination.write_bytes(response.content)


def download_documents() -> None:
    """Tải/kiểm tra các tài liệu trong SOURCES, bỏ qua file đã có sẵn."""
    missing: list[str] = []
    for filename, source in SOURCES.items():
        target = DATA_DIR / filename
        if _is_valid_document(target):
            print(f"Exists: {filename} ({target.stat().st_size:,} bytes)")
            continue

        if source["file"] is None:
            print(f"Manual: {filename} — tải từ trang công bố rồi đặt vào {DATA_DIR}")
            print(f"        {source['page']}")
            missing.append(filename)
            continue

        try:
            _download(source["file"], target, source["page"])
        except Exception as error:  # noqa: BLE001 — báo lỗi từng file, không dừng cả batch
            print(f"Failed: {filename} — {error}")
            missing.append(filename)
            continue

        if not _is_valid_document(target):
            target.unlink(missing_ok=True)
            print(f"Failed: {filename} — nội dung tải về không phải PDF/DOC hợp lệ")
            missing.append(filename)
            continue
        print(f"Saved: {filename} ({target.stat().st_size:,} bytes)")

    present = sorted(
        path.name for path in DATA_DIR.iterdir()
        if path.suffix.lower() in ALLOWED_SUFFIXES and _is_valid_document(path)
    )
    unknown = [name for name in present if name not in SOURCES]
    if unknown:
        print(f"Warning: file chưa khai báo nguồn trong SOURCES: {unknown}")
    print(f"Legal documents ready: {len(present)}/{len(SOURCES)} — {present}")
    if missing:
        raise SystemExit(f"Thiếu tài liệu: {missing}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
