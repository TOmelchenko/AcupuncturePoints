"""Amazon Bedrock access: query embeddings and structured text generation.

`get_ai()` returns the real `BedrockAI` unless AI_PROVIDER=fake. Tests program a
`FakeAI` instead, so automated tests never call AWS. Any provider failure is
raised as `AIError`, which callers turn into a generic, retryable error.

The embedding model and dimensions must match ingestion (`ingestion/ingestion/ai.py`)
and the `vector(1024)` column.
"""

import hashlib
import json
import logging
import math
import os
import re
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 1024
DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_TEXT_MODEL = "anthropic.claude-opus-5-5"
REQUEST_TIMEOUT_SECONDS = 30.0

T = TypeVar("T", bound=BaseModel)


class AIError(Exception):
    """The AI provider failed or returned something unusable."""


class AI(Protocol):
    def embed(self, text: str) -> list[float]: ...

    def generate(self, system: str, prompt: str, output: type[T]) -> T: ...


class BedrockAI:
    def __init__(self) -> None:
        import boto3
        from anthropic import AnthropicBedrockMantle
        from botocore.config import Config

        region = os.environ.get("AWS_REGION", "us-east-1")
        self.embedding_model = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL)
        self.text_model = os.environ.get("BEDROCK_TEXT_MODEL_ID", DEFAULT_TEXT_MODEL)
        timeout = Config(
            connect_timeout=5, read_timeout=REQUEST_TIMEOUT_SECONDS, retries={"max_attempts": 2}
        )
        self.runtime = boto3.client("bedrock-runtime", region_name=region, config=timeout)
        self.claude = AnthropicBedrockMantle(
            aws_region=region, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1
        )

    def embed(self, text: str) -> list[float]:
        try:
            response = self.runtime.invoke_model(
                modelId=self.embedding_model,
                body=json.dumps(
                    {"inputText": text, "dimensions": EMBEDDING_DIMENSIONS, "normalize": True}
                ),
            )
            embedding: list[float] = json.loads(response["body"].read())["embedding"]
        except Exception as exc:  # boto3 raises many unrelated exception types
            raise AIError(f"embedding failed: {type(exc).__name__}") from exc
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise AIError(f"embedding has {len(embedding)} dimensions")
        return embedding

    def generate(self, system: str, prompt: str, output: type[T]) -> T:
        import anthropic

        try:
            response = self.claude.messages.parse(
                model=self.text_model,
                max_tokens=4000,
                output_config={"effort": "low"},
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=output,
            )
        except (anthropic.APIError, ValidationError) as exc:
            raise AIError(f"generation failed: {type(exc).__name__}") from exc
        if response.stop_reason != "end_turn":
            raise AIError(f"generation stopped early: {response.stop_reason}")
        if response.parsed_output is None:
            raise AIError("generation returned no structured output")
        return response.parsed_output


class FakeAI:
    """Offline stand-in. Embeddings are hashed bag-of-words (same algorithm as
    ingestion's FakeAI, so fake retrieval works end to end); generation answers
    come from per-output-type handlers that tests or demo mode register."""

    def __init__(self, handlers: dict[type[BaseModel], Callable[[str], Any]] | None = None) -> None:
        self.handlers = dict(handlers or {})
        self.prompts: list[str] = []

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def generate(self, system: str, prompt: str, output: type[T]) -> T:
        self.prompts.append(prompt)
        handler = self.handlers.get(output)
        if handler is None:
            raise AIError(f"no fake response for {output.__name__}")
        result = handler(prompt)
        if isinstance(result, Exception):
            raise result
        try:
            return output.model_validate(result)
        except ValidationError as exc:
            raise AIError("fake response did not match the schema") from exc


@lru_cache
def get_ai() -> AI:
    provider = os.environ.get("AI_PROVIDER", "bedrock")
    if provider == "fake":
        log.warning("AI_PROVIDER=fake: using offline fake AI responses")
        return FakeAI()
    if provider == "bedrock":
        return BedrockAI()
    raise ValueError(f"Unknown AI_PROVIDER: {provider}")
