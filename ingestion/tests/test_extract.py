import json
import shutil
from pathlib import Path

import pytest
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from ingestion.extract import Source, clean_text, extract_all, extract_source, write_jsonl

needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="needs tesseract")


def make_pdf(path: Path, pages: list[str | Image.Image]) -> Path:
    """Build a PDF where str pages hold real text and Image pages simulate scans."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for content in pages:
        pdf.add_page()
        if isinstance(content, str):
            pdf.multi_cell(0, 8, content)
        else:
            pdf.image(content, x=10, y=10, w=190)
    pdf.output(str(path))
    return path


def scanned_image(text: str) -> Image.Image:
    image = Image.new("RGB", (1600, 400), "white")
    font = ImageFont.load_default(size=64)
    ImageDraw.Draw(image).text((40, 150), text, fill="black", font=font)
    return image


def test_clean_text_joins_hyphenation_and_drops_page_numbers() -> None:
    raw = "Press the point  gently with\nyour thumb for acu-\npressure.\n\n12\n\nNext   paragraph."
    assert (
        clean_text(raw)
        == "Press the point gently with your thumb for acupressure.\n\nNext paragraph."
    )


def test_clean_text_drops_headers_figure_labels_and_splits_point_headings() -> None:
    raw = (
        "Test Meridian 56\nTP1: Ceshi\nOn the test hand,\nnear the wrist.\n"
        "TP2: Other\nOn the arm.\nTP1\nTP2\n- 12 -"
    )
    assert clean_text(raw, [r"^Test Meridian\s*\d+$"]) == (
        "TP1: Ceshi On the test hand, near the wrist.\n\nTP2: Other On the arm."
    )


def test_page_range_limits_extracted_pages(tmp_path: Path) -> None:
    make_pdf(tmp_path / "guide.pdf", ["Front matter page.", "Point page.", "Index page."])
    pages = extract_source(Source(file="guide.pdf", title="Guide", pages="2-2"), tmp_path)
    assert [(p.page, p.text) for p in pages] == [(2, "Point page.")]


def test_clean_text_normalises_unicode() -> None:
    assert clean_text("ﬁnger width") == "finger width"


def test_extracts_text_pages_with_page_numbers(tmp_path: Path) -> None:
    pdf = make_pdf(
        tmp_path / "guide.pdf",
        ["First page about the hand point.", "Second page with more curated text."],
    )
    pages = extract_source(Source(file="guide.pdf", title="Guide"), tmp_path)

    assert [(p.page, p.text, p.ocr) for p in pages] == [
        (1, "First page about the hand point.", False),
        (2, "Second page with more curated text.", False),
    ]
    assert pdf.exists()


@needs_tesseract
def test_scanned_page_is_ocred(tmp_path: Path) -> None:
    make_pdf(
        tmp_path / "scan.pdf",
        ["A normal page with selectable text.", scanned_image("Scanned acupressure page")],
    )
    pages = extract_source(Source(file="scan.pdf", title="Scan"), tmp_path)

    assert pages[0].ocr is False
    assert pages[1].ocr is True
    assert "Scanned acupressure page" in pages[1].text


def test_blank_page_is_skipped_without_tesseract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pytesseract

    def missing(*args: object, **kwargs: object) -> str:
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "image_to_string", missing)
    make_pdf(
        tmp_path / "doc.pdf", ["Readable page text here.", Image.new("RGB", (10, 10), "white")]
    )

    pages = extract_source(Source(file="doc.pdf", title="Doc"), tmp_path)

    assert [p.page for p in pages] == [1]


def test_text_file_source(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("Some  curated\nnotes.", encoding="utf-8")
    pages = extract_source(Source(file="notes.md", title="Notes"), tmp_path)
    assert [(p.page, p.text) for p in pages] == [(1, "Some curated notes.")]


def test_unsupported_file_type_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        extract_source(Source(file="slides.pptx", title="Slides"), tmp_path)


def test_manifest_metadata_is_kept_in_output(tmp_path: Path) -> None:
    make_pdf(tmp_path / "de.pdf", ["Ein Text auf Deutsch über Akupressur."])
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "file": "de.pdf",
                        "title": "Leitfaden",
                        "language": "de",
                        "author": "A. Author",
                        "url": "https://example.org/de.pdf",
                        "license": "CC BY 4.0",
                    }
                ]
            }
        )
    )

    output = tmp_path / "out" / "pages.jsonl"
    write_jsonl(extract_all(manifest), output)

    record = json.loads(output.read_text().splitlines()[0])
    assert record["page"] == 1
    assert record["source"] == {
        "file": "de.pdf",
        "title": "Leitfaden",
        "language": "de",
        "author": "A. Author",
        "url": "https://example.org/de.pdf",
        "license": "CC BY 4.0",
        "pages": None,
        "drop_lines": [],
        "use_ocr": True,
    }
