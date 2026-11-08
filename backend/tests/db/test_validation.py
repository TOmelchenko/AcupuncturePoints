import psycopg
import pytest

from app.ai import AIError
from app.points import PointRecord
from app.validation import (
    InvalidRecommendation,
    RecommendationChoice,
    build_points,
    image_url,
    validate_choice,
)

PUBLIC = "http://localhost:54321"


@pytest.fixture
def points(db: psycopg.Connection) -> psycopg.Connection:
    db.execute(
        "insert into points (id, name, location_text, instructions, duration, pressure, "
        "image_path, image_attribution, image_license) values "
        "('VA1', 'One', 'Loc 1', '{Step 1,Step 2}', '1 minute', 'Firm', "
        "'points/VA1.png', 'Fig 1', 'CC0'),"
        "('VA2', 'Two', 'Loc 2', '{Step}', null, null, null, null, null),"
        "('VA3', 'Three', 'Loc 3', '{Step}', null, 'Gentle', null, null, null)"
    )
    return db


def choice(ids: list[str]) -> RecommendationChoice:
    return RecommendationChoice(enough_relevant=True, point_ids=ids)


CANDIDATES = {"VA1", "VA2", "VA3", "GHOST"}


def test_valid_choice_returns_records_in_order(points: psycopg.Connection) -> None:
    records = validate_choice(points, choice(["VA3", "VA1", "VA2"]), CANDIDATES)
    assert [r.id for r in records] == ["VA3", "VA1", "VA2"]


@pytest.mark.parametrize(
    ("ids", "message"),
    [
        (["VA1", "VA2"], "expected 3"),
        (["VA1", "VA2", "VA3", "GHOST"], "expected 3"),
        (["VA1", "VA1", "VA2"], "duplicate"),
        (["VA1", "VA2", "LI4-INVENTED"], "not among candidates"),
        (["VA1", "VA2", "GHOST"], "not in curated database"),
    ],
)
def test_invalid_choices_are_rejected(
    points: psycopg.Connection, ids: list[str], message: str
) -> None:
    with pytest.raises(InvalidRecommendation, match=message) as error:
        validate_choice(points, choice(ids), CANDIDATES)
    assert isinstance(error.value, AIError)  # handled like any AI failure: generic error + retry


def test_response_details_come_from_curated_records_only(points: psycopg.Connection) -> None:
    records = validate_choice(points, choice(["VA1", "VA2", "VA3"]), CANDIDATES)
    one, two, three = build_points(records, PUBLIC)

    assert one.image_url == f"{PUBLIC}/storage/v1/object/public/point-images/points/VA1.png"
    assert (one.image_attribution, one.duration, one.pressure) == ("Fig 1", "1 minute", "Firm")
    assert one.instructions == ["Step 1", "Step 2"]
    # No image -> text location fallback only; missing duration/pressure stay absent.
    assert (two.image_url, two.location_text, two.duration, two.pressure) == (
        None,
        "Loc 2",
        None,
        None,
    )
    assert (three.duration, three.pressure) == (None, "Gentle")
    assert [p.rank for p in (one, two, three)] == [1, 2, 3]


def test_image_url_keeps_absolute_urls() -> None:
    assert image_url("https://example.org/li4.png", PUBLIC) == "https://example.org/li4.png"
    assert image_url(None, PUBLIC) is None


def test_attribution_is_hidden_without_image() -> None:
    record = PointRecord("X", "X", "Loc", None, "stale", None, ["Step"], None, None)
    assert build_points([record], PUBLIC)[0].image_attribution is None
