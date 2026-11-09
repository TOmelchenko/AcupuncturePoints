import pytest

from app.points import PointRecord
from app.ranking import MAX_RATING_ADJUSTMENT, RatingSignal, rank, rating_adjustment
from app.retrieval import Candidate


def candidate(point_id: str, relevance: float) -> Candidate:
    point = PointRecord(point_id, point_id, "here", None, None, None, ["press"], None, None)
    return Candidate(point, relevance)


def ids(candidates: list[Candidate]) -> list[str]:
    return [c.point.id for c in candidates]


def test_without_ratings_order_is_by_relevance() -> None:
    result = rank([candidate("B", 0.7), candidate("A", 0.9), candidate("C", 0.8)], {})
    assert ids(result) == ["A", "C", "B"]


def test_ratings_break_near_ties() -> None:
    signals = {"B": RatingSignal(average=5.0, count=20), "A": RatingSignal(average=1.0, count=20)}
    assert ids(rank([candidate("A", 0.80), candidate("B", 0.79)], signals)) == ["B", "A"]


def test_ratings_cannot_overturn_a_clearly_more_relevant_point() -> None:
    gap = 2 * MAX_RATING_ADJUSTMENT + 0.001
    best_possible = RatingSignal(average=5.0, count=1000)
    worst_possible = RatingSignal(average=1.0, count=1000)
    result = rank(
        [candidate("relevant", 0.9), candidate("less", 0.9 - gap)],
        {"relevant": worst_possible, "less": best_possible},
    )
    assert ids(result) == ["relevant", "less"]


@pytest.mark.parametrize("signal", [None, RatingSignal(5.0, 0), RatingSignal(3.0, 2)])
def test_missing_or_sparse_ratings_have_no_effect(signal: RatingSignal | None) -> None:
    assert rating_adjustment(signal) == 0.0


def test_adjustment_is_bounded_and_grows_with_count() -> None:
    assert rating_adjustment(RatingSignal(5.0, 1)) > 0.0
    assert rating_adjustment(RatingSignal(5.0, 1)) < rating_adjustment(RatingSignal(5.0, 3))
    assert rating_adjustment(RatingSignal(5.0, 3)) == pytest.approx(MAX_RATING_ADJUSTMENT)
    assert rating_adjustment(RatingSignal(1.0, 500)) == pytest.approx(-MAX_RATING_ADJUSTMENT)
    assert rating_adjustment(RatingSignal(3.0, 50)) == 0.0
