"""Steps 2-4 of ingestion: translate, chunk, embed and store extracted pages.

Reads the JSONL written by `ingestion.extract`, then for each source:
translates non-English pages into English, splits them into chunks (a new chunk
starts at each "CODE: Name" point heading), embeds each chunk and stores it in
`knowledge_chunks` with its source, page reference and the point it is about.
Re-running replaces the chunks of each source, so the step is repeatable.

Usage:
    DATABASE_URL=... uv run python -m ingestion.load out/pages.jsonl
    AI_PROVIDER=fake ...   # offline run with fake embeddings and translation
"""

import argparse
import json
import logging
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import psycopg

from ingestion.ai import AI, get_ai
from ingestion.chunk import chunk_text
from ingestion.codes import normalize_codes

log = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
# A paragraph that starts with a point code and a colon, as in the WHO atlas ("ST21: Liangmen").
POINT_HEADING = re.compile(r"(?:[A-Z]{2}\d{1,2}|EX-[A-Z]+\d+)(?=: )")


def read_pages(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Group extracted pages by source title, keeping page order."""
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            by_source[record["source"]["title"]].append(record)
    return by_source


def upsert_source(conn: psycopg.Connection, source: dict[str, Any]) -> int:
    """Create or update the source row (identified by title) and clear its old chunks."""
    row = conn.execute("select id from sources where title = %s", (source["title"],)).fetchone()
    values = (source.get("author"), source.get("url"), source["language"], source.get("license"))
    if row:
        source_id = int(row[0])
        conn.execute(
            "update sources set author = %s, url = %s, language = %s, license = %s where id = %s",
            (*values, source_id),
        )
        conn.execute("delete from knowledge_chunks where source_id = %s", (source_id,))
        return source_id
    row = conn.execute(
        "insert into sources (title, author, url, language, license) "
        "values (%s, %s, %s, %s, %s) returning id",
        (source["title"], *values),
    ).fetchone()
    assert row is not None
    return int(row[0])


def mentioned_point(text: str, point_ids: set[str]) -> str | None:
    """The curated point a chunk is about, when it mentions exactly one point code.

    Codes are normalised first, so "LI 4", "Li-04" and "LI4" all count as LI4.
    """
    text = normalize_codes(text)
    found = {pid for pid in point_ids if re.search(rf"(?<![\w-]){re.escape(pid)}(?![\w-])", text)}
    return found.pop() if len(found) == 1 else None


def heading_point(section: str, point_ids: set[str]) -> str | None:
    """The curated point a section is headed by, e.g. "ST21: Liangmen ..." -> "ST21"."""
    match = POINT_HEADING.match(normalize_codes(section))
    return match.group(0) if match and match.group(0) in point_ids else None


def split_sections(text: str) -> list[str]:
    """Split page text before each point heading, so each point is chunked on its own."""
    sections = re.split(r"\n\n(?=" + POINT_HEADING.pattern + ")", text)
    return [s for s in sections if s.strip()]


def insert_chunk(
    conn: psycopg.Connection,
    ai: AI,
    source_id: int,
    point_id: str | None,
    page: int | None,
    content: str,
) -> None:
    conn.execute(
        "insert into knowledge_chunks "
        "(source_id, point_id, page, language, content, embedding) "
        "values (%s, %s, %s, 'en', %s, %s::extensions.vector)",
        (source_id, point_id, page, content, str(ai.embed(content))),
    )


def load_source(
    conn: psycopg.Connection, ai: AI, pages: list[dict[str, Any]], point_ids: set[str]
) -> int:
    source = pages[0]["source"]
    source_id = upsert_source(conn, source)
    count = 0
    for page in pages:
        text = page["text"]
        if source["language"] != "en":
            text = ai.translate(text, source["language"])
        for section in split_sections(text):
            heading = heading_point(section, point_ids)
            for chunk in chunk_text(section):
                point_id = heading or mentioned_point(chunk, point_ids)
                insert_chunk(conn, ai, source_id, point_id, page["page"], chunk)
                count += 1
    return count


def load_all(conn: psycopg.Connection, ai: AI, pages_path: Path) -> int:
    point_ids = {row[0] for row in conn.execute("select id from points").fetchall()}
    total = 0
    for title, pages in read_pages(pages_path).items():
        count = load_source(conn, ai, pages, point_ids)
        log.info("Stored %d chunks for %r", count, title)
        total += count
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate, chunk, embed and store pages.")
    parser.add_argument("pages", type=Path, help="JSONL file written by ingestion.extract")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)) as conn:
        total = load_all(conn, get_ai(), args.pages)  # committed on exit, rolled back on error
    log.info("Stored %d chunks in total", total)


if __name__ == "__main__":
    main()
