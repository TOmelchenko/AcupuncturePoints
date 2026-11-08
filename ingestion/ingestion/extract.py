"""Step 1 of ingestion: read curated source documents and extract clean page text.

Sources are local files listed in a JSON manifest, so that each document carries
its title, language, licence and URL into later steps:

    {
      "sources": [
        {"file": "pdfs/guide.pdf", "title": "...", "language": "en",
         "author": "...", "url": "...", "license": "..."}
      ]
    }

Usage:
    uv run python -m ingestion.extract sources/manifest.json -o out/pages.jsonl
"""

import argparse
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import pypdfium2
import pytesseract
from pypdf import PdfReader

log = logging.getLogger(__name__)

# Pages with less extractable text than this are treated as scanned and OCR'd.
MIN_TEXT_CHARS = 20
OCR_DPI = 300
# ISO 639-1 codes to Tesseract language packs.
TESSERACT_LANGS = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "uk": "ukr",
    "ru": "rus",
    "zh": "chi_sim",
    "ja": "jpn",
    "ko": "kor",
}


@dataclass
class Source:
    file: str
    title: str
    language: str = "en"
    author: str | None = None
    url: str | None = None
    license: str | None = None


@dataclass
class Page:
    source: Source
    page: int
    text: str
    ocr: bool = False


def clean_text(text: str) -> str:
    """Normalise extracted text while keeping paragraph breaks."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines()]
        lines = [line for line in lines if line and not line.isdigit()]  # drop page numbers
        paragraph = re.sub(r"\s+", " ", " ".join(lines)).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return "\n\n".join(paragraphs)


def ocr_pdf_page(path: Path, page_index: int, language: str) -> str:
    pdf = pypdfium2.PdfDocument(path)
    try:
        image = pdf[page_index].render(scale=OCR_DPI / 72).to_pil()
    finally:
        pdf.close()
    lang = TESSERACT_LANGS.get(language, "eng")
    return str(pytesseract.image_to_string(image, lang=lang))


def extract_pdf(path: Path, source: Source) -> list[Page]:
    pages = []
    for index, pdf_page in enumerate(PdfReader(path).pages):
        text, used_ocr = clean_text(pdf_page.extract_text() or ""), False
        if len(text.replace(" ", "")) < MIN_TEXT_CHARS:
            try:
                text, used_ocr = clean_text(ocr_pdf_page(path, index, source.language)), True
            except pytesseract.TesseractNotFoundError:
                log.warning("Tesseract not installed; cannot OCR %s page %d", path.name, index + 1)
        if text:
            pages.append(Page(source, index + 1, text, used_ocr))
        else:
            log.warning("No text found in %s page %d", path.name, index + 1)
    return pages


def extract_source(source: Source, base_dir: Path) -> list[Page]:
    path = base_dir / source.file
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path, source)
    if suffix in {".txt", ".md"}:
        text = clean_text(path.read_text(encoding="utf-8"))
        return [Page(source, 1, text)] if text else []
    raise ValueError(f"Unsupported source file type: {path.name}")


def load_manifest(manifest_path: Path) -> list[Source]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [Source(**entry) for entry in data["sources"]]


def extract_all(manifest_path: Path) -> list[Page]:
    pages = []
    for source in load_manifest(manifest_path):
        pages.extend(extract_source(source, manifest_path.parent))
    return pages


def write_jsonl(pages: list[Page], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(json.dumps(asdict(page), ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract clean page text from curated sources.")
    parser.add_argument("manifest", type=Path, help="JSON manifest listing source documents")
    parser.add_argument("-o", "--output", type=Path, default=Path("out/pages.jsonl"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    pages = extract_all(args.manifest)
    write_jsonl(pages, args.output)
    log.info("Wrote %d pages to %s", len(pages), args.output)


if __name__ == "__main__":
    main()
