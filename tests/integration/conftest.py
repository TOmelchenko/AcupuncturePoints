"""Integration test fixtures.

Starts the real backend (uvicorn) against local Supabase with the development
seed data and the offline demo AI, and creates real Supabase Auth users.
Requires `make supabase-start db-setup db-seed`; `make test-integration` does this.
"""

import json
import os
import socket
import subprocess
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)


def supabase_keys() -> tuple[str, str]:
    service, anon = os.environ.get("SUPABASE_SERVICE_ROLE_KEY"), os.environ.get("SUPABASE_ANON_KEY")
    if service and anon:
        return service, anon
    status = subprocess.run(
        ["npx", "-y", "supabase@3.0.0", "status", "-o", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        pytest.fail("Local Supabase is not running: run `make supabase-start db-setup db-seed`")
    data = json.loads(status.stdout)
    return data["SERVICE_ROLE_KEY"], data["ANON_KEY"]


@dataclass
class User:
    id: str
    email: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class Supabase:
    def __init__(self, service_key: str, anon_key: str) -> None:
        self.service_key = service_key
        self.anon_key = anon_key
        self.created: list[str] = []

    def create_user(self) -> User:
        email, password = f"it-{uuid.uuid4()}@example.test", "integration-pass-123"
        admin = {"apikey": self.service_key, "Authorization": f"Bearer {self.service_key}"}
        user = httpx.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=admin,
            json={"email": email, "password": password, "email_confirm": True},
        )
        user.raise_for_status()
        self.created.append(user.json()["id"])
        session = httpx.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": self.anon_key},
            json={"email": email, "password": password},
        )
        session.raise_for_status()
        return User(user.json()["id"], email, session.json()["access_token"])

    def rest(self, user: User, table: str) -> list[dict[str, object]]:
        """Read a table through Supabase's REST API as the user (RLS applies)."""
        response = httpx.get(
            f"{SUPABASE_URL}/rest/v1/{table}?select=*",
            headers={"apikey": self.anon_key, **user.headers},
        )
        response.raise_for_status()
        rows: list[dict[str, object]] = response.json()
        return rows


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def supabase() -> Iterator[Supabase]:
    client = Supabase(*supabase_keys())
    yield client
    admin = {"apikey": client.service_key, "Authorization": f"Bearer {client.service_key}"}
    for user_id in client.created:
        httpx.delete(f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}", headers=admin)


@pytest.fixture(scope="session")
def api(supabase: Supabase) -> Iterator[httpx.Client]:
    """The real backend running as a separate process with the demo AI."""
    port = free_port()
    env = {
        **os.environ,
        "AI_PROVIDER": "fake",
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_ROLE_KEY": supabase.service_key,
        "DATABASE_URL": DATABASE_URL,
    }
    server = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT / "backend",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{base_url}/api/health").status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.5)
        else:
            pytest.fail("backend did not start")
        with httpx.Client(base_url=base_url, timeout=30) as client:
            yield client
    finally:
        server.terminate()
        server.wait(timeout=10)


@pytest.fixture
def db() -> Iterator[psycopg.Connection]:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        yield conn
