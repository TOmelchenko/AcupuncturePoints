import json

import pytest

from app.ai import AIError
from app.demo_ai import demo_ai
from app.interpretation import Category, interpret
from app.validation import RecommendationChoice

CATEGORIES = [
    Category("headache", "Headache", ""),
    Category("neck-shoulder", "Neck and shoulder tension", ""),
]


def test_matches_categories_from_symptom_words() -> None:
    result = interpret(demo_ai(), "a throbbing headache and stiff neck", CATEGORIES)
    assert result.category_ids == ["headache", "neck-shoulder"]


def test_vague_symptom_asks_once() -> None:
    assert interpret(demo_ai(), "I feel off", CATEGORIES).needs_clarification
    after = interpret(demo_ai(), "I feel off", CATEGORIES, clarification=("Where?", "nowhere"))
    assert not after.needs_clarification


def test_markers_simulate_failures() -> None:
    with pytest.raises(AIError):
        interpret(demo_ai(), "headache [demo:fail]", CATEGORIES)
    prompt = (
        "<symptom>headache [demo:invalid-id]</symptom>\n\nCandidates (best first): "
        + json.dumps([{"id": i} for i in ("A", "B", "C")])
    )
    choice = demo_ai().generate("", prompt, RecommendationChoice)
    assert choice.point_ids == ["A", "B", "NOT-A-POINT"]
