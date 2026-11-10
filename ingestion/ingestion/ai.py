"""AI access for ingestion: embeddings and translation.

AI_PROVIDER picks `bedrock` (Claude and Titan on Amazon Bedrock), `anthropic`
(Claude on the Anthropic API, embeddings from Voyage AI) or `fake`.

The embedding model and dimensions must match the backend's query embeddings
and the `vector(1024)` column in `db/01_schema.sql`.

Tests and offline runs use `FakeAI` (AI_PROVIDER=fake), which never calls a provider.
"""

import hashlib
import json
import math
import os
import re
import time
from typing import Any, Protocol

EMBEDDING_DIMENSIONS = 1024
DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_TEXT_MODEL = "anthropic.claude-opus-5-5"
# Retries per Bedrock call; "adaptive" mode also rate-limits the client after throttling.
BEDROCK_MAX_ATTEMPTS = 12
DEFAULT_ANTHROPIC_TEXT_MODEL = "claude-haiku-4-5"
DEFAULT_VOYAGE_EMBEDDING_MODEL = "voyage-3.5"
VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MAX_ATTEMPTS = 8

TRANSLATE_PROMPT = (
    "Translate the following text from the language with ISO code '{language}' into English. "
    "Keep acupressure point codes (such as LI4 or PC6), numbers and measurements exactly as "
    "written. Reply with the translation only.\n\n{text}"
)


class AI(Protocol):
    def embed(self, text: str) -> list[float]: ...

    def translate(self, text: str, language: str) -> str: ...


class BedrockAI:
    def __init__(self) -> None:
        import boto3
        from anthropic import AnthropicBedrockMantle
        from botocore.config import Config

        region = os.environ.get("AWS_REGION", "us-east-1")
        self.embedding_model = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL)
        self.text_model = os.environ.get("BEDROCK_TEXT_MODEL_ID", DEFAULT_TEXT_MODEL)
        # Ingestion is a batch job: on throttling, slow down and keep retrying.
        retries = Config(retries={"max_attempts": BEDROCK_MAX_ATTEMPTS, "mode": "adaptive"})
        self.runtime = boto3.client("bedrock-runtime", region_name=region, config=retries)
        self.claude = AnthropicBedrockMantle(aws_region=region, timeout=120.0, max_retries=8)

    def embed(self, text: str) -> list[float]:
        response = self.runtime.invoke_model(
            modelId=self.embedding_model,
            body=json.dumps(
                {"inputText": text, "dimensions": EMBEDDING_DIMENSIONS, "normalize": True}
            ),
        )
        embedding: list[float] = json.loads(response["body"].read())["embedding"]
        return embedding

    def translate(self, text: str, language: str) -> str:
        return translate_with_claude(self.claude, self.text_model, text, language)


class AnthropicAI:
    """Claude on the Anthropic API for translation, Voyage AI for document embeddings."""

    def __init__(self) -> None:
        import anthropic
        import httpx2

        self.text_model = os.environ.get("ANTHROPIC_TEXT_MODEL_ID", DEFAULT_ANTHROPIC_TEXT_MODEL)
        self.embedding_model = os.environ.get(
            "VOYAGE_EMBEDDING_MODEL_ID", DEFAULT_VOYAGE_EMBEDDING_MODEL
        )
        self.claude = anthropic.Anthropic(timeout=120.0, max_retries=8)
        self.voyage = httpx2.Client(
            timeout=60.0,
            headers={"Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"},
        )

    def embed(self, text: str) -> list[float]:
        body = {
            "input": [text],
            "model": self.embedding_model,
            "input_type": "document",
            "output_dimension": EMBEDDING_DIMENSIONS,
        }
        # Ingestion is a batch job: on rate limiting, back off and keep retrying.
        for attempt in range(VOYAGE_MAX_ATTEMPTS):
            response = self.voyage.post(VOYAGE_URL, json=body)
            if response.status_code != 429 or attempt == VOYAGE_MAX_ATTEMPTS - 1:
                break
            time.sleep(min(2**attempt, 60))
        response.raise_for_status()
        embedding: list[float] = response.json()["data"][0]["embedding"]
        return embedding

    def translate(self, text: str, language: str) -> str:
        return translate_with_claude(self.claude, self.text_model, text, language)


def translate_with_claude(claude: Any, model: str, text: str, language: str) -> str:
    # Haiku 4.5 rejects the effort parameter; newer models use it to keep answers quick.
    effort = {} if "haiku-4-5" in model else {"output_config": {"effort": "low"}}
    response = claude.messages.create(
        model=model,
        max_tokens=16000,
        messages=[
            {"role": "user", "content": TRANSLATE_PROMPT.format(language=language, text=text)}
        ],
        **effort,
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Translation did not complete (stop_reason={response.stop_reason})")
    return "".join(block.text for block in response.content if block.type == "text").strip()


class FakeAI:
    """Deterministic, offline stand-in: hashed bag-of-words embeddings, tagged translation.

    Texts that share words get similar embeddings, which is enough for local
    development and tests of the retrieval plumbing.
    """

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def translate(self, text: str, language: str) -> str:
        return f"[translated from {language}] {text}"


def get_ai() -> AI:
    provider = os.environ.get("AI_PROVIDER", "bedrock")
    if provider == "fake":
        return FakeAI()
    if provider == "bedrock":
        return BedrockAI()
    if provider == "anthropic":
        return AnthropicAI()
    raise ValueError(f"Unknown AI_PROVIDER: {provider}")
