import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from app.core.config import Settings


class PdfError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPdf:
    page_count: int
    empty_page_count: int
    chunks: list[tuple[int, str]]


def safe_filename(filename: str | None) -> str:
    name = (filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if not unicodedata.category(char).startswith("C"))
    name = name.strip().strip(".")
    if len(name) > 255:
        name = name[:251] + ".pdf" if name.lower().endswith(".pdf") else name[:255]
    return name or "document.pdf"


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(
        char if char.isspace() or not unicodedata.category(char).startswith("C") else ""
        for char in normalized
    )
    return re.sub(r"\s+", " ", normalized).strip()


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    """Bounded character windows; callers supply one normalized page at a time."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Chunk size must be positive and overlap smaller than size")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def extract_pdf(data: bytes, settings: Settings) -> ExtractedPdf:
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise PdfError("Encrypted PDFs are not supported. Upload an unencrypted copy.")
        pages = len(reader.pages)
        if pages > settings.max_pdf_pages:
            raise PdfError(f"PDF exceeds the {settings.max_pdf_pages}-page limit.")
        chunks: list[tuple[int, str]] = []
        empty = 0
        total_chars = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = normalize_text(page.extract_text() or "")
            total_chars += len(text)
            if total_chars > settings.max_extracted_chars:
                raise PdfError("PDF exceeds the extracted text limit.")
            if not text:
                empty += 1
            chunks.extend((page_number, part) for part in chunk_text(text))
        return ExtractedPdf(pages, empty, chunks)
    except PdfError:
        raise
    except Exception as exc:
        # Do not expose parser exceptions, document text, or filesystem details.
        raise PdfError("PDF could not be read. It may be damaged or unsupported.") from exc
