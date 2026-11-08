"""Validate the model's recommendation and build the response from curated records.

The model only chooses point ids from the candidates it was shown. Everything
the user sees about a point (name, location, image, instructions, duration,
pressure) comes from the curated database record, never from the model, so
missing values stay missing.
"""

import psycopg
from pydantic import BaseModel, Field

from app.ai import AIError
from app.points import PointRecord, get_points
from app.schemas import RecommendedPoint

IMAGE_BUCKET = "point-images"


class RecommendationChoice(BaseModel):
    """What the model returns for the recommendation step."""

    enough_relevant: bool = Field(
        description="False if fewer than three candidates really fit the symptom."
    )
    point_ids: list[str] = Field(description="Exactly three candidate point ids, best first.")


class InvalidRecommendation(AIError):
    """The model's output failed validation; nothing from it may be shown."""


def validate_choice(
    conn: psycopg.Connection, choice: RecommendationChoice, candidate_ids: set[str]
) -> list[PointRecord]:
    """Return the three chosen curated records in order, or raise InvalidRecommendation."""
    ids = choice.point_ids
    if len(ids) != 3:
        raise InvalidRecommendation(f"expected 3 point ids, got {len(ids)}")
    if len(set(ids)) != 3:
        raise InvalidRecommendation("duplicate point ids")
    if unknown := [pid for pid in ids if pid not in candidate_ids]:
        raise InvalidRecommendation(f"point ids not among candidates: {unknown}")
    records = get_points(conn, ids)
    if missing := [pid for pid in ids if pid not in records]:
        raise InvalidRecommendation(f"point ids not in curated database: {missing}")
    return [records[pid] for pid in ids]


def image_url(image_path: str | None, supabase_public_url: str) -> str | None:
    if not image_path:
        return None
    if image_path.startswith(("https://", "http://")):
        return image_path
    return f"{supabase_public_url}/storage/v1/object/public/{IMAGE_BUCKET}/{image_path}"


def build_points(records: list[PointRecord], supabase_public_url: str) -> list[RecommendedPoint]:
    return [
        RecommendedPoint(
            point_id=record.id,
            rank=rank,
            name=record.name,
            location_text=record.location_text,
            image_url=image_url(record.image_path, supabase_public_url),
            image_attribution=record.image_attribution if record.image_path else None,
            instructions=record.instructions,
            duration=record.duration,
            pressure=record.pressure,
        )
        for rank, record in enumerate(records, start=1)
    ]
