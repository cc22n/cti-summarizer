"""Semantic embedding service using xAI API.

Generates text embeddings and computes cosine similarity for semantic search.
Falls back gracefully when the API key is not configured.
"""

import logging
import math

logger = logging.getLogger(__name__)

# Module-level singleton; avoids creating a new httpx connection pool per call.
_openai_client = None


def _get_client():
    """Return (or lazily create) the shared AsyncOpenAI client."""
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    from app.config import settings

    if not settings.xai_api_key:
        return None

    from openai import AsyncOpenAI

    _openai_client = AsyncOpenAI(
        api_key=settings.xai_api_key,
        base_url=settings.xai_base_url,
    )
    return _openai_client


def _cosine(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


async def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Generate embeddings for a batch of texts using xAI API.

    Returns None when the API key is not set or the call fails.
    """
    from app.config import settings

    if not settings.xai_api_key:
        return None

    client = _get_client()
    if client is None:
        return None

    try:
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as exc:
        logger.warning("[embedding] API call failed: %s", exc)
        return None


async def semantic_rank(
    query: str,
    texts: list[str],
) -> list[float] | None:
    """Return cosine similarity scores for query vs each text.

    Returns None if embeddings are unavailable (no API key or API failure).
    Scores are in [0, 1]; higher is more similar.
    """
    if not texts:
        return []

    all_texts = [query] + texts
    embeddings = await embed_texts(all_texts)
    if embeddings is None:
        return None

    query_emb = embeddings[0]
    return [_cosine(query_emb, emb) for emb in embeddings[1:]]
