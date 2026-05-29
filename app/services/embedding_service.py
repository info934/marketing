from __future__ import annotations

import hashlib
from typing import Any

import requests

from app import config


FALLBACK_MODEL = "local_semantic_fingerprint_v2"
FALLBACK_PROVIDER = "local"
FALLBACK_DIMENSIONS = 128


def embed_text(text: str) -> dict[str, Any]:
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[dict[str, Any]]:
    cleaned = [_clean_text(text) for text in texts]
    if not cleaned:
        return []
    if not config.EMBEDDING_API_KEY:
        return [_fallback_embedding(text, "EMBEDDING_API_KEY is missing.") for text in cleaned]
    try:
        response = requests.post(
            f"{str(config.EMBEDDING_BASE_URL).rstrip('/')}/embeddings",
            headers={
                "Authorization": f"Bearer {config.EMBEDDING_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "Creative Memory RAG",
            },
            json={"model": config.EMBEDDING_MODEL, "input": cleaned},
            timeout=config.EMBEDDING_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        raw = response.json()
        embeddings = _extract_embeddings(raw, len(cleaned))
        if len(embeddings) != len(cleaned):
            raise ValueError("Embedding response count did not match input count.")
        return [
            {
                "status": "completed",
                "provider": _provider_from_base_url(str(config.EMBEDDING_BASE_URL)),
                "model": config.EMBEDDING_MODEL,
                "dimensions": len(vector),
                "vector": vector,
                "fallback_used": False,
                "error": "",
            }
            for vector in embeddings
        ]
    except Exception as exc:
        return [_fallback_embedding(text, str(exc)[:500]) for text in cleaned]


def semantic_fingerprint(text: str, size: int = FALLBACK_DIMENSIONS) -> list[float]:
    vector = [0.0 for _ in range(size)]
    words = [
        word
        for word in "".join(char.lower() if char.isalnum() else " " for char in str(text or "")).split()
        if len(word) > 2
    ]
    if not words:
        return vector
    for word in words[:900]:
        index = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16) % size
        vector[index] += 1.0
    total = sum(vector) or 1.0
    return [round(value / total, 6) for value in vector]


def cosine_similarity(left: list[Any], right: Any) -> float:
    if not isinstance(right, list):
        return 0.0
    try:
        left_values = [float(value) for value in left]
        right_values = [float(value) for value in right]
    except (TypeError, ValueError):
        return 0.0
    if not left_values or not right_values or len(left_values) != len(right_values):
        return 0.0
    dot = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = sum(a * a for a in left_values) ** 0.5
    right_norm = sum(b * b for b in right_values) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return round(dot / (left_norm * right_norm), 4)


def _extract_embeddings(raw: dict[str, Any], expected_count: int) -> list[list[float]]:
    rows = raw.get("data") or []
    vectors: list[list[float]] = []
    for row in rows[:expected_count]:
        embedding = row.get("embedding") if isinstance(row, dict) else None
        if not isinstance(embedding, list):
            continue
        vectors.append([float(value) for value in embedding])
    return vectors


def _fallback_embedding(text: str, reason: str) -> dict[str, Any]:
    vector = semantic_fingerprint(text)
    return {
        "status": "fallback",
        "provider": FALLBACK_PROVIDER,
        "model": FALLBACK_MODEL,
        "dimensions": len(vector),
        "vector": vector,
        "fallback_used": True,
        "error": reason,
    }


def _provider_from_base_url(base_url: str) -> str:
    lowered = base_url.lower()
    if "openrouter" in lowered:
        return "openrouter"
    if "openai" in lowered:
        return "openai"
    return "openai_compatible"


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())[:12000]
