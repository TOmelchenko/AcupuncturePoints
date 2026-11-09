"""Step 1 of ingestion: read curated source documents and extract clean page text.

Sources are local files listed in a JSON manifest, so that each document carries
its title, language, licence and URL into later steps:

    {
      "sources": [
        {"file": "pdfs/guide.pdf", "title": "...", "language": "en",
         "author": "...", "url": "...", "license": "...",
         "pages": "33-232", "drop_lines": ["^Stomach Meridian\\d+$"], "use_ocr": false}
      ]
    }

Optional fields: `pages` limits extraction to a page range, `drop_lines` lists
regular expressions for running headers and footers to remove, and `use_ocr`
(default true) can turn off OCR for pages that hold only diagrams.

Usage:
    uv run python -m ingestion.extract sources/manifest.json -o out/pages.jsonl
"""

import argparse
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
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
    pages: str | None = None  # e.g. "33-232", 1-based and inclusive
    drop_lines: list[str] = field(default_factory=list)
    use_ocr: bool = True

    def page_range(self) -> range | None:
        if not self.pages:
            return None
        first, _, last = self.pages.partition("-")
        return range(int(first), int(last or first) + 1)


@dataclass
class Page:
    source: Source
    page: int
    text: str
    ocr: bool = False


# Page numbers such as "12" or "- 12 -".
PAGE_NUMBER = re.compile(r"-?\s*\d+\s*-?")
# Figure labels: a line holding only point codes, e.g. "ST21 ST22".
FIGURE_LABEL = re.compile(r"(?:[A-Z]{2}\d{1,2}\s*)+")
# A point entry such as "ST21: Liangmen" starts a new paragraph.
POINT_HEADING = re.compile(r"[A-Z][A-Za-z]\d{1,2}: ")


def clean_text(text: str, drop_lines: list[str] | None = None) -> str:
    """Normalise extracted text while keeping paragraph breaks.

    Drops page numbers, figure labels and lines matching `drop_lines` patterns,
    and starts a new paragraph at each point heading.
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    dropped = [re.compile(pattern) for pattern in drop_lines or []]
    paragraphs = []

    def close(lines: list[str]) -> None:
        paragraph = re.sub(r"\s+", " ", " ".join(lines)).strip()
        if paragraph:
            paragraphs.append(paragraph)

    for block in re.split(r"\n\s*\n", text):
        current: list[str] = []
        for line in (line.strip() for line in block.splitlines()):
            if not line or PAGE_NUMBER.fullmatch(line) or FIGURE_LABEL.fullmatch(line):
                continue
            if any(pattern.search(line) for pattern in dropped):
                continue
            if POINT_HEADING.match(line):
                close(current)
                current = []
            current.append(line)
        close(current)
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
    wanted = source.page_range()
    for index, pdf_page in enumerate(PdfReader(path).pages):
        if wanted is not None and index + 1 not in wanted:
            continue
        text, used_ocr = clean_text(pdf_page.extract_text() or "", source.drop_lines), False
        if len(text.replace(" ", "")) < MIN_TEXT_CHARS and source.use_ocr:
            try:
                ocr_text = ocr_pdf_page(path, index, source.language)
                text, used_ocr = clean_text(ocr_text, source.drop_lines), True
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
        text = clean_text(path.read_text(encoding="utf-8"), source.drop_lines)
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
