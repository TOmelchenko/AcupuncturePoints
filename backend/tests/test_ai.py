import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
from pydantic import BaseModel

from app.ai import EMBEDDING_DIMENSIONS, AIError, AnthropicAI, BedrockAI, FakeAI, get_ai


class Answer(BaseModel):
    category: str


# --- FakeAI -------------------------------------------------------------------


def test_fake_returns_validated_handler_output() -> None:
    ai = FakeAI({Answer: lambda prompt: {"category": "headache"}})
    assert ai.generate("system", "my head hurts", Answer) == Answer(category="headache")
    assert ai.prompts == ["my head hurts"]


def test_fake_raises_ai_error_for_missing_handler_or_bad_shape() -> None:
    with pytest.raises(AIError):
        FakeAI().generate("s", "p", Answer)
    with pytest.raises(AIError):
        FakeAI({Answer: lambda p: {"wrong": 1}}).generate("s", "p", Answer)


def test_fake_can_simulate_failures() -> None:
    ai = FakeAI({Answer: lambda p: AIError("boom")})
    with pytest.raises(AIError, match="boom"):
        ai.generate("s", "p", Answer)


def test_fake_embeddings_match_ingestion() -> None:
    """Backend and ingestion fakes must embed identically for offline retrieval to work."""
    path = Path(__file__).parents[2] / "ingestion" / "ingestion" / "ai.py"
    spec = importlib.util.spec_from_file_location("ingestion_ai", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = "Press the point between thumb and index finger for headache relief."
    assert FakeAI().embed(text) == module.FakeAI().embed(text)


# --- BedrockAI with stubbed AWS clients ----------------------------------------


@pytest.fixture
def bedrock(monkeypatch: pytest.MonkeyPatch) -> BedrockAI:
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    return BedrockAI()


def stub_runtime(bedrock: BedrockAI, result: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def invoke_model(**kwargs: Any) -> Any:
        calls.append(kwargs)
        if isinstance(result, Exception):
            raise result
        return {"body": io.BytesIO(json.dumps({"embedding": result}).encode())}

    bedrock.runtime = SimpleNamespace(invoke_model=invoke_model)
    return calls


def stub_claude(bedrock: BedrockAI, result: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def parse(**kwargs: Any) -> Any:
        calls.append(kwargs)
        if isinstance(result, Exception):
            raise result
        return result

    bedrock.claude = SimpleNamespace(messages=SimpleNamespace(parse=parse))  # type: ignore[assignment]
    return calls


def test_embed_uses_titan_v2_with_1024_dimensions(bedrock: BedrockAI) -> None:
    calls = stub_runtime(bedrock, [0.5] * EMBEDDING_DIMENSIONS)
    assert bedrock.embed("sore neck") == [0.5] * EMBEDDING_DIMENSIONS
    assert calls[0]["modelId"] == "amazon.titan-embed-text-v2:0"
    assert json.loads(calls[0]["body"])["dimensions"] == 1024


@pytest.mark.parametrize("result", [RuntimeError("throttled"), [0.1] * 10], ids=["error", "dims"])
def test_embed_failures_raise_ai_error(bedrock: BedrockAI, result: Any) -> None:
    stub_runtime(bedrock, result)
    with pytest.raises(AIError):
        bedrock.embed("sore neck")


def test_generate_returns_parsed_output(bedrock: BedrockAI) -> None:
    calls = stub_claude(
        bedrock, SimpleNamespace(stop_reason="end_turn", parsed_output=Answer(category="sleep"))
    )
    assert bedrock.generate("be brief", "cannot sleep", Answer) == Answer(category="sleep")
    assert calls[0]["model"] == "anthropic.claude-opus-5-5"
    assert calls[0]["system"] == "be brief"
    assert calls[0]["output_format"] is Answer
    assert calls[0]["messages"] == [{"role": "user", "content": "cannot sleep"}]


REQUEST = httpx2.Request("POST", "https://bedrock.example/messages")


@pytest.mark.parametrize(
    "result",
    [
        SimpleNamespace(stop_reason="max_tokens", parsed_output=None),
        SimpleNamespace(stop_reason="refusal", parsed_output=None),
        SimpleNamespace(stop_reason="end_turn", parsed_output=None),
        anthropic.APIConnectionError(request=REQUEST),
        anthropic.APITimeoutError(request=REQUEST),
    ],
    ids=["max_tokens", "refusal", "no_output", "connection", "timeout"],
)
def test_generate_failures_raise_ai_error(bedrock: BedrockAI, result: Any) -> None:
    stub_claude(bedrock, result)
    with pytest.raises(AIError):
        bedrock.generate("s", "p", Answer)


def test_generate_omits_effort_for_haiku_4_5(bedrock: BedrockAI) -> None:
    bedrock.text_model = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    calls = stub_claude(
        bedrock, SimpleNamespace(stop_reason="end_turn", parsed_output=Answer(category="sleep"))
    )
    bedrock.generate("s", "p", Answer)
    assert "output_config" not in calls[0]


# --- AnthropicAI with stubbed HTTP clients --------------------------------------


@pytest.fixture
def anthropic_ai(monkeypatch: pytest.MonkeyPatch) -> AnthropicAI:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("VOYAGE_API_KEY", "test")
    return AnthropicAI()


def stub_voyage(ai: AnthropicAI, status: int, embedding: list[float]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(json.loads(request.content))
        return httpx2.Response(status, json={"data": [{"embedding": embedding}]})

    ai.voyage = httpx2.Client(transport=httpx2.MockTransport(handler))
    return calls


def test_get_ai_selects_anthropic_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    get_ai.cache_clear()
    try:
        assert isinstance(get_ai(), AnthropicAI)
    finally:
        get_ai.cache_clear()


def test_anthropic_embed_requests_voyage_query_with_1024_dimensions(
    anthropic_ai: AnthropicAI,
) -> None:
    calls = stub_voyage(anthropic_ai, 200, [0.5] * EMBEDDING_DIMENSIONS)
    assert anthropic_ai.embed("sore neck") == [0.5] * EMBEDDING_DIMENSIONS
    assert calls[0] == {
        "input": ["sore neck"],
        "model": "voyage-3.5",
        "input_type": "query",
        "output_dimension": 1024,
    }


@pytest.mark.parametrize(
    ("status", "embedding"), [(429, [0.5] * 1024), (200, [0.1] * 10)], ids=["http", "dims"]
)
def test_anthropic_embed_failures_raise_ai_error(
    anthropic_ai: AnthropicAI, status: int, embedding: list[float]
) -> None:
    stub_voyage(anthropic_ai, status, embedding)
    with pytest.raises(AIError):
        anthropic_ai.embed("sore neck")


def test_anthropic_generate_uses_haiku_without_effort(anthropic_ai: AnthropicAI) -> None:
    calls: list[dict[str, Any]] = []

    def parse(**kwargs: Any) -> Any:
        calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=Answer(category="sleep"))

    anthropic_ai.claude = SimpleNamespace(messages=SimpleNamespace(parse=parse))  # type: ignore[assignment]
    assert anthropic_ai.generate("s", "cannot sleep", Answer) == Answer(category="sleep")
    assert calls[0]["model"] == "claude-haiku-4-5"
    assert "output_config" not in calls[0]


# --- Opt-in live smoke tests -----------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AI") != "1", reason="set RUN_LIVE_AI=1 to call Bedrock"
)
def test_live_bedrock_smoke() -> None:
    ai = BedrockAI()
    assert len(ai.embed("tension headache")) == EMBEDDING_DIMENSIONS
    answer = ai.generate(
        "Classify the symptom.", "Category for 'my head hurts'? Use 'headache'.", Answer
    )
    assert answer.category


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AI") != "1", reason="set RUN_LIVE_AI=1 to call Anthropic and Voyage"
)
def test_live_anthropic_smoke() -> None:
    ai = AnthropicAI()
    assert len(ai.embed("tension headache")) == EMBEDDING_DIMENSIONS
    answer = ai.generate(
        "Classify the symptom.", "Category for 'my head hurts'? Use 'headache'.", Answer
    )
    assert answer.category
