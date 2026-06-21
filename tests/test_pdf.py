from pathlib import Path

from token_router import load_pdf_text


def test_pdf_loader_falls_back_to_page_count(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4\n/Type /Page\n/Type /Page\n")

    assert load_pdf_text(str(pdf)) == "Read a 2-page PDF from sample.pdf."
