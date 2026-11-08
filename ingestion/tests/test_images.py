import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import psycopg
import pytest

from ingestion.images import ImageEntry, catalogue, load_manifest, storage_uploader


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def __call__(self, path: str, content: bytes, content_type: str) -> None:
        self.objects[path] = (content, content_type)


@pytest.fixture
def point(db: psycopg.Connection) -> psycopg.Connection:
    db.execute(
        "insert into points (id, name, location_text, instructions) "
        "values ('IMG1', 'Test', 'Text location fallback.', '{Press.}')"
    )
    return db


def image_columns(db: psycopg.Connection) -> Any:
    return db.execute(
        "select image_path, image_attribution, image_license, location_text "
        "from points where id = 'IMG1'"
    ).fetchone()


def test_permitted_image_is_uploaded_and_linked(point: psycopg.Connection, tmp_path: Path) -> None:
    (tmp_path / "img1.PNG").write_bytes(b"png-bytes")
    storage = FakeStorage()
    entry = ImageEntry(
        point_id="IMG1",
        file="img1.PNG",
        permitted=True,
        attribution="Figure 2, A. Author",
        license="CC BY 4.0",
        source_title="Test Guide",
        page=12,
    )

    assert catalogue(point, [entry], tmp_path, storage) == (1, 0)

    assert storage.objects == {"points/IMG1.png": (b"png-bytes", "image/png")}
    assert image_columns(point) == (
        "points/IMG1.png",
        "Figure 2, A. Author (Test Guide, p. 12)",
        "CC BY 4.0",
        "Text location fallback.",
    )


def test_not_permitted_image_clears_link_and_keeps_text(
    point: psycopg.Connection, tmp_path: Path
) -> None:
    point.execute(
        "update points set image_path = 'points/old.png', image_attribution = 'x', "
        "image_license = 'y' where id = 'IMG1'"
    )
    storage = FakeStorage()

    result = catalogue(
        point, [ImageEntry("IMG1", "missing.png", permitted=False)], tmp_path, storage
    )

    assert result == (0, 1)
    assert storage.objects == {}
    assert image_columns(point) == (None, None, None, "Text location fallback.")


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (ImageEntry("NOPE", "a.png", True, "A", "CC0"), "Unknown point"),
        (ImageEntry("IMG1", "a.png", True, None, "CC0"), "attribution and license"),
        (ImageEntry("IMG1", "a.gif", True, "A", "CC0"), "unsupported"),
        (ImageEntry("IMG1", "absent.png", True, "A", "CC0"), "not found"),
    ],
)
def test_invalid_entries_are_rejected_before_any_upload(
    point: psycopg.Connection, tmp_path: Path, entry: ImageEntry, message: str
) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "a.gif").write_bytes(b"x")
    good = ImageEntry("IMG1", "a.png", True, "A", "CC0")
    storage = FakeStorage()

    with pytest.raises(ValueError, match=message):
        catalogue(point, [good, entry], tmp_path, storage)
    assert storage.objects == {}


def test_load_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "images.json"
    manifest.write_text(
        json.dumps(
            {
                "images": [
                    {
                        "point_id": "LI4",
                        "file": "li4.png",
                        "permitted": True,
                        "attribution": "A",
                        "license": "CC0",
                        "page": 3,
                    },
                ]
            }
        )
    )
    assert load_manifest(manifest) == [ImageEntry("LI4", "li4.png", True, "A", "CC0", None, 3)]


def test_storage_uploader_sends_authorised_upsert() -> None:
    received: dict[str, Any] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            received["path"] = self.path
            received["headers"] = {k.lower(): v for k, v in self.headers.items()}
            received["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    upload = storage_uploader(f"http://127.0.0.1:{server.server_port}/", "service-key")

    upload("points/LI4.svg", b"<svg/>", "image/svg+xml")
    server.server_close()

    assert received["path"] == "/storage/v1/object/point-images/points/LI4.svg"
    assert received["headers"]["authorization"] == "Bearer service-key"
    assert received["headers"]["x-upsert"] == "true"
    assert received["headers"]["content-type"] == "image/svg+xml"
    assert received["body"] == b"<svg/>"
