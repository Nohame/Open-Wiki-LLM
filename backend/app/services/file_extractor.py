from io import BytesIO
from pathlib import Path

import pdfplumber
from docx import Document

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}


async def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension non supportée : {ext!r}")
    if ext in {".md", ".txt"}:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"Fichier non décodable en UTF-8 : {e}") from e
    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    return _extract_docx(file_bytes)


def _extract_pdf(data: bytes) -> str:
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n\n".join(p for p in pages if p.strip())
    except Exception as e:
        raise ValueError(f"PDF illisible : {e}") from e


def _extract_docx(data: bytes) -> str:
    try:
        doc = Document(BytesIO(data))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        raise ValueError(f"DOCX illisible : {e}") from e
