"""Catalogue point-location images: upload permitted files and link them to points.

Images are listed by hand in a JSON manifest, so every image carries its
attribution, licence and an explicit decision on whether it may be used:

    {
      "images": [
        {"point_id": "LI4", "file": "images/li4.png", "permitted": true,
         "attribution": "Figure 3, A. Author", "license": "CC BY 4.0",
         "source_title": "Guide title", "page": 12}
      ]
    }

Permitted images are uploaded to the `point-images` Storage bucket and linked
to the point. Entries with "permitted": false clear any existing image, so the
point falls back to its text location description.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... DATABASE_URL=... \
        uv run python -m ingestion.images sources/images.json
"""

import argparse
import json
import logging
import os
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psycopg

log = logging.getLogger(__name__)

BUCKET = "point-images"
ALLOWED_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

Uploader = Callable[[str, bytes, str], None]  # (object path, content, content type)


@dataclass
class ImageEntry:
    point_id: str
    file: str
    permitted: bool
    attribution: str | None = None
    license: str | None = None
    source_title: str | None = None
    page: int | None = None

    def full_attribution(self) -> str:
        attribution = self.attribution or ""
        page = f"p. {self.page}" if self.page else None
        reference = ", ".join(p for p in [self.source_title, page] if p)
        return f"{attribution} ({reference})" if reference else attribution


def load_manifest(path: Path) -> list[ImageEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ImageEntry(**entry) for entry in data["images"]]


def validate(entry: ImageEntry, base_dir: Path, point_ids: set[str]) -> None:
    if entry.point_id not in point_ids:
        raise ValueError(f"Unknown point {entry.point_id!r}")
    if not entry.permitted:
        return
    if not (entry.attribution and entry.license):
        raise ValueError(f"{entry.file}: permitted images need attribution and license")
    if Path(entry.file).suffix.lower() not in ALLOWED_TYPES:
        raise ValueError(f"{entry.file}: unsupported image type")
    if not (base_dir / entry.file).is_file():
        raise ValueError(f"{entry.file}: file not found")


def storage_uploader(supabase_url: str, service_key: str) -> Uploader:
    def upload(object_path: str, content: bytes, content_type: str) -> None:
        request = urllib.request.Request(
            f"{supabase_url.rstrip('/')}/storage/v1/object/{BUCKET}/{object_path}",
            data=content,
            method="POST",
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        with urllib.request.urlopen(request, timeout=30):
            pass

    return upload


def catalogue(
    conn: psycopg.Connection, entries: list[ImageEntry], base_dir: Path, upload: Uploader
) -> tuple[int, int]:
    """Validate every entry first, then upload and link. Returns (linked, cleared)."""
    point_ids = {row[0] for row in conn.execute("select id from points").fetchall()}
    for entry in entries:
        validate(entry, base_dir, point_ids)

    linked = cleared = 0
    for entry in entries:
        if not entry.permitted:
            conn.execute(
                "update points set image_path = null, image_attribution = null, "
                "image_license = null where id = %s",
                (entry.point_id,),
            )
            cleared += 1
            continue
        suffix = Path(entry.file).suffix.lower()
        object_path = f"points/{entry.point_id}{suffix}"
        upload(object_path, (base_dir / entry.file).read_bytes(), ALLOWED_TYPES[suffix])
        conn.execute(
            "update points set image_path = %s, image_attribution = %s, image_license = %s "
            "where id = %s",
            (object_path, entry.full_attribution(), entry.license, entry.point_id),
        )
        linked += 1
    return linked, cleared


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload permitted point images and link them.")
    parser.add_argument("manifest", type=Path, help="JSON manifest listing point images")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    upload = storage_uploader(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)) as conn:
        linked, cleared = catalogue(
            conn, load_manifest(args.manifest), args.manifest.parent, upload
        )
    log.info("Linked %d images, cleared %d", linked, cleared)


if __name__ == "__main__":
    main()
