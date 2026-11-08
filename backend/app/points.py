"""Curated point records as stored in the `points` table."""

from dataclasses import dataclass

import psycopg

POINT_COLUMNS = (
    "id, name, location_text, image_path, image_attribution, image_license, "
    "instructions, duration, pressure"
)


@dataclass(frozen=True)
class PointRecord:
    id: str
    name: str
    location_text: str
    image_path: str | None
    image_attribution: str | None
    image_license: str | None
    instructions: list[str]
    duration: str | None
    pressure: str | None


def get_points(conn: psycopg.Connection, point_ids: list[str]) -> dict[str, PointRecord]:
    """The curated records for the given ids; unknown ids are simply absent."""
    if not point_ids:
        return {}
    rows = conn.execute(
        f"select {POINT_COLUMNS} from points where id = any(%s)", (list(point_ids),)
    ).fetchall()
    return {row[0]: PointRecord(*row) for row in rows}
