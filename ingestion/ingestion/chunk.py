"""Split page text into overlapping chunks on paragraph and sentence boundaries."""

import re

MAX_CHARS = 1000
OVERLAP_CHARS = 150


def _sentences(paragraph: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", paragraph) if s]


def _pieces(text: str, max_chars: int) -> list[str]:
    """Paragraphs, or sentences of long paragraphs, or hard slices of very long sentences."""
    pieces = []
    for paragraph in text.split("\n\n"):
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
            continue
        for sentence in _sentences(paragraph):
            pieces.extend(sentence[i : i + max_chars] for i in range(0, len(sentence), max_chars))
    return [p for p in pieces if p.strip()]


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    chunks: list[str] = []
    current = ""
    for piece in _pieces(text, max_chars):
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current)
        tail = current[-overlap:]
        # Start the overlap at a word boundary so chunks do not begin mid-word.
        tail = tail[tail.find(" ") + 1 :] if " " in tail else tail
        current = f"{tail} {piece}" if len(tail) + len(piece) + 1 <= max_chars else piece
    if current:
        chunks.append(current)
    return chunks
