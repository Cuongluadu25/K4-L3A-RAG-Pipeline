"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cách làm:
    - legal/: MarkItDown trích text layer. PDF scan (không có text layer,
      ví dụ Hoc-phi.pdf) được render từng trang và OCR bằng EasyOCR (tiếng
      Việt). Header ghi rõ phương pháp để người đọc biết cần đối chiếu kỹ.
    - news/: ghép header (title, url, date_crawled) + content_markdown.
    - Mỗi file landing -> đúng một file .md cùng stem; chạy lại ghi đè,
      file .md không còn nguồn landing tương ứng sẽ bị xóa; output rỗng
      không được ghi.
    - Header mọi file có "Source file" và "Source URL" để từ một Markdown
      bất kỳ truy ngược được file landing và nguồn công khai.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    OCR fallback cần: pip install easyocr (đã thêm vào extras `ocr`).
"""

import json
import re
from pathlib import Path

from src.task1_collect_legal_docs import SOURCES as LEGAL_SOURCES


ROOT_DIR = Path(__file__).parent.parent
LANDING_DIR = ROOT_DIR / "data" / "landing"
OUTPUT_DIR = ROOT_DIR / "data" / "standardized"

LEGAL_SUFFIXES = {".pdf", ".doc", ".docx"}
# Dưới ngưỡng này coi như PDF không có text layer -> OCR.
MIN_TEXT_CHARS = 200
OCR_DPI = 200
OCR_LANGUAGES = ["vi", "en"]

_ocr_reader = None

# Lỗi OCR lặp lại đã đối chiếu với bản scan: chữ O/I/l bị nhận nhầm trong
# mã khóa (K2O -> K20, KI9 -> K19). Chỉ sửa trong ngữ cảnh "K<số>" để không
# đụng vào chữ thường.
_COHORT_CODE = re.compile(r"(?<![A-Za-z])K([0-9OIl]{1,2})(?![A-Za-z0-9])")
_COHORT_MAP = str.maketrans("OIl", "011")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _relative(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def _normalize_text(text: str) -> str:
    """Bỏ khoảng trắng thừa cuối dòng và gộp >2 dòng trống thành 2."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    text = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", text) + "\n"


def _write_markdown(output: Path, header: str, body: str) -> bool:
    body = body.strip()
    if not body:
        print(f"Skip (empty): {output.name}")
        output.unlink(missing_ok=True)
        return False
    output.write_text(_normalize_text(header + body), encoding="utf-8")
    return True


def _remove_stale(output_dir: Path, expected: set[str]) -> None:
    """Xóa .md không còn file landing tương ứng để giữ ánh xạ 1-1."""
    for path in output_dir.glob("*.md"):
        if path.name not in expected:
            print(f"Removed stale: {_relative(path)}")
            path.unlink()


# --------------------------------------------------------------------------- #
# Legal documents
# --------------------------------------------------------------------------- #
def _extract_with_markitdown(path: Path) -> str:
    from markitdown import MarkItDown

    return MarkItDown().convert(str(path)).text_content or ""


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr

        _ocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)
    return _ocr_reader


def _boxes_to_lines(boxes: list) -> list[str]:
    """Gom các box OCR thành dòng theo tâm trục y, sắp theo x trong dòng.

    EasyOCR trả từng ô rời rạc (đặc biệt với bảng); gom dòng để mỗi hàng
    bảng thành một dòng text như "3.2 Cử nhân K20 ... 770.000 đồng/tín chỉ".
    """
    items = []
    for box, text, _conf in boxes:
        ys = [pt[1] for pt in box]
        xs = [pt[0] for pt in box]
        items.append(((min(ys) + max(ys)) / 2, max(ys) - min(ys), min(xs), text.strip()))
    if not items:
        return []
    heights = sorted(item[1] for item in items)
    tolerance = max(heights[len(heights) // 2] * 0.6, 6)

    items.sort(key=lambda item: item[0])
    lines: list[list[tuple]] = [[items[0]]]
    for item in items[1:]:
        current_y = sum(i[0] for i in lines[-1]) / len(lines[-1])
        if abs(item[0] - current_y) <= tolerance:
            lines[-1].append(item)
        else:
            lines.append([item])
    return [" ".join(i[3] for i in sorted(line, key=lambda i: i[2])) for line in lines]


def _fix_ocr_cohort_codes(text: str) -> str:
    return _COHORT_CODE.sub(lambda m: "K" + m.group(1).translate(_COHORT_MAP), text)


def _extract_with_ocr(path: Path) -> str:
    import numpy as np
    import pdfplumber

    reader = _get_ocr_reader()
    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            image = page.to_image(resolution=OCR_DPI).original.convert("L")
            boxes = reader.readtext(np.array(image), detail=1, paragraph=False)
            lines = [_fix_ocr_cohort_codes(line) for line in _boxes_to_lines(boxes)]
            pages.append(f"<!-- page {number} -->\n" + "\n".join(lines))
            print(f"    OCR page {number}/{len(pdf.pages)}: {len(lines)} lines")
    return "\n\n".join(pages)


def _legal_header(path: Path, method: str) -> str:
    source = LEGAL_SOURCES.get(path.name, {})
    title = source.get("title") or path.stem.replace("-", " ")
    url = source.get("page") or "(chưa khai báo trong task1 SOURCES)"
    note = ""
    if method == "easyocr":
        note = (
            "\n> Văn bản gốc là bản scan; nội dung dưới đây được OCR tự động, "
            "có thể sai chính tả/dấu. Số liệu đã đối chiếu với bản scan.\n"
        )
    return (
        f"# {title}\n\n"
        f"**Source file:** {_relative(path)}\n\n"
        f"**Source URL:** {url}\n\n"
        f"**Doc type:** legal\n\n"
        f"**Converted with:** {method}\n"
        f"{note}\n---\n\n"
    )


def convert_legal_docs() -> None:
    """Convert PDF/DOCX vào standardized/legal (MarkItDown, OCR fallback cho scan)."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    expected: set[str] = set()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in LEGAL_SUFFIXES or path.name.startswith("."):
            continue
        output = output_dir / f"{path.stem}.md"
        expected.add(output.name)

        text, method = _extract_with_markitdown(path), "markitdown"
        if len(text.strip()) < MIN_TEXT_CHARS and path.suffix.lower() == ".pdf":
            print(f"  {path.name}: không có text layer ({len(text.strip())} chars) -> OCR")
            text, method = _extract_with_ocr(path), "easyocr"

        if _write_markdown(output, _legal_header(path, method), text):
            print(f"Saved: {_relative(output)} [{method}, {len(text.strip()):,} chars]")

    _remove_stale(output_dir, expected)


# --------------------------------------------------------------------------- #
# News articles
# --------------------------------------------------------------------------- #
def _news_header(path: Path, data: dict) -> str:
    extraction = data.get("extraction")
    extra = f"**Extraction:** {extraction}\n\n" if extraction else ""
    return (
        f"# {data['title'].strip()}\n\n"
        f"**Source file:** {_relative(path)}\n\n"
        f"**Source URL:** {data['url']}\n\n"
        f"**Crawled:** {data['date_crawled']}\n\n"
        f"**Doc type:** news\n\n"
        f"{extra}---\n\n"
    )


def convert_news_articles() -> None:
    """Convert JSON vào standardized/news, giữ metadata ở đầu file."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    required = {"url", "title", "date_crawled", "content_markdown"}
    expected: set[str] = set()
    for path in sorted(news_dir.glob("*.json")):
        output = output_dir / f"{path.stem}.md"
        expected.add(output.name)

        data = json.loads(path.read_text(encoding="utf-8"))
        missing = required - data.keys()
        if missing:
            print(f"Skip (missing {sorted(missing)}): {path.name}")
            expected.discard(output.name)
            continue

        body = data["content_markdown"]
        if _write_markdown(output, _news_header(path, data), body):
            print(f"Saved: {_relative(output)} [{len(body.strip()):,} chars]")

    _remove_stale(output_dir, expected)


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
