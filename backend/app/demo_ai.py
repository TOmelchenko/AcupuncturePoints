"""Offline demo responses for AI_PROVIDER=fake (local development and browser tests).

Interpretation matches category names and ids against the symptom words;
the recommendation step picks the first three candidates. This is not a real
model and must never be used in production.
"""

import json
import re
from typing import Any

from app.ai import FakeAI
from app.interpretation import Interpretation
from app.validation import RecommendationChoice

STOP_WORDS = {"and", "or", "the", "a", "of", "difficulty"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP_WORDS and len(w) > 2}


def _stems(words: set[str]) -> set[str]:
    return {w[:5] for w in words}


def interpret(prompt: str) -> dict[str, Any]:
    categories = json.loads(prompt.split("Categories: ", 1)[1].split("\n", 1)[0])
    text = re.findall(r"<(?:symptom|answer)>(.*?)</(?:symptom|answer)>", prompt, re.S)
    said = _stems(_words(" ".join(text)))
    matched = [
        c["id"]
        for c in categories
        if said & _stems(_words(f"{c['id'].replace('-', ' ')} {c['name']}"))
    ]
    answered = "<answer>" in prompt
    return {
        "category_ids": matched,
        "search_terms": [" ".join(text)] if text else [],
        "needs_clarification": not matched and not answered,
        "clarification_question": "Where do you feel it, and what does it feel like?",
    }


def recommend(prompt: str) -> dict[str, Any]:
    candidates = json.loads(prompt.split("Candidates (best first): ", 1)[1].split("\n", 1)[0])
    ids = [c["id"] for c in candidates][:3]
    return {"enough_relevant": len(ids) == 3, "point_ids": ids}


def demo_ai() -> FakeAI:
    return FakeAI({Interpretation: interpret, RecommendationChoice: recommend})
