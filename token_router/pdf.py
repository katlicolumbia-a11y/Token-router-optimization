"""PDF text loading utilities for the token router CLI."""

from __future__ import annotations

from pathlib import Path
import re


def load_pdf_text(path: str) -> str:
    """Extract enough text from a PDF path for routing and token estimation.

    If ``pypdf`` is installed, real text extraction is used. Otherwise the loader
    falls back to counting PDF page markers so the CLI can still create a routing
    prompt such as "Read a 5-page PDF" without adding a mandatory dependency.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file: {path}")

    extracted = _extract_with_pypdf(pdf_path)
    if extracted.strip():
        return extracted

    content = pdf_path.read_bytes()
    page_count = max(1, len(re.findall(rb"/Type\s*/Page\b", content)))
    return f"Read a {page_count}-page PDF from {pdf_path.name}."


def _extract_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
