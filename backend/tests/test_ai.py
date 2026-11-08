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

from app.ai import EMBEDDING_DIMENSIONS, AIError, BedrockAI, FakeAI


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


# --- Opt-in live smoke test -----------------------------------------------------


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
