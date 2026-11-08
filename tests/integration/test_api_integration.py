"""Frontend-facing API flows against the running backend, real Auth and the database."""

from typing import Any

import httpx
import psycopg

from conftest import Supabase, User


def recommend(api: httpx.Client, user: User, symptom: str) -> httpx.Response:
    return api.post("/api/recommendations", json={"symptom": symptom}, headers=user.headers)


def clarify(api: httpx.Client, user: User, attempt_id: str, answer: str) -> httpx.Response:
    return api.post(
        f"/api/recommendations/{attempt_id}/clarification",
        json={"answer": answer},
        headers=user.headers,
    )


def attempt(db: psycopg.Connection, attempt_id: str) -> Any:
    return db.execute(
        "select outcome, symptom_text, category_ids from recommendation_attempts where id = %s",
        (attempt_id,),
    ).fetchone()


def test_requests_without_a_valid_token_are_rejected(api: httpx.Client) -> None:
    response = api.post(
        "/api/recommendations",
        json={"symptom": "headache"},
        headers={"Authorization": "Bearer not-a-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_matched_symptom_returns_three_seeded_points(
    api: httpx.Client, supabase: Supabase, db: psycopg.Connection
) -> None:
    user = supabase.create_user()
    response = recommend(api, user, "I have a headache")

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "recommended"
    points = {p["point_id"]: p for p in body["points"]}
    assert set(points) == {"LI4", "GB20", "EX-HN3"}
    assert points["LI4"]["image_url"].endswith("/point-images/dev/LI4.svg")
    assert httpx.get(points["LI4"]["image_url"]).status_code == 200  # served by Supabase Storage
    assert points["EX-HN3"]["image_url"] is None and points["EX-HN3"]["duration"] is None
    assert attempt(db, body["attempt_id"]) == ("recommended", "I have a headache", ["headache"])


def test_clarification_then_recommendation(api: httpx.Client, supabase: Supabase) -> None:
    user = supabase.create_user()
    first = recommend(api, user, "I feel off today").json()
    assert first["outcome"] == "clarification_needed"

    second = clarify(api, user, first["attempt_id"], "I'm stressed and anxious").json()
    assert second["outcome"] == "recommended"
    assert {p["point_id"] for p in second["points"]} == {"HT7", "EX-HN3", "PC6"}


def test_unmatched_after_clarification_is_no_match(
    api: httpx.Client, supabase: Supabase, db: psycopg.Connection
) -> None:
    user = supabase.create_user()
    first = recommend(api, user, "my knee clicks").json()
    second = clarify(api, user, first["attempt_id"], "when I climb stairs").json()
    assert second["outcome"] == "no_match"
    assert attempt(db, first["attempt_id"])[0] == "no_match"


def test_unknown_point_id_from_model_is_a_generic_error(
    api: httpx.Client, supabase: Supabase, db: psycopg.Connection
) -> None:
    user = supabase.create_user()
    response = recommend(api, user, "headache [demo:invalid-id]")

    assert response.status_code == 502
    assert response.json()["error"]["retryable"] is True
    assert "NOT-A-POINT" not in response.text
    row = db.execute(
        "select outcome from recommendation_attempts where user_id = %s", (user.id,)
    ).fetchone()
    assert row == ("failed",)


def test_feedback_is_stored_and_replaced(
    api: httpx.Client, supabase: Supabase, db: psycopg.Connection
) -> None:
    user = supabase.create_user()
    body = recommend(api, user, "I have a headache").json()
    url = f"/api/recommendations/{body['attempt_id']}/points/LI4/feedback"

    assert api.post(url, json={"rating": 2}, headers=user.headers).status_code == 200
    assert api.post(url, json={"rating": 5}, headers=user.headers).json()["rating"] == 5
    assert api.post(url, json={"rating": 9}, headers=user.headers).status_code == 422
    rows = db.execute(
        "select point_id, rating from point_ratings where attempt_id = %s", (body["attempt_id"],)
    ).fetchall()
    assert rows == [("LI4", 5)]


def test_users_cannot_access_each_others_data(api: httpx.Client, supabase: Supabase) -> None:
    alice, bob = supabase.create_user(), supabase.create_user()
    body = recommend(api, alice, "I have a headache").json()
    attempt_id = body["attempt_id"]

    # Through the backend API
    feedback = api.post(
        f"/api/recommendations/{attempt_id}/points/LI4/feedback",
        json={"rating": 1},
        headers=bob.headers,
    )
    assert feedback.status_code == 404
    # Directly through Supabase's REST API with the public anon key (RLS)
    assert [r["id"] for r in supabase.rest(alice, "recommendation_attempts")] == [attempt_id]
    assert supabase.rest(bob, "recommendation_attempts") == []
    assert supabase.rest(bob, "recommendation_points") == []
    assert len(supabase.rest(bob, "points")) >= 3  # curated content is readable


def test_account_deletion_removes_data_and_login(
    api: httpx.Client, supabase: Supabase, db: psycopg.Connection
) -> None:
    user = supabase.create_user()
    body = recommend(api, user, "I have a headache").json()
    api.post(
        f"/api/recommendations/{body['attempt_id']}/points/LI4/feedback",
        json={"rating": 4},
        headers=user.headers,
    )

    assert api.delete("/api/account", headers=user.headers).status_code == 204

    for sql in (
        "select count(*) from recommendation_attempts where user_id = %s",
        "select count(*) from point_ratings where user_id = %s",
        "select count(*) from auth.users where id = %s",
    ):
        assert db.execute(sql, (user.id,)).fetchone() == (0,)
