import io
import json
import math
from types import SimpleNamespace
from typing import Any

import httpx2
import pytest

from ingestion.ai import EMBEDDING_DIMENSIONS, AnthropicAI, BedrockAI, FakeAI, get_ai


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_fake_embeddings_are_normalised_and_deterministic() -> None:
    ai = FakeAI()
    vector = ai.embed("Pressure on the hand point")
    assert len(vector) == EMBEDDING_DIMENSIONS
    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0)
    assert vector == ai.embed("Pressure on the hand point")


def test_fake_embeddings_rank_related_text_higher() -> None:
    ai = FakeAI()
    query = ai.embed("headache relief")
    related = ai.embed("a point used for headache relief")
    unrelated = ai.embed("knee stiffness after running")
    assert cosine(query, related) > cosine(query, unrelated)


def test_get_ai_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "other")
    with pytest.raises(ValueError):
        get_ai()


@pytest.fixture
def bedrock(monkeypatch: pytest.MonkeyPatch) -> BedrockAI:
    """A BedrockAI whose AWS clients are replaced by stubs (no network)."""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    return BedrockAI()


def test_bedrock_embed_requests_titan_with_1024_dimensions(bedrock: BedrockAI) -> None:
    calls: list[dict[str, Any]] = []

    def invoke_model(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {"body": io.BytesIO(json.dumps({"embedding": [0.1] * 1024}).encode())}

    bedrock.runtime = SimpleNamespace(invoke_model=invoke_model)

    assert bedrock.embed("some text") == [0.1] * 1024
    assert calls[0]["modelId"] == "amazon.titan-embed-text-v2:0"
    assert json.loads(calls[0]["body"]) == {
        "inputText": "some text",
        "dimensions": 1024,
        "normalize": True,
    }


def test_bedrock_translate_returns_text_and_rejects_incomplete(bedrock: BedrockAI) -> None:
    responses = [
        SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text=" Hi ")]
        ),
        SimpleNamespace(stop_reason="max_tokens", content=[]),
    ]
    requests: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        return responses.pop(0)

    bedrock.claude = SimpleNamespace(messages=SimpleNamespace(create=create))  # type: ignore[assignment]

    assert bedrock.translate("Hallo", "de") == "Hi"
    assert requests[0]["model"] == "anthropic.claude-opus-5-5"
    assert "'de'" in requests[0]["messages"][0]["content"]
    with pytest.raises(RuntimeError):
        bedrock.translate("Hallo", "de")


def test_bedrock_retries_throttled_calls_adaptively(bedrock: BedrockAI) -> None:
    retries = bedrock.runtime.meta.config.retries
    assert retries["mode"] == "adaptive"
    assert retries["total_max_attempts"] == 12 + 1  # first try plus retries


@pytest.fixture
def anthropic_ai(monkeypatch: pytest.MonkeyPatch) -> AnthropicAI:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("VOYAGE_API_KEY", "test")
    return AnthropicAI()


def test_anthropic_embed_retries_rate_limits_and_requests_documents(
    anthropic_ai: AnthropicAI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ingestion.ai.time.sleep", lambda seconds: None)
    statuses = [429, 200]
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        return httpx2.Response(statuses.pop(0), json={"data": [{"embedding": [0.1] * 1024}]})

    anthropic_ai.voyage = httpx2.Client(transport=httpx2.MockTransport(handler))

    assert anthropic_ai.embed("some text") == [0.1] * 1024
    assert len(bodies) == 2
    assert bodies[0]["input_type"] == "document"
    assert bodies[0]["output_dimension"] == 1024


def test_anthropic_translate_uses_haiku_without_effort(anthropic_ai: AnthropicAI) -> None:
    requests: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        return SimpleNamespace(
            stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Hi")]
        )

    anthropic_ai.claude = SimpleNamespace(messages=SimpleNamespace(create=create))  # type: ignore[assignment]

    assert anthropic_ai.translate("Hallo", "de") == "Hi"
    assert requests[0]["model"] == "claude-haiku-4-5"
    assert "output_config" not in requests[0]
