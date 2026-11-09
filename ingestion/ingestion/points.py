"""Load curated point records (from `ingestion.web`) into the database.

For each point this upserts the `points` row (name, location, acupressure
instructions, duration, pressure), maps its "helps with" symptoms to the
predefined symptom categories, and stores one or more knowledge chunks linked to
the point. Re-running replaces the source's chunks and the points' category
links, so the step is repeatable. Existing point images are left untouched.

Usage:
    DATABASE_URL=... uv run python -m ingestion.points sources/web/meine-tcm/points.json
    AI_PROVIDER=fake ...   # offline run with fake embeddings
"""

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

from ingestion.ai import AI, get_ai
from ingestion.chunk import chunk_text
from ingestion.load import DEFAULT_DATABASE_URL, insert_chunk, upsert_source

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    description: str
    keywords: tuple[str, ...]  # lower-case word prefixes in the source's "helps with" items


# Self-care categories offered to users. Serious medical conditions in the source
# (e.g. hypertension, diabetes, glaucoma, depression) are deliberately not mapped.
CATEGORIES = (
    Category(
        "headache",
        "Headache",
        "Head pain, tension headache or migraine, at the forehead, temples, crown or back "
        "of the head.",
        ("headache", "migraine"),
    ),
    Category(
        "nausea",
        "Nausea",
        "Queasiness, travel sickness or rising stomach discomfort.",
        ("nausea", "stomach qi"),
    ),
    Category(
        "digestion",
        "Digestive discomfort",
        "Bloating, heartburn, reflux, stomach ache, diarrhoea, constipation or poor appetite.",
        (
            "bloating",
            "heartburn",
            "reflux",
            "abdominal pain",
            "stomach complaints",
            "stomach harmonizing",
            "diarrhea",
            "constipation",
            "loss of appetite",
            "strengthen digestion",
        ),
    ),
    Category(
        "stress",
        "Stress and anxiety",
        "Feeling tense, nervous, worried, restless or overwhelmed.",
        (
            "stress",
            "restlessness",
            "nervousness",
            "fear",
            "stage fright",
            "emotional harmonization",
        ),
    ),
    Category(
        "sleep",
        "Difficulty sleeping",
        "Trouble falling asleep or staying asleep.",
        ("insomnia", "sleep"),
    ),
    Category(
        "fatigue",
        "Fatigue",
        "Low energy, tiredness or difficulty concentrating.",
        ("chronic fatigue", "energy buildup", "lack of concentration"),
    ),
    Category(
        "neck-shoulder",
        "Neck and shoulder tension",
        "Stiffness, tension or pain in the neck and shoulders.",
        ("neck", "shoulder"),
    ),
    Category(
        "back-pain",
        "Back pain",
        "Pain or stiffness in the upper or lower back, including lumbago and sciatica.",
        ("back pain", "back problems", "lumbago", "sciatica"),
    ),
    Category(
        "joint-pain",
        "Joint and limb pain",
        "Pain in the knees, hips, elbows, wrists, arms, heels or calf cramps.",
        (
            "knee pain",
            "hip",
            "tennis elbow",
            "wrist pain",
            "upper arm",
            "heel spur",
            "plantar",
            "calf cramps",
        ),
    ),
    Category(
        "cold",
        "Cold and cough",
        "Common cold, flu-like symptoms, cough, hoarseness or a blocked, stuffy nose.",
        ("cold", "flu", "cough", "hoarseness", "sinus"),
    ),
    Category(
        "menstrual",
        "Menstrual and menopausal discomfort",
        "Period pain, premenstrual symptoms, irregular periods or hot flushes.",
        ("menstruation", "premenstrual", "menopaus", "hot flashes"),
    ),
    Category(
        "eyes-ears",
        "Tired eyes, ringing ears and dizziness",
        "Strained or sensitive eyes, ringing in the ears or light dizziness.",
        ("eye problems", "sensitive eyes", "tinnitus", "dizziness"),
    ),
)


def categories_for(helps_with: list[str]) -> list[str]:
    """Category ids whose keywords start a word in any "helps with" item ("flu" not in "reflux")."""
    text = "\n".join(item.lower() for item in helps_with)
    return [
        c.id for c in CATEGORIES if any(re.search(rf"\b{re.escape(k)}", text) for k in c.keywords)
    ]


def instructions_for(point: dict[str, Any]) -> list[str]:
    """The source's acupressure steps, plus its contraindication when there is one."""
    steps = list(point["instructions"])
    contraindication = (point.get("contraindication") or "").strip()
    if contraindication.lower() == "pregnancy":
        steps.append("Do not use this point during pregnancy.")
    elif contraindication and contraindication.lower() != "none":
        steps.append(f"Contraindication: {contraindication}.")
    return steps


def point_document(point: dict[str, Any]) -> str:
    """The text that is chunked and embedded for retrieval, headed by the point code."""
    parts = [
        f"{point['id']} {point['name']}",
        point.get("summary") or "",
        "Helps with: " + ", ".join(point["helps_with"]) if point["helps_with"] else "",
        f"Location: {point['location']}",
        *point.get("description", []),
        "TCM effects: " + "; ".join(point["tcm_effects"]) if point.get("tcm_effects") else "",
        "Acupressure: " + " ".join(instructions_for(point)),
    ]
    return "\n\n".join(p for p in parts if p)


def upsert_categories(conn: psycopg.Connection) -> None:
    for c in CATEGORIES:
        conn.execute(
            "insert into symptom_categories (id, name, description) values (%s, %s, %s) "
            "on conflict (id) do update set name = excluded.name, "
            "description = excluded.description",
            (c.id, c.name, c.description),
        )


def upsert_point(conn: psycopg.Connection, point: dict[str, Any]) -> None:
    conn.execute(
        "insert into points (id, name, location_text, instructions, duration, pressure) "
        "values (%s, %s, %s, %s, %s, %s) "
        "on conflict (id) do update set name = excluded.name, "
        "location_text = excluded.location_text, instructions = excluded.instructions, "
        "duration = excluded.duration, pressure = excluded.pressure",
        (
            point["id"],
            point["name"],
            point["location"],
            instructions_for(point),
            point.get("duration"),
            point.get("pressure"),
        ),
    )
    conn.execute("delete from point_categories where point_id = %s", (point["id"],))
    for category_id in categories_for(point["helps_with"]):
        conn.execute(
            "insert into point_categories (point_id, category_id) values (%s, %s)",
            (point["id"], category_id),
        )


def load_points(conn: psycopg.Connection, ai: AI, data: dict[str, Any]) -> tuple[int, int]:
    """Upsert categories, points and their chunks. Returns (points, chunks)."""
    upsert_categories(conn)
    source_id = upsert_source(conn, data["source"])
    chunks = 0
    for point in data["points"]:
        upsert_point(conn, point)
        heading = f"{point['id']} {point['name']}"
        for chunk in chunk_text(point_document(point)):
            # Later chunks repeat the heading, so every chunk says which point it is about.
            content = chunk if chunk.startswith(heading) else f"{heading}\n\n{chunk}"
            insert_chunk(conn, ai, source_id, point["id"], None, content)
            chunks += 1
    return len(data["points"]), chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Load curated points, categories and chunks.")
    parser.add_argument("points", type=Path, help="points.json written by ingestion.web")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = json.loads(args.points.read_text(encoding="utf-8"))
    with psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)) as conn:
        points, chunks = load_points(conn, get_ai(), data)  # committed on exit
    log.info("Loaded %d points and %d chunks", points, chunks)


if __name__ == "__main__":
    main()
