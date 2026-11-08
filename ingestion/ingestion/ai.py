"""Amazon Bedrock access for ingestion: embeddings and translation.

The embedding model and dimensions must match the backend's query embeddings
and the `vector(1024)` column in `db/01_schema.sql`.

Tests and offline runs use `FakeAI` (AI_PROVIDER=fake), which never calls AWS.
"""

import hashlib
import json
import math
import os
import re
from typing import Protocol

EMBEDDING_DIMENSIONS = 1024
DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_TEXT_MODEL = "anthropic.claude-opus-5-5"

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

        region = os.environ.get("AWS_REGION", "us-east-1")
        self.embedding_model = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", DEFAULT_EMBEDDING_MODEL)
        self.text_model = os.environ.get("BEDROCK_TEXT_MODEL_ID", DEFAULT_TEXT_MODEL)
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.claude = AnthropicBedrockMantle(aws_region=region, timeout=120.0)

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
        response = self.claude.messages.create(
            model=self.text_model,
            max_tokens=16000,
            output_config={"effort": "low"},
            messages=[
                {"role": "user", "content": TRANSLATE_PROMPT.format(language=language, text=text)}
            ],
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
    raise ValueError(f"Unknown AI_PROVIDER: {provider}")
