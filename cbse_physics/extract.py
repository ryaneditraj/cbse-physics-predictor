"""Pull text out of local question-paper PDFs.

The reader caps file size, page count, and extracted length. Directory scans
do not follow symlinks that resolve outside the directory the user named.
OCR is optional, off unless CBSE_PHYSICS_OCR=1, and never shells out through a
shell string.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 40
MAX_TEXT_CHARS = 1_500_000
MAX_PDFS = 200
_TESSERACT_CMD = re.compile(r"[A-Za-z0-9._/\\:-]{1,200}")


class ExtractError(ValueError):
    """A PDF could not be read under the safety limits."""


def collect_pdfs(path: Path) -> list[Path]:
    path = path.expanduser()
    if not path.exists():
        raise ExtractError(f"path not found: {path}")
    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ExtractError("expected a .pdf file or a directory of PDFs")
        resolved = path.resolve()
        if not resolved.is_file():
            raise ExtractError(f"not a regular file: {path}")
        return [resolved]

    root = path.resolve()
    if not root.is_dir():
        raise ExtractError(f"not a directory: {path}")
    found: list[Path] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or candidate.suffix.lower() != ".pdf":
            continue
        relative = candidate.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        resolved = candidate.resolve()
        if not resolved.is_file() or not _is_inside(root, resolved):
            continue
        found.append(resolved)
        if len(found) > MAX_PDFS:
            raise ExtractError(f"refusing to read more than {MAX_PDFS} PDFs in one run")
    return found


def _is_inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def extract_pdf_text(path: Path) -> str:
    if path.stat().st_size > MAX_PDF_BYTES:
        raise ExtractError(f"{path.name} exceeds {MAX_PDF_BYTES} bytes")
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            raise ExtractError(f"{path.name} is encrypted")
        page_count = len(reader.pages)
        if page_count > MAX_PAGES:
            raise ExtractError(f"{path.name} has {page_count} pages; the limit is {MAX_PAGES}")
        chunks: list[str] = []
        total = 0
        for page in reader.pages:
            piece = page.extract_text() or ""
            total += len(piece)
            if total > MAX_TEXT_CHARS:
                raise ExtractError(f"{path.name} exceeds the extracted-text limit")
            chunks.append(piece)
    except PdfReadError as exc:
        raise ExtractError(f"{path.name} is not a readable PDF") from exc
    text = "\n".join(chunks).strip()
    if len(text) >= 40 or os.environ.get("CBSE_PHYSICS_OCR", "0") != "1":
        return text
    return _ocr_pdf(path, page_count)


def _ocr_pdf(path: Path, page_count: int) -> str:
    command = os.environ.get("CBSE_PHYSICS_TESSERACT_CMD", "").strip()
    if command and (_TESSERACT_CMD.fullmatch(command) is None or any(char.isspace() for char in command)):
        raise ExtractError("CBSE_PHYSICS_TESSERACT_CMD is not a plain path")
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise ExtractError(
            "OCR was requested but the optional ocr extra is not installed "
            "(pip install -e '.[ocr]')"
        ) from exc

    if command:
        pytesseract.pytesseract.tesseract_cmd = command

    last_page = min(page_count, 8)
    try:
        images = convert_from_path(str(path), dpi=200, first_page=1, last_page=last_page)
    except Exception as exc:  # poppler and PIL raise a wide, library-specific set
        raise ExtractError(f"could not render {path.name} for OCR") from exc
    parts: list[str] = []
    total = 0
    for image in images:
        try:
            piece = pytesseract.image_to_string(image, timeout=20) or ""
        except RuntimeError as exc:
            raise ExtractError(f"OCR timed out or failed on {path.name}") from exc
        total += len(piece)
        if total > MAX_TEXT_CHARS:
            raise ExtractError(f"{path.name} exceeds the extracted-text limit")
        parts.append(piece)
    return "\n".join(parts).strip()
